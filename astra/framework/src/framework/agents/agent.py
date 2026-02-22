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
import json
import re
from typing import TYPE_CHECKING, Any

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
    from framework.code_mode.semantic import EntitySemanticLayer


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
        rag_pipeline: Any | None = None,
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
            tools: Optional list of tools (local functions or MCPToolSource instances)
            code_mode: Whether to enable code mode (default: True)
            storage: Optional storage backend
            rag_pipeline: Optional Rag instance for RAG capabilities
            memory: Optional memory configuration
            max_retries: Maximum retry attempts for failed requests (default: 3)
            temperature: Sampling temperature for model responses (default: 0.7)
            max_tokens: Maximum tokens to generate per response
            stream_enabled: Whether to stream responses by default (default: False)
            middlewares: Optional list of middlewares (guardrails, validation, etc.)
        """
        # Basic identifiers & metadata
        self.name = name
        provided_id = str(id).strip() if id is not None else ""
        if provided_id:
            self.id = provided_id
        else:
            normalized_name = re.sub(r"[^a-z0-9]+", "-", self.name.lower())
            normalized_name = re.sub(r"-+", "-", normalized_name).strip("-")
            if not normalized_name:
                normalized_name = "unknown"
            self.id = f"agent-{normalized_name}"
        self.description = description

        # Core behavior config
        self.instructions = instructions
        self.model = model
        self.tools = tools
        self.code_mode = code_mode

        # Memory & Storage
        self.memory = memory or Memory()
        self.storage = storage

        # RAG Support
        self.rag_pipeline = rag_pipeline

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

        # Calculate effective input middlewares
        input_middlewares = [
            m for m in self.middlewares if MiddlewareStage.INPUT in m.effective_stages
        ]

        if not input_middlewares:
            return data, None

        from observability import LogLevel, log, span

        async with span(
            "middleware.input",
            attributes={
                "middleware_count": len(input_middlewares),
                "middleware_names": [m.__class__.__name__ for m in input_middlewares],
            },
        ):
            await log(LogLevel.INFO, "Running input middlewares")
            ctx = MiddlewareContext(data=data)
            ctx = await run_middlewares(self.middlewares, MiddlewareStage.INPUT, ctx)

            if ctx.stop:
                error_msg = ctx.error or "Input rejected by middleware"
                await log(LogLevel.ERROR, f"Middleware error: {error_msg}")
                return data, error_msg

            await log(LogLevel.INFO, "All input middlewares completed successfully")
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

    # CODE MODE PROVIDER PROPERTIES
    @property
    def provider_type(self) -> str:
        return "AGENT"

    def build_semantic_layer(
        self, tool_definitions: dict[str, Any] | None = None
    ) -> EntitySemanticLayer:
        """
        Build the semantic layer for this agent.

        This builds a structured representation of all tools (local + MCP)
        available for this agent. It's used to:
        1. Generate Python stubs for the LLM
        2. Build the tool map for sandbox execution

        Args:
            tool_definitions: Optional dict of ToolDefinition objects from DB.
                              If provided, MCP tools are included from DB.
                              Keys are slugs, values are ToolDefinition objects.

        Returns:
            EntitySemanticLayer with all tools
        """
        from framework.code_mode.semantic import (
            build_domain_schema,
            build_entity_semantic_layer,
            build_mcp_domain_schema,
        )
        from framework.tool import Tool
        from framework.tool.mcp.toolkit import MCPToolkit

        # Separate local tools and MCP toolkits
        local_tools: list[Tool] = []
        mcp_toolkits: list[MCPToolkit] = []

        for t in self.tools or []:
            if isinstance(t, Tool):
                local_tools.append(t)
            elif isinstance(t, MCPToolkit):
                mcp_toolkits.append(t)

        # Build domain for the agent with local tools
        domain = build_domain_schema(
            id=self.id,
            name=self.name,
            description=self.description,
            tools=local_tools,
        )

        # Add MCP tools as additional domains (using shared builder)
        mcp_domains = []
        seen_mcp_domains: set[str] = set()
        for mcp in mcp_toolkits:
            if mcp.slug in seen_mcp_domains:
                continue
            seen_mcp_domains.add(mcp.slug)
            mcp_domain = build_mcp_domain_schema(mcp.slug, mcp.name, tool_definitions)
            if mcp_domain:
                mcp_domains.append(mcp_domain)

        all_domains = [domain, *mcp_domains]

        return build_entity_semantic_layer(
            provider_id=self.id,
            provider_name=self.name,
            provider_description=self.description or f"Agent: {self.name}",
            provider_instructions=self.instructions,
            domains=all_domains,
            metadata={"is_agent": True, "mcp_count": len(mcp_toolkits)},
        )

    async def get_history(self, thread_id: str) -> list[dict[str, Any]]:
        """
        Get conversation history for this agent.
        """
        if self.memory and self.storage:
            return await self.memory.get_context(thread_id, self.storage)
        return []

    # RAG Support Methods
    def _create_retrieve_evidence_tool(self, name_suffix: str = "") -> Any | None:
        """Create retrieve_evidence tool for RAG.

        When an agent is created with rag_pipeline, this method auto-generates
        a `retrieve_evidence` tool that queries the knowledge base.

        Args:
            name_suffix: Optional suffix for tool name (used for multi-RAG)

        Returns:
            A Tool instance or None if no RAG pipeline configured
        """
        from pydantic import BaseModel, Field

        from framework.tool import Tool

        rag_pipeline = self.rag_pipeline
        if not rag_pipeline:
            return None

        max_results = getattr(rag_pipeline, "max_results", 10)
        tool_name = f"retrieve_evidence{f'_{name_suffix}' if name_suffix else ''}"
        tool_description = f"Retrieve evidence from {'the ' + name_suffix + ' ' if name_suffix else ''}knowledge base to support your reasoning."

        # Define Pydantic schemas
        class RetrieveEvidenceInput(BaseModel):
            """Input for retrieve_evidence tool."""

            query: str = Field(..., description="What evidence do you need?")
            limit: int = Field(default=10, description="Maximum number of results to return")

        class RetrieveEvidenceOutput(BaseModel):
            """Output for retrieve_evidence tool."""

            result: str = Field(..., description="JSON string of evidence or error")

        async def retrieve_evidence_fn(input_data: RetrieveEvidenceInput) -> RetrieveEvidenceOutput:
            """Retrieve evidence to support reasoning."""
            try:
                effective_limit = min(input_data.limit, max_results)

                # Use query() for Rag
                results = await rag_pipeline.query(
                    query=input_data.query,
                    top_k=effective_limit,
                )

                if not results:
                    return RetrieveEvidenceOutput(result="No relevant evidence found.")

                # Format as evidence
                evidence = [
                    {
                        "content": getattr(doc, "content", str(doc)),
                        "source": getattr(doc, "source", None) or getattr(doc, "name", "unknown"),
                        "metadata": getattr(doc, "metadata", {}),
                    }
                    for doc in results
                ]

                return RetrieveEvidenceOutput(result=json.dumps(evidence, indent=2))
            except Exception as e:
                return RetrieveEvidenceOutput(result=f"Error retrieving evidence: {e!s}")

        return Tool(
            name=tool_name,
            description=tool_description,
            func=retrieve_evidence_fn,
            input_schema=RetrieveEvidenceInput,
            output_schema=RetrieveEvidenceOutput,
        )

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

    # Code Mode Methods
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

        return generate_stubs(self.build_semantic_layer())

    async def generate_parse_validate_code(self, user_query: str) -> str:
        """
        Generate Python code from a user query.

        Uses the agent's tools (via semantic layer) to build a prompt for the LLM,
        which then generates Python code that calls the appropriate tools.

        Args:
            user_query: The user's request/question

        Returns:
            Python code string ready for sandbox execution

        Example:
            >>> code = await agent.generate_parse_validate_code("Get Apple stock price")
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
        context: dict[str, Any] | None = None,
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
            context: Optional runtime context dict (e.g., store_id, user_tier)

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
            resource_id=self.id,
            resource_name=self.name,
        )

        # Execute in sandbox
        sandbox = Sandbox(self)
        result = await sandbox.run(
            query, timeout=timeout or self.timeout, thread_id=thread_id, context=context
        )
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
        context: dict[str, Any] | None = None,
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
            context: Optional runtime context dict (e.g., store_id, user_tier)

        Yields:
            StreamEvent objects for SSE streaming
        """
        from observability import LogLevel, log, span

        from framework.code_mode.sandbox import Sandbox
        from framework.storage.persistence import save_assistant_message, save_user_message
        from framework.team.team import StreamEvent

        # Run INPUT middlewares (instrumentation handled internally)
        query, error = await self._run_input_middleware(query)
        if error:
            yield StreamEvent(event_type="error", data={"message": error})
            return

        # Save user message with instrumentation
        async with span(
            "persistence.save_user_message",
            attributes={
                "thread_id": thread_id or "new",
                "message_length": len(query),
                "storage_backend": self.storage.__class__.__name__ if self.storage else "none",
            },
        ):
            await log(LogLevel.INFO, "Saving user message to storage")
            thread_id = await save_user_message(
                self.storage,
                thread_id,
                query,
                resource_type="agent",
                resource_id=self.id,
                resource_name=self.name,
            )
            await log(LogLevel.DEBUG, f"Message saved with thread_id: {thread_id}")
            await log(LogLevel.INFO, "Persistence complete")

        yield StreamEvent(event_type="status", data={"message": "Generating code..."})

        # Create sandbox
        sandbox = Sandbox(self)
        exec_timeout = timeout or self.timeout

        # Generate code first
        try:
            code = await sandbox.generate_parse_validate_code(
                query, thread_id=thread_id, context=context
            )

            # Check for clarification (missing data)
            clarification = sandbox._extract_clarification(code)
            if clarification:
                question = clarification.get("question", "Could you provide more details?")
                await save_assistant_message(self.storage, thread_id, question)
                yield StreamEvent(event_type="content", data={"text": question})
                yield StreamEvent(event_type="done", data={"status": "needs_clarification"})
                return

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

        # Build + validate DSL workflow from generated code
        try:
            await sandbox.build_dsl_workflow(code)
            dsl_workflow = getattr(sandbox, "_dsl_workflow", None)
            if dsl_workflow:
                yield StreamEvent(
                    event_type="status",
                    data={
                        "message": "DSL workflow built and validated.",
                        "dsl_summary": dsl_workflow.summary(),
                    },
                )
        except Exception as e:
            yield StreamEvent(event_type="error", data={"message": f"DSL build failed: {e}"})
            return

        # Execute and stream results
        try:
            result = await sandbox.execute_dsl(timeout=exec_timeout)

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
            import traceback

            tb = traceback.format_exc()
            yield StreamEvent(
                event_type="error", data={"message": f"Execution error: {e}", "traceback": tb}
            )

    def __repr__(self) -> str:
        """Minimal string representation of the Agent."""
        return f"Agent(id={self.id!r}, name={self.name!r})"

    def __str__(self) -> str:
        """Human-friendly representation."""
        return self.__repr__()
