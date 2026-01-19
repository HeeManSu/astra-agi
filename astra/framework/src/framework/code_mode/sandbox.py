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
import sys
from typing import TYPE_CHECKING, Any

from framework.code_mode.prompts import (
    AGENT_CODE_MODE_PROMPT,
    RESPONSE_FORMAT_PROMPT,
    TEAM_CODE_MODE_PROMPT,
)
from framework.code_mode.stub_generator import generate_runtime_stubs, generate_stubs


if TYPE_CHECKING:
    from framework.agents.agent import Agent
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
    # Use 100MB buffer limit to handle very large tool responses
    response_line = sys.stdin.readline(100 * 1024 * 1024)
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

    def __init__(self, team_or_agent: Team | Agent):
        """Initialize sandbox with Team or Agent.

        Both Team and Agent have the same interface for code mode:
        - semantic_layer: Structured representation of tools
        - tool_registry: Maps tool names to Tool objects
        - model: LLM model for code generation
        - name, description, instructions: Metadata for prompts

        Args:
            team_or_agent: Team or Agent instance to generate/execute code for
        """
        self.team = team_or_agent  # Keep as "team" for backward compatibility
        self.model = team_or_agent.model
        # Tool registry is accessed via team.tool_registry (lazily built)

    # PUBLIC API
    # The Sandbox has 3 public methods:
    #   - run(): All-in-one method (generate + execute)
    #   - generate_code(): Just generate code from user query
    #   - execute(): Just execute code in subprocess
    #
    # Use run() for simple cases. Use generate_code() + execute() separately
    # when you need to yield events between steps (e.g., for streaming).

    async def run(self, user_query: str, timeout: float = 60.0) -> SandboxResult:
        """Generate code from a user query, execute it, and format the response.

        This is the simplest way to use the sandbox - just pass a query and get results.
        Under the hood, it does three things:
            1. Asks the LLM to generate Python code based on the query
            2. Runs that code in an isolated subprocess
            3. Formats the raw JSON output into a human-readable response

        Example:
            >>> sandbox = Sandbox(team)
            >>> result = await sandbox.run("What is Apple's stock price?")
            >>> print(result.formatted_output)  # "Apple (AAPL) is trading at $150.25..."

        Args:
            user_query: What the user wants to do (e.g., "Get stock price for AAPL")
            timeout: How long to wait before killing the subprocess (default: 60 seconds)

        Returns:
            SandboxResult containing:
                - output: Raw JSON result
                - formatted_output: Human-readable response
                - success: True if code ran without errors
                - tool_calls: List of tools that were called
                - stderr: Any error messages (for debugging)
        """
        # Step 1: Ask LLM to generate Python code
        code = await self.generate_code(user_query)
        with open("generated_code.txt", "w") as f:
            f.write(code)
        print("Generated code saved in the file generated_code.txt")

        # Step 2: Run the generated code in an isolated subprocess
        result = await self.execute(code, timeout=timeout)
        result.generated_code = code

        # Step 3: Format the response into human-readable text
        if result.success and result.output:
            result.formatted_output = await self.format_response(user_query, result.output)

        print(result)

        with open("result.md", "w") as f:
            f.write(result.formatted_output)
        print("Result saved to result.md")

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
        prompt = RESPONSE_FORMAT_PROMPT.format(
            agent_name=self.team.name,
            agent_instructions=getattr(self.team, "instructions", "") or "",
            user_query=user_query,
            tool_results=raw_output,
        )

        response = await self.model.invoke([{"role": "user", "content": prompt}])
        content = response.content if hasattr(response, "content") else str(response)

        with open("response.md", "w") as f:
            f.write(content)
        print("Response saved to response.md")

        return content.strip()

    async def generate_code(self, user_query: str) -> str:
        """Ask the LLM to generate Python code based on a user query.

        This is the "brain" part of the sandbox. It:
            1. Gets the semantic layer (describes what tools are available)
            2. Generates Python stubs (code templates the LLM can use)
            3. Builds a prompt explaining what to do
            4. Calls the LLM to generate the actual code

        The generated code will look something like:
            price = market_analyst.get_stock_price('AAPL')
            news = market_analyst.get_market_news('technology')
            synthesize_response({"price": price, "news": news})

        Args:
            user_query: What the user wants (e.g., "Get Apple stock info")

        Returns:
            Python code as a string (ready to execute)
        """

        # Step 1: Get the semantic layer
        semantic_layer = self.team.semantic_layer
        with open("semantic_layer.json", "w") as f:
            json.dump(semantic_layer.to_dict(), f, indent=2, ensure_ascii=False)
        print("Semantic layer saved to semantic_layer.json")

        # Step 2: Generate Python stubs from the semantic layer
        stubs = generate_stubs(semantic_layer)
        with open("stubs.txt", "w") as f:
            f.write(stubs)
        print("Stubs saved to stubs.txt")

        # Step 3: Build the prompt - use different template for Agent vs Team
        # Agent doesn't have 'members' attribute, Team does
        is_agent = not hasattr(self.team, "members")

        if is_agent:
            # Agent: use agent-specific prompt
            agent_class = self.team.name.lower().replace(" ", "_").replace("-", "_")
            prompt = AGENT_CODE_MODE_PROMPT.format(
                agent_name=self.team.name,
                agent_description=self.team.description or f"Agent: {self.team.name}",
                agent_instructions=self.team.instructions or "",
                agent_class=agent_class,
                stubs=stubs,
                user_query=user_query,
            )
        else:
            # Team: use team-specific prompt
            prompt = TEAM_CODE_MODE_PROMPT.format(
                team_name=self.team.name,
                team_description=self.team.description or "",
                team_instructions=self.team.instructions or "",
                stubs=stubs,
                user_query=user_query,
            )

        # Step 4: Call the LLM to generate code
        print("Invoking LLM")
        response = await self.model.invoke([{"role": "user", "content": prompt}])

        # Extract the code from the LLM's response
        content = response.content if hasattr(response, "content") else str(response)

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
        # Step 1: Build the complete executable code
        # This combines: runtime bridge functions + agent stub classes + LLM code
        full_code = self._build_full_code(code)

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

        try:
            # Step 3: Monitor the subprocess and handle tool calls
            # This loop reads stdout, executes tools, and sends responses back
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
        runtime_stubs = generate_runtime_stubs(self.team.semantic_layer)
        parts.append(runtime_stubs)

        # Part 3: LLM Generated Code
        # This is the actual logic that uses the stubs above
        parts.append("\n# ═══════ LLM Generated Code ═══════\n")
        parts.append(code)

        # Combine everything into one script
        full_code = "\n".join(parts)

        # Debug: Print the full code (remove in production)
        print("DEBUG: Full Execution Code:\n" + "=" * 40 + "\n" + full_code + "\n" + "=" * 40)

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
                        tool_name = request.get("name", "unknown")
                        print(f"DEBUG: Tool call received: {tool_name}")
                        tool_calls.append(request)

                        # Execute the tool and send response
                        response = await self._handle_tool_call(request)

                        # Store result in tool_calls for history/metrics
                        if response.get("type") == "error":
                            request["error"] = response.get("message")
                            print(f"DEBUG: Tool error: {response.get('message')}")
                        else:
                            request["result"] = response.get("data")
                            data_preview = str(response.get("data"))[:200]
                            print(f"DEBUG: Tool success, data preview: {data_preview}...")

                        response_json = json.dumps(response) + "\n"
                        proc.stdin.write(response_json.encode())
                        await proc.stdin.drain()
                        print("DEBUG: Response sent to subprocess")

                    elif msg_type == "synthesize":
                        # Final response from subprocess
                        final_response = request.get("message", "")
                        print(f"DEBUG: Synthesize received: {str(final_response)[:200]}...")

                    continue  # Don't add JSON to output

                except json.JSONDecodeError as e:
                    # Log the failed JSON parsing for debugging
                    print(f"DEBUG: JSONDecodeError - {e}")
                    print(f"DEBUG: Failed to parse line: {text[:200]}...")

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

        # Look up tool in registry by qualified name (agent_id.tool_name)
        qualified_name = f"{module_name}.{tool_name}"
        tool = self.team.tool_registry.get(qualified_name)

        if not tool:
            return {"type": "error", "message": f"Tool '{qualified_name}' not found"}

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

            return {"type": "result", "data": data}

        except Exception as e:
            return {"type": "error", "message": str(e)}
