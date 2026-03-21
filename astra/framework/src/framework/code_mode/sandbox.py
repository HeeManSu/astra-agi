"""
Sandbox for Team Code Mode.

This module provides:
1. Code generation from user queries using LLM
2. Code execution in isolated subprocess

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

from framework.code_mode.prompts import (
    AGENT_CODE_MODE_PROMPT,
    AGENT_PLANNER_PROMPT,
    RESPONSE_FORMAT_PROMPT,
    TEAM_CODE_MODE_PROMPT,
    TEAM_PLANNER_PROMPT,
)
from framework.code_mode.stub_generator import generate_runtime_stubs, generate_stubs


if TYPE_CHECKING:
    from framework.code_mode.provider import CodeModeProvider


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


def save_debug_artifact(filename: str, content: str) -> None:
    """Save a debug artifact to .debug/ (overwrite) and astra/evals/ (numbered).

    The .debug/ copy is always overwritten for quick access.
    The evals/ copy uses incrementing numbers (code_1.py, code_2.py, ...) to
    preserve history across runs for evaluation purposes.
    """
    # 1. Always overwrite the .debug/ copy
    os.makedirs(".debug", exist_ok=True)
    with open(f".debug/{filename}", "w") as f:
        f.write(content)

    # 2. Save numbered copy to evals/
    # Map debug filenames to eval folders + base names
    eval_map: dict[str, tuple[str, str]] = {
        "generated_code.py": ("generated_code", "code"),
        "stubs.py": ("generated_stubs", "stubs"),
        "prompt.txt": ("generated_prompt", "prompt"),
        "semantic_layer.json": ("generated_semantic_layer", "semantic_layer"),
        "execution_plan.json": ("generated_DSL", "dsl"),
    }

    entry = eval_map.get(filename)
    if not entry:
        return

    folder_name, base_name = entry
    # Walk up from CWD to find the astra/evals directory
    evals_dir = _find_evals_dir()
    if not evals_dir:
        return

    target_dir = os.path.join(evals_dir, folder_name)
    os.makedirs(target_dir, exist_ok=True)

    # Determine file extension
    ext = os.path.splitext(filename)[1]  # .py, .txt, .json

    # Find the next number by checking existing files
    existing = [
        f for f in os.listdir(target_dir) if f.startswith(base_name + "_") and f.endswith(ext)
    ]
    max_num = 0
    for f in existing:
        raw = f[len(base_name) + 1 : -len(ext)]
        if raw.isdigit():
            max_num = max(max_num, int(raw))

    next_num = max_num + 1
    numbered_filename = f"{base_name}_{next_num}{ext}"
    with open(os.path.join(target_dir, numbered_filename), "w") as f:
        f.write(content)


def _find_evals_dir() -> str | None:
    """Find the astra/evals directory by walking up from CWD."""
    current = os.path.abspath(".")
    for _ in range(10):  # max 10 levels up
        candidate = os.path.join(current, "astra", "evals")
        if os.path.isdir(candidate):
            return candidate
        # Also check if we're inside astra/ already
        candidate2 = os.path.join(current, "evals")
        if os.path.isdir(candidate2) and os.path.basename(current) == "astra":
            return candidate2
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


# RESULT DATACLASS
@dataclass
class SandboxResult:
    """Result from sandbox code execution.

    Attributes:
        output: Raw JSON output from synthesize_response()
        formatted_output: Human-readable formatted response (from LLM)
        success: Whether execution completed successfully
        exit_code: Process exit code (0 = success)
        tool_calls: List of tool calls made during execution
        stderr: Standard error output (for debugging)
        generated_code: The LLM-generated code that was executed
    """

    output: str
    formatted_output: str = ""
    success: bool = True
    exit_code: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stderr: str = ""
    generated_code: str = ""


# SANDBOX CLASS
class Sandbox:
    """Sandbox for Team code mode.

    Handles both code generation and execution:
    1. generate_parse_validate_code(): LLM generates Python code from user query
    2. execute(): Run code in isolated subprocess with tool routing
    3. run(): Convenience method that does both

    Example:
        >>> sandbox = Sandbox(team)
        >>> result = await sandbox.run("Process order ORD-001")
        >>> print(result.output)
        "Order ORD-001 processed successfully!"
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
        self._tool_map: dict[str, Any] | None = None  # Lazy-built tool lookup
        self._mcp_tool_name_map: dict[str, str] = {}  # "{mcp_slug}.{tool_slug}" -> remote MCP name
        self._semantic_layer: Any = (
            None  # Stored after build_semantic_layer() with tool_definitions
        )

    def _build_tool_map(self) -> dict[str, Any]:
        """Build a tool lookup map from provider's tools.

        Maps "domain_id.tool_slug" to Tool objects for local tools.
        Stores MCPToolkit objects keyed by mcp slug ("mcp_slug" -> ("MCP", toolkit)).

        For Agents: uses provider.tools directly
        For Teams: iterates through flat_members to get each agent's tools
        """
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
            for tool in tools:
                if isinstance(tool, Tool):
                    tool_slug = str(getattr(tool, "slug", "")).strip()
                    if not tool_slug:
                        raise ValueError("Local tool is missing slug in sandbox tool map build.")
                    qualified_name = f"{domain_id}.{tool_slug}"
                    existing = tool_map.get(qualified_name)
                    if existing is not None and existing is not tool:
                        raise ValueError(
                            f"Duplicate local tool key '{qualified_name}' detected while building tool map."
                        )
                    tool_map[qualified_name] = tool

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

    # CLARIFICATION DETECTION
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

    # PUBLIC API
    # The Sandbox has 3 public methods:
    #   - run(): All-in-one method (generate + execute)
    #   - generate_parse_validate_code(): Just generate code from user query
    #   - execute(): Just execute code in subprocess
    #
    # Use run() for simple cases. Use generate_parse_validate_code() + execute() separately
    # when you need to yield events between steps (e.g., for streaming).

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
                    exit_code=0,
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
        # Use semantic layer for metadata
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
        content = response.content if hasattr(response, "content") else str(response)

        # Print token usage
        usage = response.usage
        if usage:
            print(
                f"Tokens: in={usage.get('input_tokens', 0)} "
                f"out={usage.get('output_tokens', 0)} "
                f"thinking={usage.get('thoughts_tokens', 0)} "
                f"total={usage.get('total_tokens', 0)}"
            )

        # Save final output to debug file
        final_output = content.strip()
        save_debug_artifact("final_output.txt", final_output)

        return final_output

    async def _execute_planning_phase(
        self,
        user_query: str,
        semantic_layer: Any,
    ) -> tuple[str, str]:
        """Phase 1: Planning — select relevant agents/tools before code generation.

        Returns:
            Tuple of (filtered_tool_stubs, planner_summary).
        """
        # Build structured context with agent roles
        planner_ctx = semantic_layer.get_planner_context()
        save_debug_artifact(
            "planner_input.json",
            json.dumps(planner_ctx, indent=2, ensure_ascii=False),
        )
        print("  [planner] Saved to: .debug/planner_input.json")

        # Pick prompt based on provider type
        if self.provider.provider_type == "TEAM":
            prompt = TEAM_PLANNER_PROMPT.format(
                team_name=planner_ctx["provider_name"],
                team_description=planner_ctx["provider_description"],
                team_instructions=planner_ctx["provider_instructions"],
                agents_section=planner_ctx["agents"],
                user_query=user_query,
            )
        else:
            prompt = AGENT_PLANNER_PROMPT.format(
                agent_name=planner_ctx["provider_name"],
                agent_description=planner_ctx["provider_description"],
                agent_instructions=planner_ctx["provider_instructions"],
                tools_section=planner_ctx["agents"],
                user_query=user_query,
            )

        save_debug_artifact("planner_prompt.txt", prompt)
        print("  [planner] Saved to: .debug/planner_prompt.txt")

        print("  [planner] Invoking LLM...")
        response = await self.model.invoke([{"role": "user", "content": prompt}])

        content = response.content if hasattr(response, "content") else str(response)

        cleaned_content = content.strip()
        if cleaned_content.startswith("```"):
            cleaned_content = cleaned_content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        # Track token usage
        usage = response.usage
        if usage:
            print(
                f"  [planner] Tokens: "
                f"in={usage.get('input_tokens', 0)} "
                f"out={usage.get('output_tokens', 0)} "
                f"thinking={usage.get('thoughts_tokens', 0)} "
                f"total={usage.get('total_tokens', 0)}"
            )

        save_debug_artifact("planner_output.json", cleaned_content)
        print("  [planner] Saved to: .debug/planner_output.json")

        # Collect planned tool slugs as "agent.tool_slug"
        planned_tool_slugs = set()
        for step in json.loads(cleaned_content).get("steps", []):
            agent = step.get("agent", "")
            tool_slug = step.get("tool_slug", "")
            if agent and tool_slug:
                planned_tool_slugs.add(f"{agent}.{tool_slug}")

        # Filter semantic layer and generate stubs from filtered tools only
        filtered_layer = semantic_layer.get_tool_stubs_by_tool_slugs(planned_tool_slugs)
        filtered_stubs = generate_stubs(filtered_layer)

        save_debug_artifact("stubs_filtered.py", filtered_stubs)
        print("  [planner] Saved to: .debug/stubs_filtered.py")

        return filtered_stubs, cleaned_content

    async def generate_parse_validate_code(
        self,
        user_query: str,
        thread_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Ask the LLM to generate Python code based on a user query.

        This is the "brain" part of the sandbox. It:
            1. Gets the semantic layer (describes what tools are available)
            2. Generates Python stubs (code templates the LLM can use)
            3. Loads conversation history if thread_id is provided
            4. Builds a prompt explaining what to do
            5. Calls the LLM to generate the actual code

        The generated code will look something like:
            price = market_analyst.get_stock_price('AAPL')
            news = market_analyst.get_market_news('technology')
            synthesize_response({"price": price, "news": news})

        Args:
            user_query: What the user wants (e.g., "Get Apple stock info")
            thread_id: Optional thread ID for loading conversation history
            context: Optional runtime context dict to include in the prompt

        Returns:
            Python code as a string (ready to execute)
        """
        from framework.code_mode.compiler.ast_parser import parse_code, validate

        # Step 1: Build semantic layer
        tool_definitions = context.get("tool_definitions") if context else None
        if hasattr(self.provider, "build_semantic_layer"):
            semantic_layer = self.provider.build_semantic_layer(tool_definitions)
            self._semantic_layer = semantic_layer

        allowed_tools = {
            f"{domain.id}.{tool.slug}" for domain in semantic_layer.domains for tool in domain.tools
        }

        agent_count = len(semantic_layer.domains)
        total_tools = sum(len(d.tools) for d in semantic_layer.domains)
        print(f"  [code-gen] Semantic layer: {agent_count} agents, {total_tools} tools")
        save_debug_artifact(
            "semantic_layer.json",
            json.dumps(semantic_layer.to_dict(), indent=2, ensure_ascii=False),
        )
        print("  [code-gen] Saved to: .debug/semantic_layer.json")

        # Step 2: Planning phase (tool selection) → returns filtered stubs + planner summary
        planner_summary = ""
        stubs = ""
        if total_tools > 5:
            print("  [code-gen] Running planning phase...")
            stubs, planner_summary = await self._execute_planning_phase(user_query, semantic_layer)
        else:
            print(f"  [code-gen] Skipping planning ({total_tools} tools <= 5)")
            stubs = generate_stubs(semantic_layer)

        save_debug_artifact("stubs.py", stubs)
        print("  [code-gen] Saved to: .debug/stubs.py")

        # Step 4: Load conversation history ONLY for clarification follow-ups.
        # Normal queries skip history to avoid tool call name patterns
        # (e.g. "agent-slug.tool-name") misleading the LLM.
        messages: list[dict[str, Any]] = []
        if thread_id:
            storage = getattr(self.provider, "storage", None)
            if storage:
                recent = await storage.get_history_as_messages(thread_id, limit=2)
                has_prior_clarification = any(
                    "needs_clarification" in m.get("content", "")
                    for m in recent
                    if m.get("role") == "assistant"
                )
                if has_prior_clarification:
                    history = await storage.get_history_as_messages(thread_id, limit=8)
                    messages.extend(history)
                    print(
                        f"  [code-gen] Loaded {len(messages)} history messages (clarification follow-up)"
                    )

        # Step 5: Build prompt
        runtime_context_str = "No additional runtime context provided."
        if context:
            filtered_context = {
                key: value for key, value in context.items() if key != "tool_definitions"
            }
            if filtered_context:
                runtime_context_str = "\n".join(
                    [f"- {key}: {value}" for key, value in filtered_context.items()]
                )

        # Escape curly braces in dynamic content so Python's .format() does not
        # mis-interpret them as positional/keyword placeholder syntax.
        # This mirrors the same pattern used in format_response() above.
        escaped_stubs = stubs.replace("{", "{{").replace("}", "}}")
        escaped_planner = (
            (planner_summary or "No planning phase was executed.")
            .replace("{", "{{")
            .replace("}", "}}")
        )
        escaped_runtime = runtime_context_str.replace("{", "{{").replace("}", "}}")

        if self.provider.provider_type == "AGENT":
            agent_domain_id = semantic_layer.provider_id
            if semantic_layer.domains:
                agent_domain_id = semantic_layer.domains[0].id
                for domain in semantic_layer.domains:
                    if domain.id == semantic_layer.provider_id:
                        agent_domain_id = domain.id
                        break
            agent_class = re.sub(r"[^a-zA-Z0-9_]+", "_", agent_domain_id)
            prompt = AGENT_CODE_MODE_PROMPT.format(
                agent_name=semantic_layer.provider_name,
                agent_description=semantic_layer.provider_description
                or f"Agent: {semantic_layer.provider_name}",
                agent_instructions=semantic_layer.provider_instructions or "",
                agent_class=agent_class,
                stubs=escaped_stubs,
                runtime_context=escaped_runtime,
                planner_summary=escaped_planner,
                user_query=user_query,
            )
        else:
            prompt = TEAM_CODE_MODE_PROMPT.format(
                team_name=semantic_layer.provider_name,
                team_description=semantic_layer.provider_description or "",
                stubs=escaped_stubs,
                runtime_context=escaped_runtime,
                planner_summary=escaped_planner,
                user_query=user_query,
            )

        messages.append({"role": "user", "content": prompt})
        save_debug_artifact("prompt.txt", prompt)
        print("  [code-gen] Saved to: .debug/prompt.txt")

        # Step 6: Generate code with retry
        max_code_gen_attempts = 2
        code = ""
        last_error: str | None = None

        for attempt_idx in range(max_code_gen_attempts):
            if attempt_idx > 0:
                print(f"  [code-gen] Retry attempt {attempt_idx + 1}: {last_error}")
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous output was not valid Python.\n"
                            f"Error: {last_error}\n\n"
                            "Fix the code and output ONLY raw Python — "
                            "no markdown fences, no prose, no explanation.\n"
                            "Start directly with executable Python statements."
                        ),
                    }
                )

            print(f"  [code-gen] Invoking LLM (attempt {attempt_idx + 1})...")
            response = await self.model.invoke(messages)
            content = response.content if hasattr(response, "content") else str(response)

            # Track token usage
            usage = response.usage
            if usage:
                print(
                    f"  [code-gen] Tokens: "
                    f"in={usage.get('input_tokens', 0)} "
                    f"out={usage.get('output_tokens', 0)} "
                    f"thinking={usage.get('thoughts_tokens', 0)} "
                    f"total={usage.get('total_tokens', 0)}"
                )

            code = self._extract_code(content)
            save_debug_artifact("generated_code.py", code)
            save_debug_artifact(f"generated_code_attempt_{attempt_idx + 1}.py", content)
            print(f"  [code-gen] Saved to: .debug/generated_code_attempt_{attempt_idx + 1}.py")

            # Parse and validate
            parsed_ast = parse_code(code)

            if parsed_ast.error:
                last_error = str(parsed_ast.error)
                print(f"  [code-gen] AST parse failed: {last_error}")
                if attempt_idx < max_code_gen_attempts - 1:
                    continue
                raise SyntaxError(f"Generated code has syntax errors: {parsed_ast.error}")

            assert parsed_ast.module is not None and parsed_ast.ast_dump is not None

            errors = validate(parsed_ast.module, allowed_tools=allowed_tools)

            if errors:
                error_msgs = [f"  L{e.line}: {e.message}" for e in errors]
                error_summary = "\n".join(error_msgs)
                last_error = error_summary
                print(f"  [code-gen] Validation failed ({len(errors)} errors)")
                if attempt_idx < max_code_gen_attempts - 1:
                    continue
                raise ValueError(
                    f"Generated code failed validation ({len(errors)} errors):\n{error_summary}"
                )

            print("  [code-gen] Validation passed ✔")
            break

        return code

    async def build_dsl_workflow(self, code: str) -> None:
        """Lower generated code into a DSL workflow graph, validate, and save artifact.

        Steps:
            1. Parse the code into an AST via ast_parser.parse_code()
            2. Build the DSL graph from the AST via plan_builder.build()
            3. Validate the workflow via plan_validator.validate_plan()
            4. Save the full workflow as .debug/dsl.json (+ numbered eval copy)
            5. Store the workflow on self._dsl_workflow for downstream use

        Args:
            code: Generated Python code string.

        Raises:
            ValueError: If DSL build or validation fails.
        """
        from dataclasses import asdict

        from observability import LogLevel, log, span

        from framework.code_mode.compiler.ast_parser import parse_code
        from framework.code_mode.compiler.plan_builder import build as _build_dsl
        from framework.code_mode.compiler.plan_validator import validate_plan

        async with span("dsl.build"):
            result = parse_code(code)
            if result.ast_dump is not None:
                save_debug_artifact("parsed_code.py", result.ast_dump)
                print("  [code-gen] Saved to: .debug/parsed_code.py")
            if result.error or result.module is None:
                await log(LogLevel.ERROR, f"DSL parse failed: {result.error}")
                raise ValueError(f"DSL parse failed: {result.error}")

            # Extract tool whitelist from semantic layer so the builder
            # only classifies known domain.tool calls as ActionNodes.
            semantic = self._semantic_layer or self.provider.build_semantic_layer()
            allowed_tools = {
                f"{domain.id}.{tool.slug}" for domain in semantic.domains for tool in domain.tools
            }

            await log(LogLevel.INFO, "Lowering AST to DSL workflow graph")
            build_result = _build_dsl(result.module, name="workflow", allowed_tools=allowed_tools)

            if not build_result.ok:
                error_summary = "\n".join(f"  - {e}" for e in build_result.errors)
                await log(
                    LogLevel.ERROR,
                    f"DSL build failed ({len(build_result.errors)} errors):\n{error_summary}",
                )
                raise ValueError(
                    f"DSL lowering failed ({len(build_result.errors)} errors):\n{error_summary}"
                )

            workflow = build_result.workflow
            assert workflow is not None  # guaranteed by ok

            await log(
                LogLevel.DEBUG,
                f"DSL built: {workflow.summary()}",
                {
                    "nodes": len(workflow.nodes),
                    "edges": len(workflow.edges),
                    "entry": workflow.entry,
                },
            )

            # Validate the DSL workflow
            await log(LogLevel.INFO, "Validating DSL workflow")
            validation = validate_plan(workflow)

            if validation.warnings:
                for w in validation.warnings:
                    await log(LogLevel.WARN, f"DSL warning: {w}")

            if not validation.ok:
                error_summary = "\n".join(f"  - {e}" for e in validation.errors)
                await log(
                    LogLevel.ERROR,
                    f"DSL validation failed ({len(validation.errors)} errors):\n{error_summary}",
                )
                raise ValueError(
                    f"DSL validation failed ({len(validation.errors)} errors):\n{error_summary}"
                )

            await log(LogLevel.INFO, "DSL validation passed")

            # Save full DSL artifact using dataclasses.asdict for complete dump
            save_debug_artifact(
                "execution_plan.json",
                json.dumps(asdict(workflow), indent=2, ensure_ascii=False, default=str),
            )
            await log(LogLevel.DEBUG, "Saved to: .debug/dsl.json")

            # Store workflow on sandbox for downstream use
            self._dsl_workflow = workflow

    async def execute(self, code: str, timeout: float = 60.0) -> SandboxResult:
        """Run Python code in an isolated subprocess.

        This is the "execution engine" of the sandbox. It runs code safely by:
            1. Building a complete Python script (runtime + stubs + your code)
            2. Starting a subprocess to run the script
            3. Handling tool calls from the subprocess via IPC (stdin/stdout)
            4. Returning the final result

        Why a subprocess?
            - Isolation: The code can't access the parent process's memory
            - Safety: If the code crashes, it doesn't crash the main app
            - Timeout: We can kill the subprocess if it runs too long

        How IPC (Inter-Process Communication) works:
            Subprocess wants to call a tool:
              1. Subprocess prints JSON: {"type": "call_tool", "name": "market_analyst.get_stock_price", "args": {...}}
              2. Parent (us) reads this from subprocess stdout
              3. Parent executes the actual tool and gets the result
              4. Parent sends result back via subprocess stdin
              5. Subprocess receives result and continues

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

            # Step 1: Build the complete executable code
            # This combines: runtime bridge functions + agent stub classes + LLM code
            full_code = self._build_full_code(code)
            await log(
                LogLevel.DEBUG,
                f"Built full code with runtime bridge ({len(full_code)} chars)",
                {"code_length": len(full_code)},
            )

            # Save full runtime code for debugging as requested
            save_debug_artifact("full_runtime_code.py", full_code)
            await log(LogLevel.DEBUG, "Saved full runtime code to: .debug/full_runtime_code.py")

            # Step 2: Start an isolated subprocess
            # We use Python's asyncio to run subprocess non-blocking
            # stdin/stdout/stderr are all piped so we can communicate with it
            # Use 100MB limit for large tool responses (default is 64KB)
            large_limit = 100 * 1024 * 1024  # 100MB
            proc = await asyncio.create_subprocess_exec(
                sys.executable,  # Use the same Python interpreter
                "-c",  # Run code from command line argument
                full_code,  # The complete code to execute
                stdin=asyncio.subprocess.PIPE,  # We'll send tool results here
                stdout=asyncio.subprocess.PIPE,  # We'll read tool calls from here
                stderr=asyncio.subprocess.PIPE,  # Capture errors for debugging
                limit=large_limit,  # Buffer limit for StreamReader (default 64KB)
            )

            await log(LogLevel.DEBUG, f"Subprocess started with PID: {proc.pid}")
            update_span({"subprocess_id": proc.pid})

            try:
                # Step 3: Monitor the subprocess and handle tool calls
                # This loop reads stdout, executes tools, and sends responses back
                await log(LogLevel.DEBUG, "Monitoring subprocess for tool calls")
                result = await asyncio.wait_for(
                    self._monitor_subprocess(proc),
                    timeout=timeout,  # Kill if it takes too long
                )
                return result

            except asyncio.TimeoutError:
                # If the subprocess takes too long, we kill it
                # This prevents infinite loops or slow operations from hanging
                proc.kill()
                await proc.wait()  # Clean up the dead process
                await log(LogLevel.ERROR, f"Execution timed out after {timeout}s")
                return SandboxResult(
                    output="Execution timed out",
                    success=False,
                    exit_code=-1,
                    stderr="TimeoutError: Execution exceeded time limit",
                )

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
        """Execute the compiled ExecutionPlan via the DSL execution engine.

        Requires build_dsl_workflow() to have been called first.

        Args:
            timeout: Maximum seconds for workflow execution.

        Returns:
            SandboxResult with output, tool_calls, and success flag.
        """
        import asyncio as _asyncio

        from framework.code_mode.executor import run_plan

        if not getattr(self, "_dsl_workflow", None):
            return SandboxResult(
                output="",
                success=False,
                stderr="execute_dsl() called before build_dsl_workflow(). "
                "Call build_dsl_workflow(code) first.",
            )

        dsl_tools = self._build_dsl_tool_map()

        try:
            exec_result = await _asyncio.wait_for(
                run_plan(
                    self._dsl_workflow,
                    initial_state={},
                    tools=dsl_tools,
                ),
                timeout=timeout,
            )
        except _asyncio.TimeoutError:
            return SandboxResult(
                output="",
                success=False,
                exit_code=-1,
                stderr=f"TimeoutError: DSL execution exceeded {timeout}s",
            )
        except Exception as exc:
            return SandboxResult(
                output="",
                success=False,
                stderr=str(exc),
            )

        # ── Convert ExecutionResult → SandboxResult
        # Build node_id → tool name lookup from the workflow
        from framework.code_mode.compiler.nodes import ActionNode

        node_tool_map: dict[str, str] = {}
        for node in self._dsl_workflow.nodes:
            if isinstance(node, ActionNode):
                node_tool_map[node.id] = node.tool

        tool_calls: list[dict[str, Any]] = [
            {
                "name": node_tool_map.get(entry.node_id, entry.label),
                "args": entry.inputs,
                "result": entry.outputs,
            }
            for entry in exec_result.journal
            if entry.node_type == "action"
        ]

        raw_output = exec_result.response or json.dumps(
            exec_result.state, default=str, ensure_ascii=False
        )

        print(
            f"DSL execution complete — status={exec_result.status.value}, "
            f"nodes={len(exec_result.journal)}, tokens={exec_result.total_token_usage}"
        )

        # Surface node-level errors
        if not exec_result.ok:
            if exec_result.error:
                print(f"DSL FAILED: {exec_result.error}")
            for entry in exec_result.journal:
                if entry.status == "error" and entry.error:
                    print(f"  Node '{entry.label}' ({entry.node_id}) failed: {entry.error}")

        return SandboxResult(
            output=raw_output,
            success=exec_result.ok,
            exit_code=0 if exec_result.ok else 1,
            tool_calls=tool_calls,
            stderr=exec_result.error or "",
        )

    def _build_full_code(self, code: str) -> str:
        """Assemble the complete Python script for the subprocess.

        The subprocess needs three things to work:
            1. Runtime Bridge: Functions that let the subprocess talk to us
            2. Agent Stubs: Classes that look like agents but route calls to us
            3. LLM Code: The actual logic generated by the LLM

        The final script looks like this:
            ┌─────────────────────────────────────┐
            │ Runtime Bridge                      │  <- call_tool(), synthesize_response()
            │  - call_tool(name, **kwargs)        │
            │  - synthesize_response(message)     │
            ├─────────────────────────────────────┤
            │ Agent Stub Classes                  │  <- class market_analyst:
            │  - class market_analyst:            │        def get_stock_price(symbol):
            │      def get_stock_price(symbol):   │            return call_tool(...)
            │          return call_tool(...)      │
            ├─────────────────────────────────────┤
            │ LLM Generated Code                  │  <- The actual logic
            │  - price = market_analyst...        │
            │  - synthesize_response(...)         │
            └─────────────────────────────────────┘

        Args:
            code: Python code from the LLM

        Returns:
            Complete executable Python script as a single string
        """
        parts = []

        # Part 1: Runtime Bridge
        # These are the IPC functions that let subprocess talk to parent
        # call_tool() sends a request to parent and waits for response
        # synthesize_response() sends the final answer and exits
        parts.append(RUNTIME_BRIDGE)

        # Part 2: Agent Stub Classes
        # These make agent.tool() calls work by routing them to call_tool()
        # Example: market_analyst.get_stock_price('AAPL')
        #          -> call_tool("market_analyst.get_stock_price", symbol="AAPL")
        # Use stored semantic layer (with tool_definitions) if available, else build fresh
        semantic_layer = self._semantic_layer or self.provider.build_semantic_layer()
        runtime_stubs = generate_runtime_stubs(semantic_layer)
        parts.append(runtime_stubs)

        # Part 3: LLM Generated Code
        # This is the actual logic that uses the stubs above
        parts.append("\n# ═══════ LLM Generated Code ═══════\n")
        parts.append(code)

        # Combine everything into one script
        full_code = "\n".join(parts)

        return full_code

    # PRIVATE: IPC Loop
    # These methods handle communication with the subprocess.

    async def _monitor_subprocess(self, proc: asyncio.subprocess.Process) -> SandboxResult:
        """Listen to subprocess stdout and handle messages.

        This is the heart of the IPC system. It:
            1. Reads each line from subprocess stdout
            2. Checks if it's a JSON message (tool call or final response)
            3. If tool call: execute the tool and send result back
            4. If synthesize: save the final response
            5. Otherwise: just collect as regular output (print statements)

        The subprocess communicates via JSON messages:
            Tool call:  {"type": "call_tool", "name": "market_analyst.get_stock_price", "args": {"symbol": "AAPL"}}
            Response:   {"type": "synthesize", "message": "The stock price is $150.25"}

        Args:
            proc: The running subprocess to monitor

        Returns:
            SandboxResult with the final output and metadata
        """
        output_lines: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        tool_results_for_debug: list[dict[str, Any]] = []
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

                        # Store result in tool_calls for history/metrics
                        if response.get("type") == "error":
                            request["error"] = response.get("message")
                        else:
                            request["result"] = response.get("data")

                        # Collect for .debug/tool_results.json
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

                        # Save tool results for debugging
                        try:
                            os.makedirs(".debug", exist_ok=True)
                            import pathlib as _pathlib

                            _pathlib.Path(".debug/tool_results.json").write_text(
                                json.dumps(tool_results_for_debug, indent=2, default=str)
                            )
                        except Exception:
                            pass

                        # Send response back to subprocess
                        proc.stdin.write((json.dumps(response) + "\n").encode("utf-8"))
                        await proc.stdin.drain()

                    elif msg_type == "synthesize":
                        # Final response from subprocess
                        final_response = request.get("message", "")

                    continue  # Don't add JSON to output

                except json.JSONDecodeError:
                    # Log the failed JSON parsing for debugging
                    pass

            # Regular output line (print statements, etc.)
            output_lines.append(text)

        from observability import LogLevel, log, span

        # Wait for process to exit
        await proc.wait()

        # Read stderr for debugging
        stderr = ""
        if proc.stderr:
            stderr_bytes = await proc.stderr.read()
            stderr = stderr_bytes.decode("utf-8", errors="replace")

        # Determine final output
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

        # Emit completion event span as requested
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
            exit_code=proc.returncode or 0,
            tool_calls=tool_calls,
            stderr=stderr,
        )

    async def _handle_tool_call(self, request: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call and return the result.

        Looks up the tool in _tool_map and executes it.
        Supports both local tools (Tool objects) and MCP tools (MCPToolkit).

        Args:
            request: Tool call request with "name" and "args"

        Returns:
            Response dict with "type" and "data" or "message"
        """
        from observability import LogLevel, SpanKind, log, span

        name = request.get("name", "")
        args = request.get("args", {})

        # Parse qualified tool key by splitting on the LAST dot.
        # This supports module identifiers that may include dots.
        if "." not in name:
            return {"type": "error", "message": f"Invalid tool name format: '{name}'"}
        module_name, tool_name = name.rsplit(".", 1)
        if not module_name or not tool_name:
            return {"type": "error", "message": f"Invalid tool name format: '{name}'"}

        # First check if module_name is an MCP toolkit
        mcp_entry = self._get_tool(module_name)
        is_mcp = isinstance(mcp_entry, tuple) and len(mcp_entry) == 2 and mcp_entry[0] == "MCP"

        if is_mcp:
            # MCP tool execution
            assert mcp_entry is not None  # Guaranteed by is_mcp check above
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

                    # MCP returns string, try to parse as JSON
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

        # Local tool execution
        qualified_name = f"{module_name}.{tool_name}"
        tool = self._get_tool(qualified_name)

        # Determine execution type safely
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

            # Emit SSE event span for frontend real-time updates as requested
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
                # Get the callable function from Tool
                tool_callable = tool.func

                # Construct Pydantic input model if available
                if tool.input_schema:
                    input_model = tool.input_schema(**args)
                    # Get actual parameter name from function signature
                    import inspect

                    sig = inspect.signature(tool_callable)
                    param_name = next(iter(sig.parameters.keys()))  # First (and only) parameter
                    call_args = {param_name: input_model}
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

                await log(LogLevel.INFO, "Tool execution completed successfully")

                # Emit result event span
                async with span(
                    "event.tool_result",
                    attributes={"event_type": "tool_result", "tool": tool_name, "success": True},
                ):
                    await log(LogLevel.DEBUG, "Emitting SSE event: tool_result")

                return {"type": "result", "data": data}

            except Exception as e:
                await log(LogLevel.ERROR, f"Tool execution failed: {e!s}")
                # Emit error event span
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
