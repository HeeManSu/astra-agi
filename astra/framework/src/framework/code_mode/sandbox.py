"""
Sandbox for Team Code Mode.

This module provides:
1. Code generation from user queries using LLM
2. Code execution in isolated subprocess

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    PARENT PROCESS                           │
    │  Sandbox.run(query)                                         │
    │    ├── generate_code() → LLM → Python code                  │
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
import re
import sys
from typing import TYPE_CHECKING, Any

from framework.code_mode.prompts import TEAM_CODE_MODE_PROMPT
from framework.code_mode.stub_generator import generate_stubs


if TYPE_CHECKING:
    from framework.team.team import Team


# RUNTIME BRIDGE
# This code is injected into the subprocess BEFORE the LLM-generated code.
# It provides:
#   - call_tool(): Sends tool requests to parent via stdout, reads response from stdin
#   - synthesize_response(): Returns final answer to parent and exits

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
    response_line = sys.stdin.readline()
    if not response_line:
        raise RuntimeError("No response from parent process")

    response = json.loads(response_line)

    # Check for error
    if response.get("type") == "error":
        raise RuntimeError(response.get("message", "Tool execution failed"))

    return response.get("data", {})


def synthesize_response(message: str):
    """Return final response to parent and exit.

    This ends the subprocess execution and sends the final answer.

    Args:
        message: Final response message to user
    """
    request = {"type": "synthesize", "message": str(message)}
    print(json.dumps(request), flush=True)
    sys.exit(0)

'''


# RESULT DATACLASS
@dataclass
class SandboxResult:
    """Result from sandbox code execution.

    Attributes:
        output: Final output from synthesize_response() or stdout
        success: Whether execution completed successfully
        exit_code: Process exit code (0 = success)
        tool_calls: List of tool calls made during execution
        stderr: Standard error output (for debugging)
        generated_code: The LLM-generated code that was executed
    """

    output: str
    success: bool
    exit_code: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stderr: str = ""
    generated_code: str = ""


# SANDBOX CLASS
class Sandbox:
    """Sandbox for Team code mode.

    Handles both code generation and execution:
    1. generate_code(): LLM generates Python code from user query
    2. execute(): Run code in isolated subprocess with tool routing
    3. run(): Convenience method that does both

    Example:
        >>> sandbox = Sandbox(team)
        >>> result = await sandbox.run("Process order ORD-001")
        >>> print(result.output)
        "Order ORD-001 processed successfully!"
    """

    def __init__(self, team: Team):
        """Initialize sandbox with Team.

        Args:
            team: Team instance to generate/execute code for
        """
        self.team = team
        self.model = team.model
        # Tool registry is accessed via team.tool_registry (lazily built)

    # PUBLIC API
    async def run(self, user_query: str, timeout: float = 60.0) -> SandboxResult:
        """Generate code and execute it.

        This is the main entry point that:
        1. Generates Python code from user query
        2. Executes the code in an isolated subprocess
        3. Returns the final result

        Args:
            user_query: User's request/task
            timeout: Maximum execution time in seconds

        Returns:
            SandboxResult with output and metadata
        """
        # Step 1: Generate code from LLM
        code = await self.generate_code(user_query)

        # Step 2: Execute code in subprocess
        result = await self.execute(code, timeout=timeout)
        result.generated_code = code

        return result

    async def generate_code(self, user_query: str) -> str:
        """Generate Python code from user query.

        Args:
            user_query: User's request/task

        Returns:
            Generated Python code as string
        """
        # Build stubs from semantic layer
        stubs = generate_stubs(self.team.semantic_layer)

        # Build prompt
        prompt = TEAM_CODE_MODE_PROMPT.format(
            team_name=self.team.name,
            team_description=self.team.description or "",
            team_instructions=self.team.instructions or "",
            stubs=stubs,
            user_query=user_query,
        )

        # Call LLM
        response = await self.model.invoke([{"role": "user", "content": prompt}])

        # Extract code from response
        content = response.content if hasattr(response, "content") else str(response)
        return self._extract_code(content)

    async def execute(self, code: str, timeout: float = 60.0) -> SandboxResult:
        """Execute code in isolated subprocess.

        Creates a subprocess with:
        - Runtime bridge (call_tool, synthesize_response)
        - Agent stub classes (route to call_tool)
        - LLM-generated code

        Monitors stdout for tool calls and handles them.

        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds

        Returns:
            SandboxResult with output and metadata
        """
        # Build complete code: runtime + stubs + user code
        full_code = self._build_full_code(code)

        # Spawn isolated subprocess
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            full_code,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            # Monitor stdout and handle tool calls
            result = await asyncio.wait_for(
                self._monitor_subprocess(proc),
                timeout=timeout,
            )
            return result

        except asyncio.TimeoutError:
            # Kill subprocess if it exceeds timeout
            proc.kill()
            await proc.wait()
            return SandboxResult(
                output="Execution timed out",
                success=False,
                exit_code=-1,
                stderr="TimeoutError: Execution exceeded time limit",
            )

    # PRIVATE: Code Generation
    def _extract_code(self, response: str) -> str:
        """Extract Python code from LLM response.

        LLM responses typically wrap code in markdown code blocks:
            ```python
            import json

            result = tool.call()
            ```

        This method extracts just the code inside those blocks.
        """
        # Pattern 1: Match ```python\n<code>``` (with optional whitespace)
        # Extracts code between ```python and closing ```
        # re.DOTALL makes . match newlines too
        match = re.search(r"```python\s*\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Pattern 2: Match ```\n<code>``` (no language specified)
        # Fallback for code blocks without "python" label
        match = re.search(r"```\s*\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Pattern 3: No code block found
        # Assume the entire response is raw code, but strip any trailing ```
        code = response.strip()
        # Remove any stray markdown fences
        if code.endswith("```"):
            code = code[:-3].strip()
        if code.startswith("```python"):
            code = code[9:].strip()
        elif code.startswith("```"):
            code = code[3:].strip()
        return code

    # PRIVATE: Runtime Bridge & Stubs
    def _build_full_code(self, user_code: str) -> str:
        """Build complete code to execute in subprocess.

        Combines:
        1. Runtime bridge (call_tool, synthesize_response)
        2. Agent stub classes (each agent becomes a class with tool methods)
        3. User's LLM-generated code
        """
        parts = []

        # Part 1: Runtime bridge
        parts.append(RUNTIME_BRIDGE)

        # Part 2: Agent stub classes
        parts.append(self._generate_stub_classes())

        # Part 3: User code
        parts.append("\n# ═══════ LLM Generated Code ═══════\n")
        parts.append(user_code)

        full_code = "\n".join(parts)
        print("DEBUG: Full Execution Code:\n" + "=" * 40 + "\n" + full_code + "\n" + "=" * 40)
        return full_code

    def _generate_stub_classes(self) -> str:
        """Generate stub classes for each agent in the team.

        Each agent becomes a class with static methods for its tools.
        These methods call call_tool() which routes to the parent process.

        Example output:
            class inventory:
                @staticmethod
                def check_inventory(product_ids):
                    return call_tool("inventory.check_inventory", product_ids=product_ids)
        """
        lines = ["\n# ═══════ Agent Stub Classes ═══════\n"]

        # Use flat members to support nested teams
        for member in self.team.flat_members:
            # Use agent id/name as class name (sanitized)
            agent = member.agent
            raw_name = member.id or member.name or getattr(agent, "name", None) or "unknown"
            class_name = raw_name.replace("-", "_").replace(" ", "_").lower()

            lines.append(f"class {class_name}:")
            lines.append(f'    """Agent: {member.name or raw_name}"""')

            # Add tool methods - get from underlying agent
            tools = getattr(agent, "tools", []) or []
            if not tools:
                lines.append("    pass")

            for tool in tools:
                tool_name = getattr(tool, "name", str(tool))
                full_name = f"{class_name}.{tool_name}"

                # Get parameter names
                params = self._get_tool_params(tool)
                param_str = ", ".join(params) if params else ""

                lines.append("    @staticmethod")
                lines.append(f"    def {tool_name}({param_str}):")

                # Generate call_tool body
                if params:
                    args = ", ".join(f"{p}={p}" for p in params)
                    lines.append(f'        return call_tool("{full_name}", {args})')
                else:
                    lines.append(f'        return call_tool("{full_name}")')

            lines.append("")

        return "\n".join(lines)

    def _get_tool_params(self, tool: Any) -> list[str]:
        """Extract parameter names from tool."""
        # Try Pydantic input_schema
        if hasattr(tool, "input_schema") and tool.input_schema:
            schema = tool.input_schema
            if hasattr(schema, "model_fields"):
                return list(schema.model_fields.keys())

        # Try function signature
        if hasattr(tool, "func"):
            import inspect

            sig = inspect.signature(tool.func)
            return [p for p in sig.parameters if p != "self"]

        return []

    # PRIVATE: Subprocess Execution
    async def _monitor_subprocess(self, proc: asyncio.subprocess.Process) -> SandboxResult:
        """Monitor subprocess stdout and handle tool calls.

        This is the core IPC loop:
        1. Read lines from subprocess stdout
        2. If line is JSON with type="call_tool", execute tool and respond
        3. If line is JSON with type="synthesize", capture final response
        4. Otherwise, collect as regular output

        Args:
            proc: Running subprocess

        Returns:
            SandboxResult with output and metadata
        """
        output_lines: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        final_response: str | None = None

        assert proc.stdout is not None
        assert proc.stdin is not None

        while True:
            # Read line from subprocess stdout
            line = await proc.stdout.readline()

            # Empty line means process ended
            if not line:
                break

            text = line.decode("utf-8", errors="replace").strip()

            # Check if this is a JSON message (tool call or synthesize)
            if text.startswith("{") and text.endswith("}"):
                try:
                    request = json.loads(text)
                    msg_type = request.get("type")

                    if msg_type == "call_tool":
                        # Tool call request from subprocess
                        tool_calls.append(request)

                        # Execute the tool and send response
                        response = await self._handle_tool_call(request)
                        response_json = json.dumps(response) + "\n"
                        proc.stdin.write(response_json.encode())
                        await proc.stdin.drain()

                    elif msg_type == "synthesize":
                        # Final response from subprocess
                        final_response = request.get("message", "")

                    continue  # Don't add JSON to output

                except json.JSONDecodeError:
                    pass  # Not valid JSON, treat as regular output

            # Regular output line (print statements, etc.)
            output_lines.append(text)

        # Wait for process to exit
        await proc.wait()

        # Read stderr for debugging
        stderr = ""
        if proc.stderr:
            stderr_bytes = await proc.stderr.read()
            stderr = stderr_bytes.decode("utf-8", errors="replace")

        # Determine final output
        output = final_response if final_response else "\n".join(output_lines)

        return SandboxResult(
            output=output,
            success=proc.returncode == 0,
            exit_code=proc.returncode or 0,
            tool_calls=tool_calls,
            stderr=stderr,
        )

    async def _handle_tool_call(self, request: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call and return the result.

        Looks up the tool in _tool_map and executes it.

        Args:
            request: Tool call request with "name" and "args"

        Returns:
            Response dict with "type" and "data" or "message"
        """
        name = request.get("name", "")
        args = request.get("args", {})

        # Parse "module.tool_name" format
        parts = name.split(".")
        if len(parts) != 2:
            return {"type": "error", "message": f"Invalid tool name format: '{name}'"}

        module_name, tool_name = parts

        # Look up tool in registry by qualified name (module.tool_name)
        # The registry now stores tools with qualified names to allow same tool on multiple agents
        qualified_name = f"{module_name}.{tool_name}"
        tool_spec = self.team.tool_registry.get(qualified_name)

        if not tool_spec:
            return {"type": "error", "message": f"Tool '{qualified_name}' not found"}

        try:
            # Get the callable from ToolSpec
            tool_callable = tool_spec.invoke

            # If invoke is a Tool object, get its func
            if hasattr(tool_callable, "func"):
                tool_callable = tool_callable.func

            # Construct Pydantic input model if available
            # Tools expect a single `input` parameter with a Pydantic model
            if tool_spec.input_schema:
                input_model = tool_spec.input_schema(**args)
                call_args = {"input": input_model}
            else:
                call_args = args

            # Execute tool (may be sync or async)
            if asyncio.iscoroutinefunction(tool_callable):
                result = await tool_callable(**call_args)
            else:
                result = tool_callable(**call_args)

            # Serialize result
            if hasattr(result, "model_dump"):
                data = result.model_dump()
            elif hasattr(result, "model_dump_json"):
                data = json.loads(result.model_dump_json())
            else:
                data = result

            return {"type": "result", "data": data}

        except Exception as e:
            return {"type": "error", "message": str(e)}
