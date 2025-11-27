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

from collections.abc import Callable
from typing import Any
import uuid

from framework.astra import AstraContext
from framework.models import Model


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
        max_retries: int = 3,
        temperature: float = 0.7,
        # Handle this in the invoke/stream methods as well.
        max_tokens: int | None = None,
        stream: bool = False,
        max_messages: int = 10,
        enable_message_summary: bool = False,
        input_middlewares: list[Any] | Callable | None = None,
        output_middlewares: list[Any] | Callable | None = None,
        guardrails: dict[str, Any] | None = None,
        output_format: Any | None = None,
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
            max_retries: Maximum retry attempts for failed requests (default: 3)
            temperature: Sampling temperature for model responses (default: 0.7, range: 0.0-2.0)
            max_tokens: Maximum tokens to generate per response (default: 4096)
            stream: Whether to stream responses by default (default: False)
            max_messages: Number of recent messages to keep in context (default: 10)
            enable_message_summary: Whether to summarize old messages instead of dropping them (default: False)
            input_middlewares: Optional list of input middlewares
            output_middlewares: Optional list of output middlewares
            guardrails: Optional guardrails configuration
            output_format: Optional output format
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
        self.storage = storage
        self.knowledge = knowledge

        # Execution config
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream = stream
        self.max_messages = max_messages
        self.enable_message_summary = enable_message_summary

        # Middleware / guardrails / formatting
        self.input_middlewares = input_middlewares
        self.output_middlewares = output_middlewares
        self.guardrails = guardrails
        self.output_format = output_format

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

    def __repr__(self) -> str:
        """Minimal, fast string representation of the Agent."""
        return f"Agent(id={self.id!r}, name={self.name!r})"

    def __str__(self) -> str:
        """Human-friendly representation."""
        return self.__repr__()
