"""
Agent class for Astra Framework.

The Agent class is the core abstraction for creating AI agents. It supports:
- Standalone mode: Agent has its own infrastructure (AstraContext)
- Lazy initialization: Resources initialized only when needed
- Model abstraction: Supports multiple LLM providers
- Tool execution: Automatic tool calling and result handling
- Observability: Built-in tracing, metrics, and logging (via AstraContext)

Notes:
- context window size changed to max_messages
- enable_summary changed to enable_message_summary
"""

from collections.abc import AsyncIterator, Callable
import json
from typing import Any
import uuid

from framework.agents.exceptions import ModelError, RetryExhaustedError, ToolError, ValidationError
from framework.agents.execution import ExecutionContext, execute_tool_parallel
from framework.agents.retry import RetryConfig, retry_with_backoff
from framework.astra import AstraContext
from framework.memory import AgentMemory
from framework.memory.manager import MemoryManager
from framework.middlewares import InputMiddleware, MiddlewareContext, OutputMiddleware
from framework.models import Model, ModelResponse
from framework.storage.memory import AgentStorage


class Agent:
    """
    Agent class is used to create AI agents.

    It provides initialization with basic properties like id, name, description, instructions, model, tools, etc.. but it does not perform any heavy work during initialization. All the expensive operations are deferred (lazy initialization).

    Example:
    agent = Agent(
        name="Assistant",
        instructions="You are helpful",
        model=Gemini("1.5-flash"),
        tools=[calculator]
    )

    Later:
    response = await agent.invoke("What is 2+2?")
    """

    def __init__(
        self,
        model: Model,
        instructions: str,
        name: str,
        id: str | None = None,
        description: str | None = None,
        tools: list[Any] | None = None,
        storage: Any | None = None,
        knowledge: Any | None = None,
        memory: AgentMemory | None = None,
        max_retries: int = 3,
        temperature: float = 0.7,
        # Handle this in the invoke/stream methods as well.
        max_tokens: int | None = None,
        stream_enabled: bool = False,
        input_middlewares: list[Any] | Callable | None = None,
        output_middlewares: list[Any] | Callable | None = None,
        guardrails: dict[str, Any] | None = None,
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
            storage: Optional storage backend (e.g., SQLiteStorage)
            knowledge: Optional knowledge base (e.g., PDFKnowledgeBase)
            memory: Optional memory configuration (AgentMemory)
            max_retries: Maximum retry attempts for failed requests (default: 3)
            temperature: Sampling temperature for model responses (default: 0.7, range: 0.0-2.0)
            max_tokens: Maximum tokens to generate per response (default: 4096)
            stream_enabled: Whether to stream responses by default (default: False)
            input_middlewares: Optional list of input middlewares
            output_middlewares: Optional list of output middlewares
            guardrails: Optional guardrails configuration
        """

        # Lazily-initialized context (Observability, Logger, Settings, etc.)
        self._context: AstraContext | None = None

        # Lazily-initialized/cached tools schema (computed when needed)
        self._tools_schema: list[dict[str, Any]] | None = None

        # Basic identifiers & metadata
        self.name = name
        if id is None:
            self.id = f"agent-{uuid.uuid4().hex[:8]}"
        else:
            self.id = id

        self.description = description

        # Core behavior config
        self.instructions = instructions
        self.model = model
        self.tools = tools

        # Memory & Storage
        self.memory = memory or AgentMemory()
        self.memory_manager = MemoryManager(self.memory, self.model)

        self.storage: AgentStorage | None = None
        if storage:
            # Pass max_messages from memory config to storage (for legacy support/defaults)
            self.storage = AgentStorage(
                storage=storage, max_messages=self.memory.num_history_responses
            )

        self.knowledge = knowledge

        # Execution config
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream_enabled = stream_enabled

        # Middleware / guardrails / formatting
        self.input_middlewares = input_middlewares
        self.output_middlewares = output_middlewares
        self.guardrails = guardrails

    @property
    def context(self) -> AstraContext:
        """Get the context for the agent. Lazily initialized."""
        if self._context is None:
            self._context = AstraContext()
        return self._context

    @property
    def tools_schema(self) -> list[dict[str, Any]]:
        """Get tools schema. Lazily computed and cached."""
        if self._tools_schema is None:
            if not self.tools:
                self._tools_schema = []
            else:
                self._tools_schema = []
                for tool in self.tools:
                    # Tool object (from @tool decorator)
                    if (
                        hasattr(tool, "name")
                        and hasattr(tool, "description")
                        and hasattr(tool, "parameters")
                    ):
                        self._tools_schema.append(
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.parameters,
                            }
                        )
                    # Dict format
                    elif isinstance(tool, dict):
                        self._tools_schema.append(
                            {
                                "name": tool.get("name", ""),
                                "description": tool.get("description", ""),
                                "parameters": tool.get("parameters", {}),
                            }
                        )
        return self._tools_schema

    def _validate_invoke_params(
        self,
        message: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Validate invocation parameters."""

        if message is not None:
            if not isinstance(message, str):
                raise ValidationError(f"Message must be a string. Got {type(message)}.")
            if not message.strip():
                raise ValidationError("Message cannot be empty.")
            if len(message) > 100_000:
                raise ValidationError("Message cannot be longer than 100000 characters.")

        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                raise ValidationError(f"Temperature must be a number. Got {type(temperature)}.")
            if temperature < 0.0 or temperature > 2.0:
                raise ValidationError("Temperature must be between 0.0 and 2.0.")

        if max_tokens is not None:
            if not isinstance(max_tokens, int):
                raise ValidationError(f"Max tokens must be an integer. Got {type(max_tokens)}.")
            if max_tokens < 0:
                raise ValidationError("Max tokens must be a non-negative integer.")
            if max_tokens > 100_000:
                raise ValidationError(f"max_tokens too large: {max_tokens}")

    def _prepare_messages(
        self,
        message: str,
        context: ExecutionContext,
        history: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Prepare messages for the model invocation."""

        messages = []

        # Add system message with instructions
        if self.instructions:
            messages.append(
                {
                    "role": "system",
                    "content": self.instructions,
                }
            )

        # Add conversation history
        if history:
            messages.extend(history)

        # Add user message
        messages.append(
            {
                "role": "user",
                "content": message,
            }
        )

        return messages

    async def _invoke_with_retry(
        self,
        messages: list[dict[str, Any]],
        context: ExecutionContext,
    ) -> ModelResponse:
        """Invoke the model with retry logic."""

        config = RetryConfig(
            max_retries=self.max_retries, initial_delay=1.0, max_delay=60.0, exponential_base=2.0
        )

        async def _invoke():
            return await self.model.invoke(
                messages=messages,
                tools=self.tools_schema if context.tools else None,
                temperature=context.temperature,
                max_tokens=context.max_tokens,
            )

        try:
            response = await retry_with_backoff(_invoke, config, context)
            self._log_success("Model invoked successfully", context)
            return response
        except Exception as e:
            self._log_error("All retries exhausted", e, context)
            raise RetryExhaustedError(f"Failed after {self.max_retries} attempts: {e}") from e

    async def _execute_tools(
        self, tool_calls: list[dict[str, Any]], context: ExecutionContext
    ) -> list[dict[str, Any]]:
        """Execute tool calls and return results."""

        if not self.tools:
            raise ToolError("Model requested tools but none are available")

        try:
            results = await execute_tool_parallel(
                tool_calls=tool_calls, tools=self.tools, context=context
            )
            return results
        except Exception as e:
            self._log_error("Tool execution failed", e, context)
            raise ToolError(f"Tool execution failed: {e}") from e

    def _format_response(self, response: ModelResponse) -> str:
        """Format model response for return."""

        if not response.content:
            return ""

        return response.content.strip()

    def _format_tool_results(self, results: list[dict]) -> str:
        """Format tool results for model."""

        formatted = []
        for result in results:
            tool_name = result.get("tool", "unknown")
            if "error" in result:
                formatted.append(f"{tool_name}: Error - {result['error']}")
            else:
                formatted.append(f"{tool_name}: {result.get('result', 'No result')}")

        return "Tool Results:\n" + "\n".join(formatted)

    def _log_success(self, message: str, context: ExecutionContext) -> None:
        """Log successful operation."""
        if context.observability:
            context.observability.logger.info(message, agent_id=self.id, agent_name=self.name)

    def _log_error(self, message: str, error: Exception, context: ExecutionContext) -> None:
        """Log error."""
        if context.observability:
            context.observability.logger.error(
                message,
                agent_id=self.id,
                agent_name=self.name,
                error=str(error),
                error_type=type(error).__name__,
            )

    async def invoke(
        self,
        message: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[Any] | None = None,
        stream: bool | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Invoke the agent with a message and get a response.

        Args:
            message: The message to send to the agent.
            temperature: The temperature to use for the model.
            max_tokens: The maximum number of tokens to generate.
            tools: The tools to use for the agent.
            stream: Whether to stream the response.
            **kwargs: Additional keyword arguments.

        Returns:
            The response from the agent.

        Example:
         response = await agent.invoke("What is 2+2?")
         print(response) # "2+2 equals 4"
        """

        # 1. Validate input
        self._validate_invoke_params(
            message=message,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 2. Prepare execution context
        context = ExecutionContext(
            agent_id=self.id,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            tools=tools or self.tools,
            observability=self.context.observability if self._context else None,
        )

        # 3. Prepare messages
        thread_id = kwargs.get("thread_id")

        # Load history if enabled
        history = None
        if self.storage and thread_id and self.memory.add_history_to_messages:
            history = await self.memory_manager.get_context(thread_id, self.storage)

        messages = self._prepare_messages(message, context, history=history)

        # Middleware Context
        middleware_context = MiddlewareContext(
            agent=self,
            thread_id=thread_id,
        )

        # Input Middleware
        if self.input_middlewares and isinstance(self.input_middlewares, list):
            for middleware in self.input_middlewares:
                if isinstance(middleware, InputMiddleware):
                    messages = await middleware.process(messages, middleware_context)

        # Save user message if storage is enabled (history loading removed for now)
        if self.storage and thread_id:
            await self.storage.add_message(thread_id=thread_id, role="user", content=message)

        # 4. Invoke model with retry logic
        try:
            response = await self._invoke_with_retry(messages, context)
        except Exception as e:
            self._log_error("Model invocation failed", e, context)
            raise ModelError("Model invocation failed") from e

        # Output Middleware
        if self.output_middlewares and isinstance(self.output_middlewares, list):
            for middleware in self.output_middlewares:
                if isinstance(middleware, OutputMiddleware):
                    response = await middleware.process(response, middleware_context)

        # Save Assistant Response
        if self.storage and thread_id:
            await self.storage.add_message(
                thread_id=thread_id, role="assistant", content=response.content or ""
            )

        # 5. Execute tools until done
        max_tool_iterations = 10
        iteration = 0
        while response.tool_calls and iteration < max_tool_iterations:
            iteration += 1
            tool_results = await self._execute_tools(response.tool_calls, context)

            # Save assistant message WITH tool_calls BEFORE tool execution
            if self.storage and thread_id:
                await self.storage.add_message(
                    thread_id=thread_id,
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls,
                )

            # After getting response with tool_calls, add assistant message to context
            messages.append(
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": response.tool_calls,
                }
            )

            # Then add tool results
            for idx, tr in enumerate(tool_results):
                tool_result_content = json.dumps(tr.get("result", ""), ensure_ascii=False)
                messages.append(
                    {
                        "role": "tool",
                        "name": tr["tool"],
                        "content": tool_result_content,
                    }
                )

                # Save Tool Result to Storage
                if self.storage and thread_id:
                    # Generate tool_call_id from tool call index (or use tool name as identifier)
                    tool_call_id = f"call_{uuid.uuid4().hex[:8]}_{idx}"
                    await self.storage.add_message(
                        thread_id=thread_id,
                        role="tool",
                        content=tool_result_content,
                        tool_call_id=tool_call_id,
                        metadata={
                            "tool_name": tr["tool"],
                            "success": tr.get("success", True),
                            "error": tr.get("error"),
                        },
                    )

            # Re-invoke with updated messages
            response = await self._invoke_with_retry(messages, context)

            # Save subsequent assistant response (final response without tool_calls)
            if self.storage and thread_id:
                await self.storage.add_message(
                    thread_id=thread_id,
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls if response.tool_calls else None,
                )

            # Log warning if twe hit the limit
            if iteration >= max_tool_iterations and response.tool_calls:
                self._log_error(
                    f"Tool calling loop reached maximum iterations ({max_tool_iterations})",
                    Exception(f"Max tool iterations exceeded ({max_tool_iterations})"),
                    context,
                )
                raise ToolError(f"Max tool iterations exceeded ({max_tool_iterations})")

        # 6. Return formatted final result
        return self._format_response(response)

    async def stream(
        self,
        message: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        self._validate_invoke_params(
            message=message, temperature=temperature, max_tokens=max_tokens
        )

        context = ExecutionContext(
            agent_id=self.id,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            tools=tools or self.tools,
            observability=self.context.observability if self._context else None,
        )

        thread_id = kwargs.get("thread_id")

        # Load history if enabled
        history = None
        if self.storage and thread_id and self.memory.add_history_to_messages:
            history = await self.memory_manager.get_context(thread_id, self.storage)

        messages = self._prepare_messages(message, context, history=history)

        # Save user message if storage is enabled
        if self.storage and thread_id:
            await self.storage.add_message(thread_id=thread_id, role="user", content=message)

        max_tool_iterations = 10
        iteration = 0

        while iteration < max_tool_iterations:
            iteration += 1

            # Stream response from model
            stream_iter = self.model.stream(
                messages=messages,
                tools=self.tools_schema if context.tools else None,
                temperature=context.temperature,
                max_tokens=context.max_tokens,
                **kwargs,
            )

            # Accumulate chunks and detect tool calls
            accumulated_content = ""
            accumulated_tool_calls: list[dict[str, Any]] = []

            try:
                async for chunk in stream_iter:  # type: ignore
                    # Yield text content immediately for streaming
                    if chunk.content:
                        accumulated_content += chunk.content
                        yield chunk.content

                    # Accumulate tool calls (check for non-empty list)
                    if chunk.tool_calls and len(chunk.tool_calls) > 0:
                        # Merge tool calls, avoiding duplicates
                        for tc in chunk.tool_calls:
                            if tc not in accumulated_tool_calls:
                                accumulated_tool_calls.append(tc)

                    # Track final chunk for usage metadata
                    if chunk.metadata.get("final"):
                        self._log_usage(chunk.usage, context)

            except Exception as e:
                self._log_error("Streaming failed", e, context)
                raise ModelError(f"Streaming failed: {e}") from e

            # If no tool calls, save final assistant response and we're done
            if not accumulated_tool_calls:
                if self.storage and thread_id:
                    await self.storage.add_message(
                        thread_id=thread_id,
                        role="assistant",
                        content=accumulated_content or "",
                    )
                break

            # Save assistant message WITH tool_calls BEFORE tool execution
            if self.storage and thread_id:
                await self.storage.add_message(
                    thread_id=thread_id,
                    role="assistant",
                    content=accumulated_content or "",
                    tool_calls=accumulated_tool_calls,
                )

            # Execute tools and continue loop
            tool_results = await self._execute_tools(accumulated_tool_calls, context)

            # Add assistant message with tool calls
            messages.append(
                {
                    "role": "assistant",
                    "content": accumulated_content or "",
                    "tool_calls": accumulated_tool_calls,
                }
            )

            # Add tool results
            for idx, tr in enumerate(tool_results):
                tool_result_content = json.dumps(tr.get("result", ""), ensure_ascii=False)
                messages.append(
                    {
                        "role": "tool",
                        "name": tr["tool"],
                        "content": tool_result_content,
                    }
                )

                # Save Tool Result to Storage
                if self.storage and thread_id:
                    tool_call_id = f"call_{uuid.uuid4().hex[:8]}_{idx}"
                    await self.storage.add_message(
                        thread_id=thread_id,
                        role="tool",
                        content=tool_result_content,
                        tool_call_id=tool_call_id,
                        metadata={
                            "tool_name": tr["tool"],
                            "success": tr.get("success", True),
                            "error": tr.get("error"),
                        },
                    )

            # Check if we hit the limit
            if iteration >= max_tool_iterations:
                self._log_error(
                    f"Tool calling loop reached maximum iterations ({max_tool_iterations})",
                    Exception(f"Max tool iterations exceeded ({max_tool_iterations})"),
                    context,
                )
                raise ToolError(f"Max tool iterations exceeded ({max_tool_iterations})")

    def _log_usage(self, usage: dict[str, Any], context: ExecutionContext) -> None:
        """Log usage metrics."""
        if context.observability:
            context.observability.logger.info(
                "Model usage",
                agent_id=self.id,
                agent_name=self.name,
                tokens_in=usage.get("input_tokens", 0),
                tokens_out=usage.get("output_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )

    def __repr__(self) -> str:
        """Minimal, fast string representation of the Agent."""
        return f"Agent(id={self.id!r}, name={self.name!r})"

    def __str__(self) -> str:
        """Human-friendly representation."""
        return self.__repr__()
