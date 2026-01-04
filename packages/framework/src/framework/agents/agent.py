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
from framework.agents.tool import Tool, tool
from framework.astra import AstraContext
from framework.code_mode.api_generator import VirtualAPIGenerator
from framework.code_mode.sandbox import SandboxExecutor, synthesize_response
from framework.code_mode.tool_registry import ToolRegistry, ToolSpec
from framework.mcp.manager import MCPManager
from framework.mcp.server import MCPServer
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
        code_mode: bool = True,
        storage: Any | None = None,
        rag_pipeline: Any | None = None,
        rag_pipelines: dict[str, Any] | None = None,
        memory: AgentMemory | None = None,
        max_retries: int = 3,
        temperature: float = 0.7,
        # Handle this in the invoke/stream methods as well.
        max_tokens: int | None = None,
        stream_enabled: bool = False,
        input_middlewares: list[Any] | Callable | None = None,
        output_middlewares: list[Any] | Callable | None = None,
        guardrails: dict[str, Any] | None = None,
        enable_persistent_facts: bool = False,
        persistent_facts: Any | None = None,
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
            storage: Optional storage backend (e.g., SQLiteStorage)
            rag_pipeline: Optional Rag for RAG capabilities
            rag_pipelines: Optional dict of named Rag instances for multi-RAG
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
        self.code_mode = code_mode

        # Initialize tool registry
        self._tool_registry = ToolRegistry(agent_id=id or name)

        # Initialize API generator for code mode (lazy)
        self._api_generator: VirtualAPIGenerator | None = None

        # # Store tools list for later processing
        self._tools = tools or []

        # Memory & Storage
        self.memory = memory or AgentMemory()
        self.memory_manager = MemoryManager(self.memory, self.model)

        self.storage: AgentStorage | None = None
        if storage:
            # Pass max_messages from memory config to storage (for legacy support/defaults)
            self.storage = AgentStorage(
                storage=storage, max_messages=self.memory.num_history_responses
            )

        # Persistent Facts (Long-Term Memory)
        self.persistent_facts: Any | None = None
        if persistent_facts:
            self.persistent_facts = persistent_facts
        elif enable_persistent_facts and storage:
            # Auto-initialize with defaults using existing storage
            from framework.memory.persistent_facts import MemoryScope, PersistentFacts

            self.persistent_facts = PersistentFacts(
                storage=storage,  # Use existing storage backend
                scope=MemoryScope.USER,  # Default: USER scope
                auto_extract=True,
            )

        self.rag_pipeline = rag_pipeline
        self.rag_pipelines = rag_pipelines or {}

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
    def api_generator(self) -> VirtualAPIGenerator:
        """Get the API generator for code mode. Lazily initialized."""
        if self._api_generator is None:
            self._api_generator = VirtualAPIGenerator()
        return self._api_generator

    @property
    def api_surface(self) -> str:
        """Get the compact API surface for code mode.

        Returns:
            Compact API surface string ready for LLM prompts.
            Empty string if code_mode is disabled or no tools available.
        """
        if not self.code_mode:
            return ""

        # Ensure tool registry is populated
        if len(self._tool_registry) == 0 and self._tools:
            # This will be populated lazily during invoke
            # For now, return empty if not populated
            return ""

        return self.api_generator.generate_compact_api_surface(self._tool_registry)

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

    @property
    def tool_registry(self) -> ToolRegistry:
        """Get the tool registry for this agent.

        Returns:
          ToolRegistry instance containing all agent tools
        """
        return self._tool_registry

    def _infer_module_from_tool_name(self, tool_name: str) -> str:
        """Infer the module name from the tool name.

        Examples:
            'crm.get_user' -> 'crm'
            'gdrive.get_document' -> 'gdrive'
            'get_user' -> 'default'

        Args:
            tool_name: The name of the tool.

        Returns:
            The module name of the tool.
        """
        if "." in tool_name:
            return tool_name.split(".")[0]
        return "default"

    async def _register_python_tool(self, tool: Tool) -> None:
        """Register a Python @tool function in the registry.

        Args:
            tool: Tool instance from @tool decorator
        """
        # Use explicit module if provided, otherwise infer from tool name
        if hasattr(tool, "module") and tool.module is not None:
            module = tool.module
        else:
            module = self._infer_module_from_tool_name(tool.name)
            # Warn if falling back to "default" module (might be unintentional)
            if module == "default" and self._context and self._context.observability:
                self._context.observability.logger.info(
                    f"[WARNING] Tool '{tool.name}' assigned to 'default' module. "
                    f"Consider using @tool(module='...') or naming with dot notation (e.g., 'module.tool_name')"
                )

        # Create ToolSpec
        spec = ToolSpec.from_tool(
            tool,
            module=module,
            is_mcp=False,
        )

        # Register
        try:
            self._tool_registry.register(spec)
            if self._context and self._context.observability:
                self._context.observability.logger.info(
                    f"Registered Python tool: {tool.name} (module: {module})"
                )
        except ValueError as e:
            # Tool name collision
            if self._context and self._context.observability:
                self._context.observability.logger.info(
                    f"Failed to register tool '{tool.name}': {e}"
                )

    async def _register_mcp_server(self, server: MCPServer) -> None:
        """Register all tools from an MCP server.

        Args:
            server: MCPServer instance
        """
        try:
            # Get tools from server (this calls server.start() if needed)
            mcp_tools = await server.get_tools()

            # Use server name as module namespace
            module_name = server.name

            # Register each tool
            for mcp_tool in mcp_tools:
                spec = ToolSpec.from_tool(
                    mcp_tool, module=module_name, is_mcp=True, mcp_server_name=server.name
                )

                try:
                    self._tool_registry.register(spec)
                    if self._context and self._context.observability:
                        self._context.observability.logger.info(
                            f"Registered MCP tool: {mcp_tool.name} (server: {server.name}, module: {module_name})"
                        )
                except ValueError as e:
                    # Tool name collision
                    if self._context and self._context.observability:
                        self._context.observability.logger.info(
                            f"Failed to register MCP tool '{mcp_tool.name}' from server '{server.name}': {e}"
                        )

        except Exception as e:
            if self._context and self._context.observability:
                self._context.observability.logger.error(
                    f"Failed to get tools from MCP server '{server.name}': {e}"
                )
            raise

    async def _register_mcp_manager(self, manager: MCPManager) -> None:
        """
        Register all tools from an MCP manager by iterating servers directly.

        Args:
            manager: MCPManager instance
        """
        try:
            # Iterate servers directly to preserve server identity
            for server in manager.servers:
                await self._register_mcp_server(server)
        except Exception as e:
            if self._context and self._context.observability:
                self._context.observability.logger.error(
                    f"Failed to register tools from MCP manager: {e}"
                )
            raise

    async def _populate_tool_registry(self) -> None:
        """Populate tool registry from this list.

        Handles:
        - Regular @tool decorated functions (Tool instances)
        - MCPServer instance (async initialization)
        - MCPManager instance (async initialization)
        """

        if not self._tools:
            return

        for tool in self._tools:
            if isinstance(tool, MCPServer):
                await self._register_mcp_server(tool)
            # Handle MCPManager
            elif isinstance(tool, MCPManager):
                await self._register_mcp_manager(tool)
            # Handle regular @tool decorated functions
            elif hasattr(tool, "name") and hasattr(tool, "description"):
                await self._register_python_tool(tool)
            else:
                raise ValueError(f"Unknown tool type: {type(tool)}")

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
            # Empty messages are allowed (handled by model or treated as empty user turn)
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

    def _create_retrieve_evidence_tool(self, name_suffix: str = "") -> Any | None:
        """Create retrieve_evidence tool for RAG.

        Args:
            name_suffix: Optional suffix for tool name (used for multi-RAG)
        """
        rag_pipeline = self.rag_pipeline
        if not rag_pipeline:
            return None

        max_results = getattr(rag_pipeline, "max_results", 10)
        tool_name = f"retrieve_evidence{f'_{name_suffix}' if name_suffix else ''}"

        @tool(
            name=tool_name,
            description=f"Retrieve evidence from {'the ' + name_suffix + ' ' if name_suffix else ''}knowledge base to support your reasoning.",
        )
        async def retrieve_evidence(
            query: str,
            limit: int = 10,
        ) -> str:
            """
            Retrieve evidence to support reasoning.

            Args:
                query: What evidence do you need?
                limit: Maximum number of results to return (default: 10)

            Returns:
                JSON string of evidence with content, source, and metadata
            """
            try:
                effective_limit = min(limit, max_results)

                # Use query() for Rag
                results = await rag_pipeline.query(
                    query=query,
                    top_k=effective_limit,
                )

                if not results:
                    return "No relevant evidence found."

                # Format as evidence
                evidence = [
                    {
                        "content": getattr(doc, "content", str(doc)),
                        "source": getattr(doc, "source", None) or getattr(doc, "name", "unknown"),
                        "metadata": getattr(doc, "metadata", {}),
                    }
                    for doc in results
                ]

                return json.dumps(evidence, indent=2)
            except Exception as e:
                return f"Error retrieving evidence: {e!s}"

        return retrieve_evidence

    def _create_multi_rag_tools(self) -> list[Any]:
        """Create retrieve_evidence tools for multiple RAG pipelines."""
        tools = []
        for name, pipeline in self.rag_pipelines.items():
            # Temporarily set rag_pipeline for tool creation
            original = self.rag_pipeline
            self.rag_pipeline = pipeline
            tool_fn = self._create_retrieve_evidence_tool(name_suffix=name)
            self.rag_pipeline = original
            if tool_fn:
                tools.append(tool_fn)
        return tools

    async def ingest(
        self,
        path: str | None = None,
        url: str | None = None,
        text: str | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Ingest content into the agent's RAG knowledge base.

        This is a convenience passthrough to rag_pipeline.ingest().
        Allows ingestion without needing a separate reference to the pipeline.

        Args:
            path: File path to ingest
            url: URL to fetch and ingest
            text: Raw text to ingest
            name: Name for the content
            metadata: Additional metadata

        Returns:
            Content ID

        Raises:
            ValueError: If no rag_pipeline is configured

        Example:
            agent = Agent(..., rag_pipeline=rag)
            await agent.ingest(text="Python is...", name="Python Guide")
            response = await agent.invoke("What is Python?")
        """
        if not self.rag_pipeline:
            raise ValueError("No rag_pipeline configured. Cannot ingest.")

        return await self.rag_pipeline.ingest(
            path=path,
            url=url,
            text=text,
            name=name,
            metadata=metadata,
        )

    async def ingest_batch(self, items: list[dict[str, Any]]) -> list[str]:
        """Ingest multiple documents in batch.

        This is a convenience passthrough to rag_pipeline.ingest_batch().

        Args:
            items: List of dicts with keys: path, url, text, name, metadata

        Returns:
            List of content IDs

        Raises:
            ValueError: If no rag_pipeline is configured

        Example:
            agent = Agent(..., rag_pipeline=rag)
            ids = await agent.ingest_batch([
                {"text": "Python is...", "name": "Python Guide"},
                {"path": "./doc.txt", "name": "Documentation"},
            ])
        """
        if not self.rag_pipeline:
            raise ValueError("No rag_pipeline configured. Cannot ingest.")

        return await self.rag_pipeline.ingest_batch(items)

    async def ingest_directory(
        self,
        directory: str,
        pattern: str = "*.txt",
        recursive: bool = False,
    ) -> list[str]:
        """Ingest all files from a directory.

        This is a convenience passthrough to rag_pipeline.ingest_directory().

        Args:
            directory: Directory path
            pattern: Glob pattern for file matching
            recursive: Whether to search recursively

        Returns:
            List of content IDs

        Raises:
            ValueError: If no rag_pipeline is configured

        Example:
            agent = Agent(..., rag_pipeline=rag)
            ids = await agent.ingest_directory("./docs", pattern="*.md", recursive=True)
        """
        if not self.rag_pipeline:
            raise ValueError("No rag_pipeline configured. Cannot ingest.")

        return await self.rag_pipeline.ingest_directory(
            directory=directory,
            pattern=pattern,
            recursive=recursive,
        )

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

    async def _generate_code(
        self, user_message: str, api_surface: str, context: ExecutionContext
    ) -> str:
        """Generate Python code from user message using API surface.

        Args:
            user_message: User's request
            api_surface: Compact API surface description
            context: Execution context

        Returns:
            Generated Python code string
        """
        # Code generation system prompt
        system_prompt = f"""You are a Python code generation agent. Your task is to write Python code that accomplishes the user's request.

Available API:
{api_surface}

Rules:
- Import only from astra_api (e.g., `from astra_api import crm, gdrive`)
- Use print() statements for output (keep them concise)
- Handle errors gracefully with try/except if needed
- Do NOT print large JSON dumps - summarize results instead
- Write clean, readable Python code
- Focus on accomplishing the task efficiently

Example:
User: "Fetch user 123 and multiply their ID by 2"
Code:
```python
from astra_api import crm, math

user = crm.get_user(123)
result = math.multiply(user['id'], 2)
print(f"Result: {{result}}")
```

Now generate code for the user's request. Return ONLY the Python code, no explanations or markdown formatting."""

        # Prepare messages for code generation
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        # Invoke model to generate code
        try:
            response = await self.model.invoke(
                messages=messages,
                tools=None,  # No tools for code generation
                temperature=context.temperature,
                max_tokens=context.max_tokens or 2000,  # Higher limit for code
            )

            code = response.content or ""
            # Extract code from markdown code blocks if present
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()

            return code.strip()

        except Exception as e:
            if self._context and self._context.observability:
                self._context.observability.logger.error(f"Code generation failed: {e}")
            raise ModelError(f"Code generation failed: {e}") from e

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

        # 1.5. Lazy initialization: Populate tool registry if not done yet
        if self.code_mode and len(self._tool_registry) == 0 and self._tools:
            if self._context and self._context.observability:
                self._context.observability.logger.info(
                    f"Lazy initializing tool registry for agent '{self.name}'"
                )
            await self._populate_tool_registry()

            # Log registry stats after population
            if self._context and self._context.observability:
                tool_count = len(self._tool_registry)
                mcp_count = len(self._tool_registry.get_mcp_tools())
                python_count = len(self._tool_registry.get_python_tools())

                self._context.observability.logger.info(
                    f"Tool Registry initialized: {tool_count} total tools "
                    f"({python_count} Python, {mcp_count} MCP)"
                )

        # 1.6. Code Mode: Execute code generation and sandbox execution
        if self.code_mode and len(self._tool_registry) > 0:
            try:
                # Get API surface
                api_surface = self.api_surface
                if not api_surface:
                    # No tools available, fall through to traditional mode
                    if self._context and self._context.observability:
                        self._context.observability.logger.info(
                            "Code mode enabled but no tools available, falling back to traditional mode"
                        )
                else:
                    # Generate API file for sandbox
                    api_file_path = self.api_generator.generate_api_file(
                        self._tool_registry, output_dir=".astra/generated/"
                    )
                    if self._context and self._context.observability:
                        self._context.observability.logger.info(
                            f"Generated API file: {api_file_path}"
                        )

                    # Prepare execution context for code generation
                    code_context = ExecutionContext(
                        agent_id=self.id,
                        temperature=temperature or self.temperature,
                        max_tokens=max_tokens or self.max_tokens,
                        tools=None,  # No tools needed for code generation
                        observability=self.context.observability if self._context else None,
                    )

                    # Generate code via LLM
                    if self._context and self._context.observability:
                        self._context.observability.logger.info(
                            "Generating Python code for code execution mode"
                        )
                    generated_code = await self._generate_code(message, api_surface, code_context)

                    if self._context and self._context.observability:
                        self._context.observability.logger.info(
                            f"Generated code:\n{generated_code[:200]}..."  # Log first 200 chars
                        )

                    # Execute code in sandbox
                    # Use longer timeout for code execution (60s) to allow for multiple tool calls
                    executor = SandboxExecutor(agent=self)
                    result = await executor.execute(generated_code, timeout=60.0)

                    # Synthesize execution results into a meaningful response
                    # This transforms raw execution output into a persona-aligned response
                    synthesized_response = await synthesize_response(
                        agent=self,
                        user_query=message,
                        execution_result=result,
                        context=code_context,
                    )

                    # Save synthesized response to storage if enabled
                    thread_id = kwargs.get("thread_id")
                    if self.storage and thread_id:
                        await self.storage.add_message(
                            thread_id=thread_id, role="user", content=message
                        )
                        await self.storage.add_message(
                            thread_id=thread_id,
                            role="assistant",
                            content=synthesized_response,
                        )

                    # Return synthesized response
                    return synthesized_response

            except Exception as e:
                # Log error and fall back to traditional mode
                if self._context and self._context.observability:
                    self._context.observability.logger.error(
                        f"Code execution mode failed, falling back to traditional mode: {e}"
                    )
                # Fall through to traditional tool calling

        # 2. Add retrieve_evidence tool if rag_pipeline available
        final_tools = list(tools) if tools else list(self.tools) if self.tools else []
        if self.rag_pipeline:
            evidence_tool = self._create_retrieve_evidence_tool()
            if evidence_tool:
                final_tools.append(evidence_tool)

        # Add multi-RAG tools if rag_pipelines provided
        if self.rag_pipelines:
            multi_rag_tools = self._create_multi_rag_tools()
            final_tools.extend(multi_rag_tools)

        # 3. Prepare execution context
        context = ExecutionContext(
            agent_id=self.id,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            tools=final_tools,
            observability=self.context.observability if self._context else None,
        )

        # 4. Prepare messages
        thread_id = kwargs.get("thread_id")

        # Load history if enabled
        history = None
        if self.storage and thread_id and self.memory.add_history_to_messages:
            # Calculate max tokens for context (use token_limit if set, else default to 8000 with safety margin)
            # Reserve 20% for response generation
            max_context_tokens = None
            if self.memory.token_limit:
                max_context_tokens = int(self.memory.token_limit * 0.8)  # Reserve 20% for response
            else:
                # Default: assume 10k context window, reserve 2k for response
                max_context_tokens = 8000

            history = await self.memory_manager.get_context(
                thread_id, self.storage, max_tokens=max_context_tokens
            )

        messages = self._prepare_messages(message, context, history=history)

        # Middleware Context
        middleware_context = MiddlewareContext(
            agent=self,
            thread_id=thread_id,
        )

        # Extract facts if persistent facts enabled
        user_id = kwargs.get("user_id")
        if self.persistent_facts and self.persistent_facts.auto_extract and user_id:
            extracted_facts = await self.persistent_facts.extract_from_messages(
                messages=[{"role": "user", "content": message}],
                scope_id=user_id,
                model=self.model,
            )
            # Store extracted facts
            for fact in extracted_facts:
                fact.scope_id = user_id
                try:
                    existing = await self.persistent_facts.get(key=fact.key, scope_id=user_id)
                    if existing:
                        await self.persistent_facts.update(
                            key=fact.key, value=fact.value, scope_id=user_id
                        )
                    else:
                        await self.persistent_facts.add(
                            key=fact.key,
                            value=fact.value,
                            scope_id=user_id,
                            tags=fact.tags,
                        )
                except Exception:
                    # Ignore extraction errors
                    pass

        # Retrieve relevant facts for context
        if self.persistent_facts and user_id:
            relevant_facts = await self.persistent_facts.get_all(scope_id=user_id)
            if relevant_facts:
                # Add facts to context as system message
                facts_text = "\n".join(
                    [f"- {fact.key}: {fact.value}" for fact in relevant_facts[:10]]
                )
                facts_message = {
                    "role": "system",
                    "content": f"User context:\n{facts_text}",
                }
                # Insert after system instructions but before history
                if messages and messages[0].get("role") == "system":
                    messages.insert(1, facts_message)
                else:
                    messages.insert(0, facts_message)

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

                # Extract tool call id from tool call
                corresponding_tool_call = (
                    response.tool_calls[idx] if idx < len(response.tool_calls) else None
                )
                tool_call_id = (
                    corresponding_tool_call.get("id")
                    if corresponding_tool_call and isinstance(corresponding_tool_call, dict)
                    else None
                )

                messages.append(
                    {
                        "role": "tool",
                        "name": tr["tool"],
                        "content": tool_result_content,
                        "tool_call_id": tool_call_id,
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

        final_tools = list(tools) if tools else list(self.tools) if self.tools else []
        if self.rag_pipeline:
            evidence_tool = self._create_retrieve_evidence_tool()
            if evidence_tool:
                final_tools.append(evidence_tool)

        # Add multi-RAG tools if rag_pipelines provided
        if self.rag_pipelines:
            multi_rag_tools = self._create_multi_rag_tools()
            final_tools.extend(multi_rag_tools)

        context = ExecutionContext(
            agent_id=self.id,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            tools=final_tools,
            observability=self.context.observability if self._context else None,
        )

        thread_id = kwargs.get("thread_id")

        # Load history if enabled
        history = None
        if self.storage and thread_id and self.memory.add_history_to_messages:
            # Calculate max tokens for context
            max_context_tokens = None
            if self.memory.token_limit:
                max_context_tokens = int(self.memory.token_limit * 0.8)
            else:
                max_context_tokens = 8000

            history = await self.memory_manager.get_context(
                thread_id, self.storage, max_tokens=max_context_tokens
            )

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
