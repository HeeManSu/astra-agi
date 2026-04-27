"""
Sandbox for Team Code Mode.

This module provides:
1. Code generation from user queries using LLM
2. Code execution in isolated subprocess

@deprecated() Moved to the new DSL architecture.
Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    PARENT PROCESS                           │
    │  Sandbox.run(query)                                         │
    │    ├── generate_parse_validate_code() → LLM → Python code                  │
    │    └── execute() → subprocess                               │
    │          ├── Monitor stdout for tool calls                  │
    │          ├── Execute tool, send result via stdin            │
    │          └── Capture synthesize_response() output           │
    └─────────────────────────────────────────────────────────────┘
                               ↕ stdin/stdout (JSON)
    ┌─────────────────────────────────────────────────────────────┐
    │                    CHILD PROCESS                            │
    │  Runtime Bridge (injected)                                  │
    │    ├── call_tool(name, args) → stdout → parent              │
    │    ├── synthesize_response(msg) → stdout → exit             │
    │    └── Agent stub classes (route to call_tool)              │
    │  LLM Generated Code (appended)                              │
    └─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import os
import re
import sys
from typing import TYPE_CHECKING, Any

from observability.debug import save_debug_artifact
from typing_extensions import deprecated

from framework.code_mode.compiler.ast_parser import parse_code, validate
from framework.code_mode.compiler.nodes import ActionNode
from framework.code_mode.compiler.workflow_builder import ExecutionWorkflow, build_workflow
from framework.code_mode.executor import run_workflow
from framework.code_mode.prompts import (
    AGENT_CODE_MODE_PROMPT,
    RESPONSE_FORMAT_PROMPT,
    TEAM_CODE_MODE_PROMPT,
    TEAM_PLANNER_PROMPT,
)
from framework.code_mode.stub_generator import generate_runtime_stubs, generate_stubs


if TYPE_CHECKING:
    from framework.code_mode.provider import CodeModeProvider

RUNTIME_BRIDGE = '''
import sys
import json

def call_tool(name: str, **kwargs):
    """Call a tool in the parent process.

    Sends a JSON request to stdout, waits for response on stdin.

    Args:
        name: Tool name (e.g., "inventory.check_inventory")
        **kwargs: Tool arguments

    Returns:
        Tool result (dict or primitive)

    Raises:
        RuntimeError: If tool execution fails
    """
    # Send request to parent via stdout
    request = {"type": "call_tool", "name": name, "args": kwargs}
    print(json.dumps(request), flush=True)

    # Wait for response from parent via stdin
    # Use 100MB buffer limit to handle very large tool responses
    response_line = sys.stdin.readline(100 * 1024 * 1024)
    if not response_line:
        raise RuntimeError("No response from parent process")

    response = json.loads(response_line)

    # Check for error
    if response.get("type") == "error":
        raise RuntimeError(response.get("message", "Tool execution failed"))

    return response.get("data", {})


def synthesize_response(message):   # (message:str -> message)
    """Return final response to parent and exit.

    This ends the subprocess execution and sends the final answer.

    Args:
        message: Final response message (can be str, dict, or list)
    """
    # Handle dict/list by JSON serializing, otherwise use str @todo: Proper review required
    if isinstance(message, (dict, list)):
        message_str = json.dumps(message, ensure_ascii=False, default=str)
    else:
        message_str = str(message)

    request = {"type": "synthesize", "message": message_str}
    print(json.dumps(request), flush=True)
    sys.exit(0)

'''


@dataclass
class SandboxResult:
    """Result from sandbox code execution.

    Attributes:
        output: Raw JSON output from synthesize_response()
        formatted_output: Human-readable formatted response (from LLM)
        success: Whether execution completed successfully
        tool_calls: List of tool calls made during execution
        stderr: Standard error output (for debugging)
        generated_code: The LLM-generated code that was executed
    """

    output: str
    formatted_output: str = ""
    success: bool = True
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stderr: str = ""
    generated_code: str = ""


class Sandbox:
    """Sandbox for code mode execution (Agent & Team).

    Current flow:
        run() → generate_parse_validate_code() → build_dsl_workflow() → execute_dsl()

    For streaming, callers invoke each step individually so they can yield
    events between stages (see Team.stream / Agent.stream).
    """

    def __init__(
        self,
        provider: CodeModeProvider,
    ):
        """Initialize sandbox with a CodeModeProvider.

        The provider (Agent, Team, Workflow, etc.) must implement the
        CodeModeProvider protocol.

        Args:
            provider: The entity providing tools and metadata
        """
        self.provider = provider
        self.model = provider.model
        self._tool_map: dict[str, Any] | None = None
        self._mcp_tool_name_map: dict[str, str] = {}
        self._semantic_layer: Any = None
        self._dsl_workflow: ExecutionWorkflow | None = None

    @deprecated("Use _build_dsl_tool_map() instead")
    def _build_tool_map(self) -> dict[str, Any]:
        """Build a tool lookup map from provider's tools.

        Maps "domain_id.tool_slug" to Tool objects for local tools.
        Stores MCPToolkit objects keyed by mcp slug ("mcp_slug" -> ("MCP", toolkit)).

        For Agents: uses provider.tools directly
        For Teams: iterates through flat_members to get each agent's tools
        """
        from framework.code_mode.stub_generator import _sanitize_identifier
        from framework.tool import Tool
        from framework.tool.mcp.toolkit import MCPToolkit

        tool_map: dict[str, Any] = {}
        self._mcp_tool_name_map = {}
        semantic = self._semantic_layer or self.provider.build_semantic_layer()

        def normalize_domain_id(value: str | None, fallback: str = "unknown-domain") -> str:
            if isinstance(value, str) and value.strip():
                return value.strip()
            return fallback

        def register_tools(tools: list[Any], domain_id: str) -> None:
            """Register tools from a list (local or MCP)."""
            nonlocal tool_map
            # Sanitized form matches what the stub generator emits and what the
            # LLM writes in code (e.g. "macro-strategist" -> "macro_strategist").
            sanitized_domain = _sanitize_identifier(domain_id)
            for tool in tools:
                if isinstance(tool, Tool):
                    tool_slug = str(getattr(tool, "slug", "")).strip()
                    if not tool_slug:
                        raise ValueError("Local tool is missing slug in sandbox tool map build.")
                    sanitized_slug = _sanitize_identifier(tool_slug)
                    qualified_name = f"{domain_id}.{tool_slug}"
                    existing = tool_map.get(qualified_name)
                    if existing is not None and existing is not tool:
                        raise ValueError(
                            f"Duplicate local tool key '{qualified_name}' detected while building tool map."
                        )
                    tool_map[qualified_name] = tool

                    # Alias under the sanitized key so LLM-generated code
                    # (which uses Python-identifier-safe names) resolves.
                    sanitized_key = f"{sanitized_domain}.{sanitized_slug}"
                    if sanitized_key != qualified_name:
                        tool_map.setdefault(sanitized_key, tool)

                    # Backward compatibility alias by tool name.
                    name_alias = f"{domain_id}.{tool.name}"
                    if name_alias not in tool_map:
                        tool_map[name_alias] = tool
                elif isinstance(tool, MCPToolkit):
                    mcp_slug = str(getattr(tool, "slug", "")).strip()
                    if not mcp_slug:
                        raise ValueError("MCP toolkit is missing slug in sandbox tool map build.")
                    existing = tool_map.get(mcp_slug)
                    if existing is not None and existing != ("MCP", tool):
                        raise ValueError(
                            f"Duplicate MCP toolkit slug '{mcp_slug}' detected while building tool map."
                        )
                    tool_map[mcp_slug] = ("MCP", tool)

        if self.provider.provider_type == "AGENT":
            # Agent: use provider's tools directly
            agent_id = normalize_domain_id(getattr(self.provider, "id", None), semantic.provider_id)
            tools = getattr(self.provider, "tools", None) or []
            register_tools(tools, agent_id)
        else:
            # Team: iterate through member agents
            flat_members = getattr(self.provider, "flat_members", [])
            for member in flat_members:
                agent = member.agent
                agent_id = normalize_domain_id(
                    getattr(member, "id", None),
                    normalize_domain_id(
                        getattr(agent, "id", None), getattr(member, "name", "member")
                    ),
                )
                tools = getattr(agent, "tools", None) or []
                register_tools(tools, agent_id)

        # Build mcp_slug.tool_slug -> remote MCP tool-name map from semantic layer.
        mcp_domains = {
            domain.id for domain in semantic.domains if isinstance(tool_map.get(domain.id), tuple)
        }
        for domain in semantic.domains:
            if domain.id not in mcp_domains:
                continue
            for tool_schema in domain.tools:
                self._mcp_tool_name_map[f"{domain.id}.{tool_schema.slug}"] = tool_schema.name

        return tool_map

    @deprecated("Use _build_dsl_tool_map() instead")
    def _get_tool(self, qualified_name: str) -> Any | None:
        """Look up a tool by qualified name.

        Args:
            qualified_name: Full tool key (e.g., "agent-ops.get-stock-price")

        Returns:
            Tool if found, None otherwise
        """
        if self._tool_map is None:
            self._tool_map = self._build_tool_map()
        return self._tool_map.get(qualified_name)

    @deprecated("Use build_dsl_workflow() + execute_dsl() instead")
    async def execute(self, code: str, timeout: float = 60.0) -> SandboxResult:
        """DEPRECATED: Run Python code in an isolated subprocess.

        Replaced by build_dsl_workflow() + execute_dsl().

        Runs code safely by building a complete Python script
        (runtime bridge + stubs + LLM code), spawning a subprocess,
        and handling tool calls via stdin/stdout IPC.

        Args:
            code: Python code to run (usually from generate_parse_validate_code())
            timeout: Maximum time to wait (default: 60 seconds)

        Returns:
            SandboxResult with the output and metadata
        """
        from observability import LogLevel, SpanKind, log, span, update_span

        async with span(
            "sandbox.execution",
            kind=SpanKind.STEP,
            attributes={
                "code_length": len(code),
                "timeout": timeout,
            },
        ):
            await log(LogLevel.INFO, "Starting sandbox execution")

            full_code = self._build_full_code(code)
            await log(
                LogLevel.DEBUG,
                f"Built full code with runtime bridge ({len(full_code)} chars)",
                {"code_length": len(full_code)},
            )

            save_debug_artifact("full_runtime_code.py", full_code)
            await log(LogLevel.DEBUG, "Saved full runtime code to: .debug/full_runtime_code.py")

            large_limit = 100 * 1024 * 1024  # 100MB
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                full_code,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=large_limit,
            )

            await log(LogLevel.DEBUG, f"Subprocess started with PID: {proc.pid}")
            update_span({"subprocess_id": proc.pid})

            try:
                await log(LogLevel.DEBUG, "Monitoring subprocess for tool calls")
                result = await asyncio.wait_for(
                    self._monitor_subprocess(proc),
                    timeout=timeout,
                )
                return result

            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                await log(LogLevel.ERROR, f"Execution timed out after {timeout}s")
                return SandboxResult(
                    output="Execution timed out",
                    success=False,
                    stderr="TimeoutError: Execution exceeded time limit",
                )

    @deprecated("Subprocess execution replaced by DSL engine")
    def _build_full_code(self, code: str) -> str:
        """DEPRECATED: Assemble runtime bridge + stubs + LLM code for subprocess."""
        parts = []
        parts.append(RUNTIME_BRIDGE)

        semantic_layer = self._semantic_layer or self.provider.build_semantic_layer()
        runtime_stubs = generate_runtime_stubs(semantic_layer)
        parts.append(runtime_stubs)

        parts.append("\n# ═══════ LLM Generated Code ═══════\n")
        parts.append(code)

        return "\n".join(parts)

    @deprecated("Subprocess execution replaced by DSL engine")
    async def _monitor_subprocess(self, proc: asyncio.subprocess.Process) -> SandboxResult:
        """DEPRECATED: IPC loop — reads subprocess stdout, routes tool calls via stdin."""
        output_lines: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        tool_results_for_debug: list[dict[str, Any]] = []
        final_response: str | None = None

        assert proc.stdout is not None
        assert proc.stdin is not None

        while True:
            line = await proc.stdout.readline()
            if not line:
                break

            text = line.decode("utf-8", errors="replace").strip()

            if text.startswith("{") and text.endswith("}"):
                try:
                    request = json.loads(text)
                    msg_type = request.get("type")

                    if msg_type == "call_tool":
                        tool_calls.append(request)
                        response = await self._handle_tool_call(request)

                        if response.get("type") == "error":
                            request["error"] = response.get("message")
                        else:
                            request["result"] = response.get("data")

                        tool_results_for_debug.append(
                            {
                                "tool": request.get("name"),
                                "args": request.get("args"),
                                "result": response.get("data")
                                if response.get("type") == "result"
                                else None,
                                "error": response.get("message")
                                if response.get("type") == "error"
                                else None,
                            }
                        )

                        try:
                            os.makedirs(".debug", exist_ok=True)
                            import pathlib as _pathlib

                            _pathlib.Path(".debug/tool_results.json").write_text(
                                json.dumps(tool_results_for_debug, indent=2, default=str)
                            )
                        except Exception:
                            pass

                        proc.stdin.write((json.dumps(response) + "\n").encode("utf-8"))
                        await proc.stdin.drain()

                    elif msg_type == "synthesize":
                        final_response = request.get("message", "")

                    continue

                except json.JSONDecodeError:
                    pass

            output_lines.append(text)

        from observability import LogLevel, log, span

        await proc.wait()

        stderr = ""
        if proc.stderr:
            stderr_bytes = await proc.stderr.read()
            stderr = stderr_bytes.decode("utf-8", errors="replace")

        output = final_response if final_response else "\n".join(output_lines)

        if proc.returncode == 0:
            await log(
                LogLevel.INFO,
                f"Sandbox execution successful ({len(tool_calls)} tool calls)",
                {"tool_calls_count": len(tool_calls)},
            )
        else:
            await log(LogLevel.ERROR, f"Sandbox execution failed with exit code: {proc.returncode}")
            if stderr:
                await log(LogLevel.ERROR, f"Subprocess stderr:\n{stderr}")
            if output_lines:
                await log(LogLevel.ERROR, f"Subprocess stdout:\n{chr(10).join(output_lines)}")

        async with span(
            "event.done",
            attributes={
                "event_type": "done",
                "status": "complete" if proc.returncode == 0 else "error",
                "tool_calls_count": len(tool_calls),
            },
        ):
            await log(LogLevel.DEBUG, "Emitting SSE event: done")

        return SandboxResult(
            output=output,
            success=proc.returncode == 0,
            tool_calls=tool_calls,
            stderr=stderr,
        )

    @deprecated("Subprocess execution replaced by DSL engine")
    async def _handle_tool_call(self, request: dict[str, Any]) -> dict[str, Any]:
        """DEPRECATED: Execute a tool call from the subprocess IPC loop."""
        from observability import LogLevel, SpanKind, log, span

        name = request.get("name", "")
        args = request.get("args", {})

        if "." not in name:
            return {"type": "error", "message": f"Invalid tool name format: '{name}'"}
        module_name, tool_name = name.rsplit(".", 1)
        if not module_name or not tool_name:
            return {"type": "error", "message": f"Invalid tool name format: '{name}'"}

        mcp_entry = self._get_tool(module_name)
        is_mcp = isinstance(mcp_entry, tuple) and len(mcp_entry) == 2 and mcp_entry[0] == "MCP"

        if is_mcp:
            assert mcp_entry is not None
            _, mcp_toolkit = mcp_entry
            requested_tool = f"{module_name}.{tool_name}"
            remote_tool_name = self._mcp_tool_name_map.get(requested_tool, tool_name)

            async with span(
                f"tool.{tool_name}",
                kind=SpanKind.TOOL,
                attributes={
                    "tool_name": tool_name,
                    "tool_slug": tool_name,
                    "remote_tool_name": remote_tool_name,
                    "tool_qualified_name": f"{module_name}.{tool_name}",
                    "mcp_toolkit": mcp_toolkit.name,
                    "args": args,
                    "execution_type": "mcp",
                },
            ):
                await log(
                    LogLevel.INFO,
                    f"Executing MCP tool: {mcp_toolkit.name}.{remote_tool_name}",
                )
                await log(LogLevel.DEBUG, f"Tool args: {json.dumps(args)}")

                async with span(
                    "event.tool_call",
                    attributes={
                        "event_type": "tool_call",
                        "tool": tool_name,
                        "args": args,
                        "mcp": True,
                    },
                ):
                    await log(LogLevel.DEBUG, "Emitting SSE event: tool_call")

                try:
                    result = await mcp_toolkit.call_tool(remote_tool_name, **args)

                    try:
                        data = json.loads(result)
                    except (json.JSONDecodeError, TypeError):
                        data = {"result": result}

                    await log(LogLevel.INFO, "MCP tool execution completed successfully")

                    async with span(
                        "event.tool_result",
                        attributes={
                            "event_type": "tool_result",
                            "tool": tool_name,
                            "success": True,
                            "mcp": True,
                        },
                    ):
                        await log(LogLevel.DEBUG, "Emitting SSE event: tool_result")

                    return {"type": "result", "data": data}

                except Exception as e:
                    await log(LogLevel.ERROR, f"MCP tool execution failed: {e!s}")
                    async with span(
                        "event.tool_result",
                        attributes={
                            "event_type": "tool_result",
                            "tool": tool_name,
                            "success": False,
                            "error": str(e),
                            "mcp": True,
                        },
                    ):
                        await log(LogLevel.DEBUG, "Emitting SSE event: tool_result (error)")
                    return {"type": "error", "message": str(e)}

        qualified_name = f"{module_name}.{tool_name}"
        tool = self._get_tool(qualified_name)

        exec_type = "unknown"
        if tool:
            exec_type = "async" if asyncio.iscoroutinefunction(tool.func) else "sync"

        async with span(
            f"tool.{tool_name}",
            kind=SpanKind.TOOL,
            attributes={
                "tool_name": tool_name,
                "tool_qualified_name": qualified_name,
                "args": args,
                "execution_type": exec_type,
            },
        ):
            await log(LogLevel.INFO, f"Executing tool: {tool_name}")
            await log(LogLevel.DEBUG, f"Tool args: {json.dumps(args)}")

            async with span(
                "event.tool_call",
                attributes={"event_type": "tool_call", "tool": tool_name, "args": args},
            ):
                await log(LogLevel.DEBUG, "Emitting SSE event: tool_call")

            if not tool:
                error_msg = f"Tool '{qualified_name}' not found"
                await log(LogLevel.ERROR, error_msg)
                return {"type": "error", "message": error_msg}

            try:
                tool_callable = tool.func

                if tool.input_schema:
                    input_model = tool.input_schema(**args)
                    import inspect

                    sig = inspect.signature(tool_callable)
                    param_name = next(iter(sig.parameters.keys()))
                    call_args = {param_name: input_model}
                else:
                    call_args = args

                if asyncio.iscoroutinefunction(tool_callable):
                    result = await tool_callable(**call_args)
                else:
                    result = tool_callable(**call_args)

                if hasattr(result, "model_dump"):
                    data = result.model_dump()
                elif hasattr(result, "model_dump_json"):
                    data = json.loads(result.model_dump_json())
                else:
                    data = result

                await log(LogLevel.INFO, "Tool execution completed successfully")

                async with span(
                    "event.tool_result",
                    attributes={"event_type": "tool_result", "tool": tool_name, "success": True},
                ):
                    await log(LogLevel.DEBUG, "Emitting SSE event: tool_result")

                return {"type": "result", "data": data}

            except Exception as e:
                await log(LogLevel.ERROR, f"Tool execution failed: {e!s}")
                async with span(
                    "event.tool_result",
                    attributes={
                        "event_type": "tool_result",
                        "tool": tool_name,
                        "success": False,
                        "error": str(e),
                    },
                ):
                    await log(LogLevel.DEBUG, "Emitting SSE event: tool_result (error)")
                return {"type": "error", "message": str(e)}

    def _extract_clarification(self, code: str) -> dict | None:
        """Check if generated code is a clarification request, not executable logic.

        When the LLM detects missing user data, it generates a single
        synthesize_response({"status": "needs_clarification", ...}) call.
        This method detects that pattern so we can skip subprocess execution
        and return the question directly.

        Returns:
            The clarification dict if detected, None otherwise.
        """
        import ast as _ast

        try:
            tree = _ast.parse(code)
            if len(tree.body) != 1:
                return None
            stmt = tree.body[0]
            if not isinstance(stmt, _ast.Expr) or not isinstance(stmt.value, _ast.Call):
                return None
            func = stmt.value
            if not (isinstance(func.func, _ast.Name) and func.func.id == "synthesize_response"):
                return None
            if func.args:
                arg = _ast.literal_eval(func.args[0])
                if isinstance(arg, dict) and arg.get("status") == "needs_clarification":
                    return arg
        except Exception:
            pass
        return None

    @staticmethod
    def _extract_code(raw: str) -> str:
        """Strip markdown fences, leading prose, and trailing explanations.

        LLMs sometimes wrap output in ```python ... ``` blocks or prepend
        a sentence like "Here is the code:" despite being told not to.
        This method aggressively extracts the pure Python code.

        Priority:
          1. If a fenced code block exists, use its content.
          2. Otherwise strip any leading non-code lines (lines that
             don't look like Python) and trailing prose.

        Returns:
            Clean Python source string.
        """
        text = raw.strip()

        # ── 1. Extract from fenced code blocks (```python ... ``` or ``` ... ```)
        fence_pattern = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)
        match = fence_pattern.search(text)
        if match:
            return match.group(1).strip()

        # ── 2. Strip leading prose lines (before first Python-looking line)
        lines = text.split("\n")
        start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            # Heuristic: a Python line starts with a keyword, identifier,
            # comment, or string literal — not with markdown or prose.
            if (
                stripped.startswith(("#", "import ", "from ", "if ", "for ", "synthesize_response"))
                or "=" in stripped
                or (stripped[0].isalpha() and "(" in stripped)
            ):
                start_idx = i
                break
        else:
            # No Python-looking line found — return original
            return text

        # ── 3. Strip trailing prose (after last synthesize_response or assignment)
        end_idx = len(lines)
        for i in range(len(lines) - 1, start_idx - 1, -1):
            stripped = lines[i].strip()
            if not stripped:
                continue
            if (
                "synthesize_response" in stripped
                or "=" in stripped
                or stripped.startswith(("#", ")", "}", "]"))
            ):
                end_idx = i + 1
                break

        return "\n".join(lines[start_idx:end_idx]).strip()

    async def run(
        self,
        user_query: str,
        timeout: float = 60.0,
        thread_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> SandboxResult:
        """Generate code from a user query, execute it, and format the response.

        This is a single-shot execution: the LLM generates code once, executes it,
        and returns the result via synthesize_response().

        Example:
            >>> sandbox = Sandbox(team)
            >>> result = await sandbox.run("Get Apple stock price")
            >>> print(result.formatted_output)

        Args:
            user_query: What the user wants to do (e.g., "Get stock price")
            timeout: How long to wait for execution (default: 60 seconds)
            thread_id: Optional thread ID for loading conversation history
            context: Optional runtime context (e.g., store_id, user_tier) to pass to the LLM

        Returns:
            SandboxResult containing:
                - output: Raw JSON result
                - formatted_output: Human-readable response
                - success: True if code ran without errors
                - tool_calls: List of tools called during execution
        """
        from observability import LogLevel, log, span

        async with span("sandbox.run"):
            # Step 1: Generate code from user query
            await log(LogLevel.INFO, "Generating code from user query")
            code = await self.generate_parse_validate_code(
                user_query,
                thread_id=thread_id,
                context=context,
            )
            save_debug_artifact("generated_code.py", code)

            # Step 1.5: Check for clarification (missing data)
            clarification = self._extract_clarification(code)
            if clarification:
                await log(LogLevel.INFO, "Clarification needed — returning question to user")
                question = clarification.get("question", "Could you provide more details?")
                return SandboxResult(
                    output=json.dumps(clarification, ensure_ascii=False),
                    formatted_output=question,
                    success=True,
                    generated_code=code,
                )

            # Step 2: Build DSL workflow, then execute via the DSL engine
            await log(LogLevel.INFO, "Building DSL workflow from generated code")
            await self.build_dsl_workflow(code)
            await log(LogLevel.INFO, "Executing via DSL execution engine")
            result = await self.execute_dsl(timeout=timeout)
            result.generated_code = code

            # Step 3: Format the response into human-readable text
            if result.success and result.output:
                result.formatted_output = await self.format_response(user_query, result.output)

            return result

    async def format_response(self, user_query: str, raw_output: str) -> str:
        """Convert raw JSON tool results into a human-readable response.

        Args:
            user_query: Original user question (for context)
            raw_output: JSON string from synthesize_response()

        Returns:
            Human-readable formatted response
        """
        semantic = self._semantic_layer or self.provider.build_semantic_layer()

        # ── Gather agent instructions for synthesis context
        seen_instructions: set[str] = set()
        agent_instruction_parts: list[str] = []
        for domain in semantic.domains:
            if domain.instructions and domain.instructions.strip():
                instr = domain.instructions.strip()
                if instr not in seen_instructions:
                    seen_instructions.add(instr)
                    agent_instruction_parts.append(f"### {domain.id}\n{instr}")
        agent_instructions_text = (
            "\n\n".join(agent_instruction_parts)
            if agent_instruction_parts
            else "No additional agent instructions."
        )

        # Escape curly braces to prevent .format() from interpreting them
        escaped_output = raw_output.replace("{", "{{").replace("}", "}}")
        escaped_instructions = agent_instructions_text.replace("{", "{{").replace("}", "}}")

        prompt = RESPONSE_FORMAT_PROMPT.format(
            provider_name=semantic.provider_name,
            provider_instructions=semantic.provider_instructions or "",
            agent_instructions=escaped_instructions,
            user_query=user_query,
            tool_results=escaped_output,
        )

        response = await self.model.invoke([{"role": "user", "content": prompt}])
        content = getattr(response, "content", None) or ""

        # Print token usage
        usage = response.usage
        if usage:
            print(
                f"Tokens: in={usage.get('input_tokens', 0)} "
                f"out={usage.get('output_tokens', 0)} "
                f"thinking={usage.get('thoughts_tokens', 0)} "
                f"total={usage.get('total_tokens', 0)}"
            )

        final_output = content.strip() or "(no response generated)"
        save_debug_artifact("final_output.txt", final_output)

        return final_output

    async def _execute_planning_phase(
        self,
        user_query: str,
        semantic_layer: Any,
    ) -> tuple[str, str]:
        """
        Planning Phase -> returns filtered stubs + planner summary

        This phase is only applicable for teams.
        """

        planner_ctx = semantic_layer.get_planner_context()

        prompt = TEAM_PLANNER_PROMPT.format(
            team_name=planner_ctx["provider_name"],
            team_description=planner_ctx["provider_description"],
            team_instructions=planner_ctx["provider_instructions"],
            agents_section=planner_ctx["agents"],
            user_query=user_query,
        )

        response = await self.model.invoke([{"role": "user", "content": prompt}])
        print("Saved planner response to .debug/planner_response.txt")
        save_debug_artifact("planner_response.txt", response.content)

        if not hasattr(response, "content"):
            raise ValueError("Response content is required")

        content = response.content

        stripped_content = content.strip()
        if stripped_content.startswith("```"):
            stripped_content = stripped_content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        json_content = json.loads(stripped_content)
        planned_tool_slugs = set()

        for step in json_content.get("steps", []):
            agent = step.get("agent", "")
            tool_slug = step.get("tool_slug", "")
            if agent and tool_slug:
                planned_tool_slugs.add(f"{agent}.{tool_slug}")

        filtered_semantic_layer = semantic_layer.get_tool_stubs_by_tool_slugs(planned_tool_slugs)
        filtered_stubs = generate_stubs(filtered_semantic_layer)

        return filtered_stubs, json_content.get("summary", "")

    async def generate_parse_validate_code(
        self,
        user_query: str,
        thread_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Generate validated Python code from a user query.

        Args:
            user_query: The user's request/question
            thread_id: Optional thread ID for loading conversation history
            context: Optional runtime context dict to include in the prompt

        Returns:
            Validated Python code string.
        """

        if not context:
            raise ValueError("Context is required to generate code")

        # Step 1: Build semantic layer
        tool_definitions = context.get("tool_definitions")
        semantic_layer = self.provider.build_semantic_layer(tool_definitions)
        save_debug_artifact(
            "semantic_layer.json",
            json.dumps(semantic_layer.to_dict(), indent=2, ensure_ascii=False, default=str),
        )
        print("Saved semantic layer to .debug/semantic_layer.json")

        # Step 2: Planning Phase -> returns filtered stubs + planner summary
        # TODO: R&D on including this step in if condition based on the tool count.
        if self.provider.provider_type == "TEAM":
            stubs, planner_summary = await self._execute_planning_phase(user_query, semantic_layer)
            save_debug_artifact("planner_summary.txt", planner_summary)
            save_debug_artifact("stubs.txt", stubs)
            print("Saved planner summary to .debug/planner_summary.txt")
            print("Saved stubs to .debug/stubs.txt")
        else:
            stubs = generate_stubs(semantic_layer)

        # Step 3: Build prompt
        runtime_context = context.get("runtime_context", "")

        if self.provider.provider_type == "TEAM":
            prompt = TEAM_CODE_MODE_PROMPT.format(
                team_name=semantic_layer.provider_name,
                team_description=semantic_layer.provider_description,
                runtime_context=runtime_context,
                planner_summary=planner_summary,
                user_query=user_query,
                stubs=stubs,
            )
        else:
            prompt = AGENT_CODE_MODE_PROMPT.format(
                agent_name=semantic_layer.provider_name,
                agent_description=semantic_layer.provider_description,
                agent_instructions=semantic_layer.provider_instructions or "",
                runtime_context=runtime_context,
                planner_summary="",
                user_query=user_query,
                stubs=stubs,
            )

        save_debug_artifact("code_generation_prompt.txt", prompt)
        print("Saved code generation prompt to .debug/code_generation_prompt.txt")

        # Step 4: Invoke LLM
        messages: list[dict[str, Any]] = []
        if thread_id:
            messages.extend(await self.provider.get_history(thread_id))
        messages.append({"role": "system", "content": prompt})

        response = await self.model.invoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)

        save_debug_artifact("generated_code_response.txt", raw)
        print("Saved generated code response to .debug/generated_code_response.txt")
        # Step 5: Extract clean code and cache semantic layer for downstream
        code = self._extract_code(raw)
        self._semantic_layer = semantic_layer
        save_debug_artifact("generated_code.py", code)
        print("Saved generated code to .debug/generated_code.py")

        return code

    async def build_dsl_workflow(self, code: str) -> None:
        """Lower generated code into a DSL workflow graph, validate, and save artifact.

        Steps:
            1. Parse the code into an AST
            2. Validate the AST
            3. Build the DSL graph
            4. Validate the workflow self._dsl_workflow

        Args:
            code: Generated Python code string.

        Raises:
            ValueError: If DSL build or validation fails.
        """

        parsed_code = parse_code(code)
        if parsed_code.error or parsed_code.module is None:
            raise ValueError(f"DSL parse failed: {parsed_code.error}")

        validation_errors = validate(parsed_code.module)
        if validation_errors:
            raise ValueError(
                "DSL validation failed: " + "\n".join(e.message for e in validation_errors)
            )

        build_result = build_workflow(parsed_code.module)
        if not build_result.success:
            raise ValueError("DSL build failed: " + "\n".join(build_result.errors))

        self._dsl_workflow = build_result.workflow

        # save_debug_artifact("dsl_workflow.json", self._dsl_workflow.model_dump_json())
        # print("Saved DSL workflow to .debug/dsl_workflow.json")

    def _build_dsl_tool_map(self) -> dict[str, Any]:
        """Build {qualified_tool_name: async_callable} for the DSL executor.

        Wraps every entry in self._tool_map into an async callable with the
        signature  async def tool(**kwargs) -> dict  that the DSL runner expects.

        Returns:
            dict mapping "domain_id.tool_slug" → async callable for each tool.
        """
        import asyncio as _asyncio
        import inspect as _inspect

        if self._tool_map is None:
            self._tool_map = self._build_tool_map()

        dsl_tools: dict[str, Any] = {}

        for key, value in (self._tool_map or {}).items():
            # ── Skip MCP toolkit entries (keyed by mcp_slug, value = ("MCP", toolkit)).
            # Individual MCP tools are registered below via _mcp_tool_name_map.
            if not hasattr(value, "func"):
                continue  # not a local Tool — skip (MCP toolkits handled below)

            # ── Local Tool entry: key = "domain_id.tool_slug", value = Tool
            # hasattr guard above lets Pyright narrow `value` away from tuple.
            _tool = value

            async def _local_call(_t=_tool, **kwargs: Any) -> Any:
                from pydantic import ValidationError as _ValidationError

                func = _t.func
                input_schema = getattr(_t, "input_schema", None)
                if input_schema:
                    try:
                        input_model = input_schema(**kwargs)
                    except _ValidationError as exc:
                        # Return a structured error dict instead of raising so
                        # downstream tool steps and synthesize_response() still run.
                        errors = [
                            {"field": e["loc"][0] if e["loc"] else "?", "msg": e["msg"]}
                            for e in exc.errors()
                        ]
                        return {
                            "error": f"Input validation failed for {_t.name}: {exc.error_count()} error(s)",
                            "validation_errors": errors,
                            "inputs_received": {k: str(v) for k, v in kwargs.items()},
                        }
                    sig = _inspect.signature(func)
                    param_name = next(iter(sig.parameters.keys()))
                    call_args = {param_name: input_model}
                else:
                    call_args = kwargs

                if _asyncio.iscoroutinefunction(func):
                    result = await func(**call_args)
                else:
                    result = func(**call_args)

                if hasattr(result, "model_dump"):
                    return result.model_dump()
                return result

            dsl_tools[key] = _local_call

        # ── MCP tools: register under agent domain IDs.
        # After local tools are registered above, any tool in the semantic
        # layer that ISN'T in dsl_tools yet must be an MCP tool.  We find
        # the matching MCP toolkit from self._tool_map and create a callable.
        if self._semantic_layer:
            # Collect all registered MCP toolkits
            _mcp_toolkits: list[Any] = [
                v[1]
                for v in (self._tool_map or {}).values()
                if isinstance(v, tuple) and len(v) == 2 and v[0] == "MCP"
            ]

            for domain in self._semantic_layer.domains:
                for tool_schema in domain.tools:
                    tool_key_dash = f"{domain.id}.{tool_schema.slug}"
                    tool_key_under = f"{domain.id}.{tool_schema.slug.replace('-', '_')}"
                    # Already registered as local tool? skip.
                    if tool_key_dash in dsl_tools or tool_key_under in dsl_tools:
                        continue
                    # Unregistered → must be an MCP tool.
                    # tool_schema.name is the remote MCP tool name used by call_tool().
                    if not _mcp_toolkits:
                        continue
                    # Use the first available toolkit (works for single-MCP setups;
                    # for multi-MCP, we'd need to match by source).
                    _toolkit_obj = _mcp_toolkits[0]
                    _r = tool_schema.name
                    _tk_ref = _toolkit_obj

                    async def _mcp_call(_r=_r, _toolkit=_tk_ref, **kwargs: Any) -> Any:
                        result = await _toolkit.call_tool(_r, **kwargs)
                        try:
                            import json as _j

                            return _j.loads(result)
                        except (TypeError, ValueError):
                            return {"result": result}

                    dsl_tools[tool_key_dash] = _mcp_call
                    if tool_key_under != tool_key_dash:
                        dsl_tools[tool_key_under] = _mcp_call

        return dsl_tools

    async def execute_dsl(self, timeout: float = 60.0) -> SandboxResult:
        """Execute the compiled DSL workflow graph and return a SandboxResult.

        Requires build_dsl_workflow() to have been called first.

        Args:
            timeout: Maximum seconds for workflow execution.

        Returns:
            SandboxResult with output, tool_calls, and success flag.
        """

        workflow = self._dsl_workflow
        if workflow is None:
            return SandboxResult(
                output="",
                success=False,
                stderr="execute_dsl() called before build_dsl_workflow()",
            )

        tools = self._build_dsl_tool_map()

        try:
            result = await asyncio.wait_for(
                run_workflow(workflow, tools=tools),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return SandboxResult(
                output="",
                success=False,
                stderr=f"TimeoutError: DSL execution exceeded {timeout}s",
            )
        except Exception as exc:
            return SandboxResult(
                output="",
                success=False,
                stderr=str(exc),
            )

        # ── Map action steps to tool_calls for SandboxResult
        node_tool_map = {
            node.id: node.tool
            for node in workflow.nodes
            if isinstance(node, ActionNode)
        }

        tool_calls: list[dict[str, Any]] = [
            {
                "name": node_tool_map.get(step.node_id, step.label),
                "args": step.inputs,
                "result": step.outputs,
            }
            for step in result.steps
            if step.type == "action"
        ]

        if result.response is None:
            output = json.dumps(result.state, default=str, ensure_ascii=False)
        elif isinstance(result.response, (dict, list)):
            output = json.dumps(result.response, default=str, ensure_ascii=False)
        else:
            output = str(result.response)

        return SandboxResult(
            output=output,
            success=result.success,
            tool_calls=tool_calls,
            stderr=result.error or "",
        )
