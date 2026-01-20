"""
Agent class for Astra Framework.

The Agent class is the core abstraction for creating AI agents. It supports:
- Standalone mode: Agent has its own infrastructure
- Lazy initialization: Resources initialized only when needed
- Model abstraction: Supports multiple LLM providers
- Code Mode: LLM generates Python code that calls tools
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any
import uuid

from framework.memory import Memory
from framework.middleware import (
    Middleware,
    MiddlewareContext,
    MiddlewareError,
    MiddlewareStage,
    run_middlewares,
)
from framework.models import Model
from framework.storage.client import StorageClient


if TYPE_CHECKING:
    from framework.code_mode.semantic import TeamSemanticLayer
    from framework.code_mode.tool_registry import ToolRegistry


class Agent:
    """
    Agent class is used to create AI agents.

    It provides initialization with basic properties like id, name, description,
    instructions, model, tools, etc. Heavy work is deferred (lazy initialization).

    Example:
        agent = Agent(
            name="Assistant",
            instructions="You are helpful",
            model=Gemini("gemini-2.5-flash"),
            tools=[calculator]
        )

        # Get Python stubs for LLM code generation
        stubs = agent.get_stubs()
    """

    def __init__(
        self,
        model: Model,
        instructions: str,
        name: str,
        id: str | None = None,
        description: str | None = None,
        tools: list[Any] | None = None,
        code_mode: bool = True,
        storage: StorageClient | None = None,
        # @TODO: Himanshu. RAG support disabled for V1 release. Will be enabled later.
        # rag_pipeline: Any | None = None,
        # rag_pipelines: dict[str, Any] | None = None,
        memory: Memory | None = None,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream_enabled: bool = False,
        middlewares: list[Middleware] | None = None,
    ):
        """
        Initialize an Agent with the provided configuration.

        Args:
            model: Model instance (e.g., Gemini(...))
            instructions: Agent instructions (required)
            name: Agent name (required)
            id: Optional agent ID (auto-generated if not provided)
            description: Optional agent description
            tools: Optional list of tools
            code_mode: Whether to enable code mode (default: True)
            storage: Optional storage backend
            memory: Optional memory configuration
            max_retries: Maximum retry attempts for failed requests (default: 3)
            temperature: Sampling temperature for model responses (default: 0.7)
            max_tokens: Maximum tokens to generate per response
            stream_enabled: Whether to stream responses by default (default: False)
            middlewares: Optional list of middlewares (guardrails, validation, etc.)
        """
        # Basic identifiers & metadata
        self.name = name
        self.id = id if id else f"agent-{self.name}-{uuid.uuid4().hex[:5]}"
        self.description = description

        # Core behavior config
        self.instructions = instructions
        self.model = model
        self.tools = tools
        self.code_mode = code_mode

        # Lazy-initialized (cached after first access)
        self._semantic_layer: TeamSemanticLayer | None = None
        self._tool_registry: ToolRegistry | None = None

        # Memory & Storage
        self.memory = memory or Memory()
        self.storage = storage

        # @TODO: Himanshu. RAG support disabled for V1 release. Will be enabled later.
        # self.rag_pipeline = rag_pipeline
        # self.rag_pipelines = rag_pipelines or {}

        # Execution config
        self.timeout = 60.0
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream_enabled = stream_enabled

        # Middlewares (unified list - stages determine when they run)
        self.middlewares = middlewares or []

    async def _run_input_middleware(self, data: Any) -> tuple[Any, str | None]:
        """
        Run INPUT stage middlewares.

        Returns:
            Tuple of (processed_data, error_message).
            If error_message is not None, the input was rejected.
        """
        if not self.middlewares:
            return data, None

        ctx = MiddlewareContext(data=data)
        ctx = await run_middlewares(self.middlewares, MiddlewareStage.INPUT, ctx)

        if ctx.stop:
            return data, ctx.error or "Input rejected by middleware"
        return ctx.data, None

    async def _run_output_middleware(self, data: Any) -> tuple[Any, str | None]:
        """
        Run OUTPUT stage middlewares.

        Returns:
            Tuple of (processed_data, error_message).
            If error_message is not None, the output was rejected.
        """
        if not self.middlewares:
            return data, None

        ctx = MiddlewareContext(data=data)
        ctx = await run_middlewares(self.middlewares, MiddlewareStage.OUTPUT, ctx)

        if ctx.stop:
            return data, ctx.error or "Output rejected by middleware"
        return ctx.data, None

    # PROPERTIES
    @property
    def semantic_layer(self) -> TeamSemanticLayer:
        """
        Get the semantic layer for this agent. Lazily initialized.

        The semantic layer is a structured representation of all tools
        available for this agent. It's used to generate Python stubs.
        """
        if self._semantic_layer is None:
            from framework.code_mode.semantic import build_agent_semantic_layer

            self._semantic_layer = build_agent_semantic_layer(self)
            with open("semantic_agnet_layer.json", "w") as f:
                f.write(str(self._semantic_layer))
            print("Semantic layer generated in the file semantic_agnet_layer.json")
        return self._semantic_layer

    @property
    def tool_registry(self) -> ToolRegistry:
        """
        Get the tool registry for this agent. Lazily initialized.

        Maps "agent_id.tool_name" to Tool objects for lookup and execution.
        """
        if self._tool_registry is None:
            from framework.code_mode.tool_registry import ToolRegistry

            self._tool_registry = ToolRegistry()

            # Generate agent_id matching semantic layer's class_id
            agent_id = self.name.lower().replace(" ", "_").replace("-", "_")
            agent_tools = self.tools or []

            for tool in agent_tools:
                self._tool_registry.register(agent_id, tool)

        return self._tool_registry

    def get_stubs(self) -> str:
        """
        Generate Python stubs for this agent's tools.

        The stubs provide:
        1. Type-hinted function signatures for all tools
        2. Docstrings with parameter descriptions
        3. Return type information

        Returns:
            Python code string with stub definitions

        Example:
            >>> agent = Agent(name="Analyst", tools=[get_stock_price])
            >>> print(agent.get_stubs())
            class analyst:
                @staticmethod
                def get_stock_price(symbol: str) -> dict:
                    '''Get current stock price...'''
                    ...
        """
        from framework.code_mode.stub_generator import generate_stubs

        generated_stubs = generate_stubs(self.semantic_layer)
        with open("stubs.txt", "w") as f:
            f.write(generated_stubs)
        print("Generated stubs saved in the file stubs.txt")
        return generated_stubs

    async def generate_code(self, user_query: str) -> str:
        """
        Generate Python code from a user query.

        Uses the agent's tools (via semantic layer) to build a prompt for the LLM,
        which then generates Python code that calls the appropriate tools.

        Args:
            user_query: The user's request/question

        Returns:
            Python code string ready for sandbox execution

        Example:
            >>> code = await agent.generate_code("Get Apple stock price")
            >>> print(code)
            price = market_analyst.get_stock_price('AAPL')
            synthesize_response({"price": price})
        """
        from framework.code_mode.prompts import AGENT_CODE_MODE_PROMPT

        # Get the agent class name (snake_case)
        agent_class = self.name.lower().replace(" ", "_").replace("-", "_")

        # Build the prompt
        prompt = AGENT_CODE_MODE_PROMPT.format(
            agent_name=self.name,
            agent_description=self.description or f"Agent: {self.name}",
            agent_instructions=self.instructions,
            agent_class=agent_class,
            stubs=self.get_stubs(),
            user_query=user_query,
        )

        # Call LLM to generate code
        response = await self.model.invoke(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,  # Deterministic for code generation
        )

        # Extract code content
        code = response.content if hasattr(response, "content") else str(response)

        # Clean up any markdown wrappers if present
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]

        return code.strip()

    async def invoke(
        self,
        query: str,
        *,
        thread_id: str | None = None,
        timeout: float | None = None,
    ) -> str:
        """
        Execute the agent on a query and return the final response.

        This is the main entry point for running an agent in code_mode. It:
        1. Runs INPUT middlewares (validation, guardrails)
        2. Builds semantic layer from agent's tools
        3. Generates Python stubs for LLM
        4. Calls LLM to generate Python code
        5. Executes code in isolated sandbox
        6. Runs OUTPUT middlewares
        7. Formats response via second LLM call

        Args:
            query: The user's request/question
            thread_id: Optional thread ID for message persistence
            timeout: Override default timeout (seconds)

        Returns:
            The formatted response from the agent

        Raises:
            MiddlewareError: If a middleware rejects the input/output
        """
        from framework.code_mode.sandbox import Sandbox
        from framework.storage.persistence import save_assistant_message, save_user_message

        # Run INPUT middlewares
        query, error = await self._run_input_middleware(query)
        if error:
            raise MiddlewareError(error)

        # Save user message
        thread_id = await save_user_message(
            self.storage,
            thread_id,
            query,
            resource_type="agent",
            resource_id=self.id or self.name,
            resource_name=self.name,
        )

        # Execute in sandbox
        sandbox = Sandbox(self)
        result = await sandbox.run(query, timeout=timeout or self.timeout)
        response = result.formatted_output or result.output

        # Run OUTPUT middlewares
        response, error = await self._run_output_middleware(response)
        if error:
            raise MiddlewareError(error)

        # Save assistant response
        await save_assistant_message(self.storage, thread_id, response)

        return response

    async def stream(
        self,
        query: str,
        *,
        thread_id: str | None = None,
        timeout: float | None = None,
    ) -> AsyncIterator[Any]:
        """
        Stream the agent execution, yielding SSE events.

        Yields StreamEvent objects with types:
        - status: Progress updates
        - code_generated: Code has been generated
        - tool_call: A tool is being called
        - tool_result: Tool execution completed
        - content: Response content chunk
        - error: An error occurred
        - done: Streaming complete

        Args:
            query: The user's request/question
            thread_id: Optional thread ID for message persistence
            timeout: Override default timeout (seconds)

        Yields:
            StreamEvent objects for SSE streaming
        """
        from framework.code_mode.sandbox import Sandbox
        from framework.storage.persistence import save_assistant_message, save_user_message
        from framework.team.team import StreamEvent

        # Run INPUT middlewares
        query, error = await self._run_input_middleware(query)
        if error:
            yield StreamEvent(event_type="error", data={"message": error})
            return

        # Save user message
        thread_id = await save_user_message(
            self.storage,
            thread_id,
            query,
            resource_type="agent",
            resource_id=self.id or self.name,
            resource_name=self.name,
        )

        yield StreamEvent(event_type="status", data={"message": "Generating code..."})

        sandbox = Sandbox(self)
        exec_timeout = timeout or self.timeout

        # Generate code first
        try:
            code = await sandbox.generate_code(query)
            with open("generated_code.txt", "w") as f:
                f.write(code)
            print("Generated code saved in the file generated_code.py")
            yield StreamEvent(
                event_type="code_generated",
                data={
                    "message": "Code generated. Executing...",
                    "code_preview": code[:200] + "..." if len(code) > 200 else code,
                },
            )
        except Exception as e:
            yield StreamEvent(event_type="error", data={"message": f"Error generating code: {e}"})
            return

        # Execute and stream results
        try:
            result = await sandbox.execute(code, timeout=exec_timeout)

            # Report tool calls
            if result.tool_calls:
                for i, tool_call in enumerate(result.tool_calls):
                    yield StreamEvent(
                        event_type="tool_call",
                        data={
                            "index": i,
                            "tool_name": tool_call.get("name", "unknown"),
                            "arguments": tool_call.get("args", {}),
                        },
                    )
                    yield StreamEvent(
                        event_type="tool_result",
                        data={
                            "index": i,
                            "tool_name": tool_call.get("name", "unknown"),
                            "result": tool_call.get("result", ""),
                            "success": "error" not in tool_call,
                        },
                    )

            # Format and yield final output
            if result.success:
                formatted_output = await sandbox.format_response(query, result.output)

                # Run OUTPUT middlewares
                formatted_output, error = await self._run_output_middleware(formatted_output)
                if error:
                    yield StreamEvent(event_type="error", data={"message": error})
                    return

                # Save assistant response
                await save_assistant_message(self.storage, thread_id, formatted_output)

                yield StreamEvent(event_type="content", data={"text": formatted_output})
                yield StreamEvent(event_type="done", data={"status": "complete"})
            else:
                yield StreamEvent(
                    event_type="error",
                    data={"message": f"Execution failed: {result.stderr or 'Unknown error'}"},
                )

        except Exception as e:
            yield StreamEvent(event_type="error", data={"message": f"Execution error: {e}"})

    def __repr__(self) -> str:
        """Minimal string representation of the Agent."""
        return f"Agent(id={self.id!r}, name={self.name!r})"

    def __str__(self) -> str:
        """Human-friendly representation."""
        return self.__repr__()
