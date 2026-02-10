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
import os
import sys
from typing import TYPE_CHECKING, Any

from framework.code_mode.prompts import (
    AGENT_CODE_MODE_PROMPT,
    RESPONSE_FORMAT_PROMPT,
    TEAM_CODE_MODE_PROMPT,
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
    """Save a debug artifact to the .debug directory."""
    os.makedirs(".debug", exist_ok=True)
    with open(f".debug/{filename}", "w") as f:
        f.write(content)


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
    1. generate_code(): LLM generates Python code from user query
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
        self._semantic_layer: Any = (
            None  # Stored after build_semantic_layer() with tool_definitions
        )

    def _build_tool_map(self) -> dict[str, Any]:
        """Build a tool lookup map from provider's tools.

        Maps "agent_id.tool_name" to Tool objects for local tools.
        Stores MCPToolkit objects separately in _mcp_toolkits dict.

        For Agents: uses provider.tools directly
        For Teams: iterates through flat_members to get each agent's tools
        """
        from framework.tool import Tool
        from framework.tool.mcp.toolkit import MCPToolkit

        tool_map: dict[str, Any] = {}

        def register_tools(tools: list, agent_id: str) -> None:
            """Register tools from a list (local or MCP)."""
            nonlocal tool_map
            for tool in tools:
                if isinstance(tool, Tool):
                    # Local tool
                    qualified_name = f"{agent_id}.{tool.name}"
                    tool_map[qualified_name] = tool
                elif isinstance(tool, MCPToolkit):
                    # MCP toolkit - store with SANITIZED name to match call_tool routing
                    # e.g., "brave-search" -> "brave_search"
                    mcp_id = tool.name.lower().replace("-", "_").replace(" ", "_")
                    if mcp_id not in tool_map:
                        # Store as ("MCP", toolkit) tuple to distinguish from local tools
                        tool_map[mcp_id] = ("MCP", tool)

        if self.provider.provider_type == "AGENT":
            # Agent: use provider's tools directly
            semantic = self._semantic_layer or self.provider.build_semantic_layer()
            agent_id = semantic.provider_name.lower().replace(" ", "_").replace("-", "_")
            tools = getattr(self.provider, "tools", None) or []
            register_tools(tools, agent_id)
        else:
            # Team: iterate through member agents
            flat_members = getattr(self.provider, "flat_members", [])
            for member in flat_members:
                agent = member.agent
                agent_id = member.name.lower().replace(" ", "_").replace("-", "_")
                tools = getattr(agent, "tools", None) or []
                register_tools(tools, agent_id)

        return tool_map

    def _get_tool(self, qualified_name: str) -> Any | None:
        """Look up a tool by qualified name.

        Args:
            qualified_name: Full tool name (e.g., "market_analyst.get_stock_price")

        Returns:
            Tool if found, None otherwise
        """
        if self._tool_map is None:
            self._tool_map = self._build_tool_map()
        return self._tool_map.get(qualified_name)

    # PUBLIC API
    # The Sandbox has 3 public methods:
    #   - run(): All-in-one method (generate + execute)
    #   - generate_code(): Just generate code from user query
    #   - execute(): Just execute code in subprocess
    #
    # Use run() for simple cases. Use generate_code() + execute() separately
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
            code = await self.generate_code(
                user_query,
                thread_id=thread_id,
                context=context,
            )
            save_debug_artifact("generated_code.py", code)

            # Step 2: Execute the generated code
            await log(LogLevel.INFO, "Executing generated code")
            result = await self.execute(code, timeout=timeout)
            result.generated_code = code

            # Step 3: Format the response into human-readable text
            if result.success and result.output:
                result.formatted_output = await self.format_response(user_query, result.output)

            return result

    async def format_response(self, user_query: str, raw_output: str) -> str:
        """Convert raw JSON tool results into a human-readable response.

        This is the second LLM call that takes raw tool outputs and formats
        them into a natural language response that answers the user's question.

        Example:
            Input:  {"price": 150.25, "symbol": "AAPL", "change": 2.3}
            Output: "Apple (AAPL) is trading at $150.25, up 2.3% today."

        Args:
            user_query: Original user question (for context)
            raw_output: JSON string from synthesize_response()

        Returns:
            Human-readable formatted response
        """
        # Use semantic layer for metadata
        semantic = self._semantic_layer or self.provider.build_semantic_layer()

        # Escape curly braces in JSON to prevent .format() from interpreting them as placeholders
        # JSON uses {} for objects, but .format() uses {} for variable substitution. @TODO: review it properly
        escaped_output = raw_output.replace("{", "{{").replace("}", "}}")

        prompt = RESPONSE_FORMAT_PROMPT.format(
            provider_name=semantic.provider_name,
            provider_instructions=semantic.provider_instructions or "",
            user_query=user_query,
            tool_results=escaped_output,
        )

        from observability import LogLevel, SpanKind, log, span, update_span

        async with span(
            "response_formatting",
            kind=SpanKind.GENERATION,
            attributes={"model": getattr(self.model, "model_id", "unknown")},
        ):
            await log(LogLevel.INFO, "Invoking LLM for response formatting")
            response = await self.model.invoke([{"role": "user", "content": prompt}])
            content = response.content if hasattr(response, "content") else str(response)

            # Update span attributes so engine can track tokens
            # ModelResponse standardize usage in .usage dict
            usage = response.usage
            if usage:
                update_span(
                    {
                        "input_tokens": usage.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                        "thoughts_tokens": usage.get("thoughts_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }
                )

            return content.strip()

    async def generate_code(
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
        from observability import LogLevel, log, span, update_span

        async with span("code_generation"):
            # Step 1: Get the semantic layer (with tool_definitions from context if available)
            async with span("semantic_layer.build"):
                await log(LogLevel.INFO, "Building semantic layer")
                # Use build_semantic_layer with tool_definitions for MCP tool support
                tool_definitions = context.get("tool_definitions") if context else None
                if hasattr(self.provider, "build_semantic_layer"):
                    semantic_layer = self.provider.build_semantic_layer(tool_definitions)
                    self._semantic_layer = semantic_layer  # Store for use in _build_full_code()
                # else:
                #     # Fallback for providers that don't have build_semantic_layer
                #     semantic_layer = self.provider.semantic_layer
                agent_count = len(semantic_layer.domains)
                total_tools = sum(len(d.tools) for d in semantic_layer.domains)
                await log(
                    LogLevel.DEBUG,
                    f"Agents: {agent_count}, Tools: {total_tools}",
                    {"agent_count": agent_count, "total_tools": total_tools},
                )
                save_debug_artifact(
                    "semantic_layer.json",
                    json.dumps(semantic_layer.to_dict(), indent=2, ensure_ascii=False),
                )
                await log(LogLevel.DEBUG, "Saved to: .debug/semantic_layer.json")

            # Step 2: Generate Python stubs
            async with span("stubs.generate"):
                await log(LogLevel.INFO, "Generating Python stubs")
                stubs = generate_stubs(semantic_layer)
                stub_lines = stubs.count("\n")
                agents = [d.id for d in semantic_layer.domains]
                await log(
                    LogLevel.DEBUG,
                    f"Generated {stub_lines} lines for {len(agents)} agents",
                    {"stub_lines": stub_lines, "agents": agents},
                )
                save_debug_artifact("stubs.py", stubs)
                await log(LogLevel.DEBUG, "Saved to: .debug/stubs.py")

            # Step 3: Load conversation history
            async with span(
                "memory.load_context",
                attributes={
                    "thread_id": thread_id or "none",
                    "has_memory": bool(thread_id),
                },
            ):
                await log(LogLevel.INFO, "Loading conversation history")
                messages: list[dict[str, Any]] = []
                if thread_id:
                    history = await self.provider.get_history(thread_id)
                    messages.extend(history)
                await log(
                    LogLevel.DEBUG,
                    f"Retrieved {len(messages)} messages from storage",
                    {"messages_loaded": len(messages)},
                )
                if messages:
                    save_debug_artifact(
                        "conversation_context.json",
                        json.dumps(messages, indent=2, ensure_ascii=False),
                    )
                    await log(LogLevel.DEBUG, "Saved to: .debug/conversation_context.json")

            # Step 4: Build the prompt
            async with span(
                "prompt.build",
                attributes={
                    "prompt_type": self.provider.provider_type.lower(),
                    "has_history": bool(messages),
                    "has_runtime_context": bool(context),
                },
            ):
                await log(LogLevel.INFO, "Building prompt")

                # Format runtime context (exclude tool_definitions - stubs already provide that)
                runtime_context_str = ""
                if context:
                    filtered_context = {
                        key: value for key, value in context.items() if key != "tool_definitions"
                    }
                    if filtered_context:
                        runtime_context_str = "\n".join(
                            [f"- {key}: {value}" for key, value in filtered_context.items()]
                        )
                        await log(
                            LogLevel.DEBUG, f"Runtime context keys: {list(filtered_context.keys())}"
                        )
                    else:
                        runtime_context_str = "No additional runtime context provided."
                else:
                    runtime_context_str = "No additional runtime context provided."

                # Build prompt based on provider type
                if self.provider.provider_type == "AGENT":
                    agent_class = (
                        semantic_layer.provider_name.lower().replace(" ", "_").replace("-", "_")
                    )
                    prompt = AGENT_CODE_MODE_PROMPT.format(
                        agent_name=semantic_layer.provider_name,
                        agent_description=semantic_layer.provider_description
                        or f"Agent: {semantic_layer.provider_name}",
                        agent_instructions=semantic_layer.provider_instructions or "",
                        agent_class=agent_class,
                        stubs=stubs,
                        runtime_context=runtime_context_str,
                        user_query=user_query,
                    )
                    await log(LogLevel.DEBUG, "Using AGENT_CODE_MODE_PROMPT template")
                else:
                    prompt = TEAM_CODE_MODE_PROMPT.format(
                        team_name=semantic_layer.provider_name,
                        team_description=semantic_layer.provider_description or "",
                        team_instructions=semantic_layer.provider_instructions or "",
                        stubs=stubs,
                        runtime_context=runtime_context_str,
                        user_query=user_query,
                    )
                    await log(LogLevel.DEBUG, "Using TEAM_CODE_MODE_PROMPT template")

                messages.append({"role": "user", "content": prompt})
                save_debug_artifact("prompt.txt", prompt)
                await log(LogLevel.DEBUG, "Saved to: .debug/prompt.txt")

            # Step 5: Call the LLM
            async with span(
                "llm.generate_code",
                attributes={"model": getattr(self.model, "model_id", "unknown")},
            ):
                await log(LogLevel.INFO, "Invoking LLM for code generation")
                await log(LogLevel.DEBUG, f"Model: {getattr(self.model, 'name', 'unknown')}")

                response = await self.model.invoke(messages)
                content = response.content if hasattr(response, "content") else str(response)

                # Update span attributes so engine can track tokens
                # The attributes will be automatically logged on span end
                usage = response.usage
                if usage:
                    update_span(
                        {
                            "input_tokens": usage.get("input_tokens", 0),
                            "output_tokens": usage.get("output_tokens", 0),
                            "thoughts_tokens": usage.get("thoughts_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0),
                        }
                    )

                await log(
                    LogLevel.DEBUG,
                    f"Generated code: {len(content)} chars",
                    {"code_length": len(content)},
                )
                save_debug_artifact("generated_code.py", content)
                await log(LogLevel.DEBUG, "Saved to: .debug/generated_code.py")
                await log(LogLevel.INFO, "Code generation complete")

            return content.strip()

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
            code: Python code to run (usually from generate_code())
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

    # PRIVATE: Code Assembly
    # These methods build the code that runs in the subprocess.

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
                            with open(".debug/tool_results.json", "w") as f:
                                json.dump(tool_results_for_debug, f, indent=2, default=str)
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

        # Parse "module.tool_name" format
        parts = name.split(".")
        if len(parts) != 2:
            return {"type": "error", "message": f"Invalid tool name format: '{name}'"}

        module_name, tool_name = parts

        # First check if module_name is an MCP toolkit
        mcp_entry = self._get_tool(module_name)
        is_mcp = isinstance(mcp_entry, tuple) and len(mcp_entry) == 2 and mcp_entry[0] == "MCP"

        if is_mcp:
            # MCP tool execution
            assert mcp_entry is not None  # Guaranteed by is_mcp check above
            _, mcp_toolkit = mcp_entry
            # Use tool_name as-is - runtime stubs already provide original names

            async with span(
                f"tool.{tool_name}",
                kind=SpanKind.TOOL,
                attributes={
                    "tool_name": tool_name,
                    "tool_qualified_name": f"{module_name}.{tool_name}",
                    "mcp_toolkit": mcp_toolkit.name,
                    "args": args,
                    "execution_type": "mcp",
                },
            ):
                await log(LogLevel.INFO, f"Executing MCP tool: {mcp_toolkit.name}.{tool_name}")
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
                    # Call MCP tool via toolkit - use tool_name as-is
                    result = await mcp_toolkit.call_tool(tool_name, **args)

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
