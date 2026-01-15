"""
Team class for Astra Framework.

A Team coordinates multiple Agents to accomplish complex tasks using code_mode.
The LLM generates Python code that calls agent tools, which is then executed
in an isolated sandbox.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
import dataclasses
from typing import TYPE_CHECKING, Any

from framework.agents.agent import Agent
from framework.memory import Memory
from framework.middlewares.base import InputMiddleware, OutputMiddleware
from framework.models.base import Model
from framework.storage.memory import AgentStorage


if TYPE_CHECKING:
    from framework.code_mode.semantic import TeamSemanticLayer
    from framework.code_mode.tool_registry import ToolRegistry


# EXCEPTIONS
class TeamError(Exception):
    """Base exception for team-related errors."""


class DelegationError(TeamError):
    """Raised when delegation to a member fails."""


class MemberNotFoundError(TeamError):
    """Raised when a team member cannot be found by id/name."""


class TeamTimeoutError(TeamError):
    """Raised when team execution exceeds the timeout."""


# DATA CLASSES
@dataclasses.dataclass
class TeamMember:
    """
    Wrapper for an agent/team that is part of a Team.

    The `agent` field holds the actual Agent or nested Team.
    Other fields (`name`, `id`, `description`) are optional metadata
    that can override the agent's own properties for display purposes.

    Note: If name/id are not provided, the semantic layer will use
    the agent's own name/id properties directly.
    """

    agent: Agent | Team
    name: str | None = None
    id: str | None = None
    description: str | None = None


@dataclasses.dataclass
class StreamEvent:
    """
    SSE event for team streaming.

    Event types:
    - status: Progress updates (e.g., "Generating code...")
    - code_generated: Code has been generated
    - tool_call: A tool is being called
    - tool_result: Tool execution completed
    - content: Response content chunk
    - error: An error occurred
    - done: Streaming complete
    """

    event_type: str
    data: dict[str, Any]

    def __str__(self) -> str:
        """String representation for backward compatibility."""
        if self.event_type == "content":
            return self.data.get("text", "")
        elif self.event_type == "status":
            return self.data.get("message", "")
        return ""


# =============================================================================
# TEAM CLASS
# =============================================================================


class Team:
    """
    Team class for coordinating multiple agents.

    A Team orchestrates multiple Agents (or nested Teams) to accomplish
    complex tasks. It uses code_mode by default: the LLM generates Python
    code that calls agent tools directly, executed in an isolated sandbox.

    Example:
        team = Team(
            id="order-team",
            name="Order Processing",
            description="Handles order workflow",
            model=Gemini("gemini-2.5-flash"),
            members=[inventory_agent, payment_agent],
            instructions="1. Check inventory → 2. Process payment",
        )

        # Execute the team
        result = await team.invoke("Process order #123")
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        model: Model,
        members: list[Agent | Team | TeamMember],
        *,
        instructions: str,
        storage: AgentStorage | None = None,
        memory: Memory | None = None,
        timeout: float = 300.0,
        max_retries: int = 2,
        input_middlewares: list[InputMiddleware] | None = None,
        output_middlewares: list[OutputMiddleware] | None = None,
        guardrails: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.id = id
        self.name = name
        self.description = description

        # Model used for code generation
        self.model = model
        self.instructions = instructions or ""
        self.metadata = metadata or {}

        # Normalize members: convert raw Agents to TeamMember if needed
        self.members: list[TeamMember] = []
        for m in members:
            if isinstance(m, TeamMember):
                self.members.append(m)
            else:
                # Wrap raw Agent/Team in TeamMember
                self.members.append(TeamMember(agent=m))

        # Execution control
        self.timeout = timeout
        self.max_retries = max_retries

        # Memory & Storage
        self.memory = memory or Memory()
        self.storage = storage

        # Middlewares & Guardrails (for future use)
        self.input_middlewares = input_middlewares
        self.output_middlewares = output_middlewares
        self.guardrails = guardrails

        # Lazy-initialized semantic layer (cached after first access)
        self._semantic_layer: TeamSemanticLayer | None = None

    # PROPERTIES
    @property
    def semantic_layer(self) -> TeamSemanticLayer:
        """
        Get the semantic layer for this team. Lazily initialized.

        The semantic layer is a structured representation of all tools
        available across team members. It's used to:
        1. Generate Python stubs for the LLM
        2. Build the tool map for sandbox execution
        """
        if self._semantic_layer is None:
            from framework.code_mode.semantic import build_semantic_layer

            self._semantic_layer = build_semantic_layer(self)
        return self._semantic_layer

    @property
    def flat_members(self) -> list[TeamMember]:
        """
        Recursively flatten nested teams to get all agent members.

        When a Team contains another Team as a member, this property expands it
        to get the actual agents. Returns a flat list of TeamMember objects
        where each member.agent is an Agent (not a nested Team).

        This is used by:
        - Sandbox: to build tool maps and generate stubs
        - Semantic layer: to flatten the team structure

        Returns:
            List of TeamMember objects with Agent instances (no nested Teams)
        """
        flat: list[TeamMember] = []

        def _recurse(members: list[TeamMember]) -> None:
            for member in members:
                agent_or_team = member.agent
                if isinstance(agent_or_team, Team):
                    # Nested team: recursively expand its members
                    _recurse(agent_or_team.members)
                else:
                    # Agent: add to flat list
                    flat.append(member)

        _recurse(self.members)
        return flat

    @property
    def tool_registry(self) -> ToolRegistry:
        """
        Get the tool registry for this team. Lazily initialized.

        The registry maps "agent_name.tool_name" to ToolSpec objects,
        providing a unified interface for tool lookup and execution.

        Returns:
            ToolRegistry with all tools from flat_members
        """
        if not hasattr(self, "_tool_registry") or self._tool_registry is None:
            from framework.code_mode.tool_registry import ToolRegistry, ToolSpec

            self._tool_registry = ToolRegistry(agent_id=self.id)

            for member in self.flat_members:
                agent = member.agent
                # Use member id/name or fall back to agent's name
                raw_name = member.id or member.name or getattr(agent, "name", None) or "unknown"
                module_name = raw_name.replace("-", "_").replace(" ", "_").lower()

                # Get tools from the underlying agent
                agent_tools = getattr(agent, "tools", []) or []

                for tool in agent_tools:
                    spec = ToolSpec.from_tool(tool, module=module_name)
                    self._tool_registry.register(spec)

        return self._tool_registry

    # EXECUTION METHODS
    async def invoke(
        self,
        query: str,
        *,
        timeout: float | None = None,
    ) -> str:
        """
        Execute the team on a query and return the final response.

        This is the main entry point for running a team. It:
        1. Creates a Sandbox with this team's semantic layer
        2. Generates Python code from the query using the LLM
        3. Executes the code in an isolated subprocess
        4. Returns the synthesized response

        Args:
            query: The user's request/question
            thread_id: Optional conversation thread for memory (not yet used)
            timeout: Override default timeout (seconds)

        Returns:
            The final response string from the team

        Raises:
            TeamTimeoutError: If execution exceeds timeout
            TeamError: If execution fails
        """
        from framework.code_mode.sandbox import Sandbox

        # Create sandbox with this team
        sandbox = Sandbox(self)

        # Use provided timeout or fall back to team's default
        exec_timeout = timeout or self.timeout

        # Run the sandbox: generate code → execute → return result
        # sandbox.run() handles:
        #   1. generate_code() - LLM creates Python code
        #   2. execute() - Runs code in subprocess with IPC for tool calls
        result = await sandbox.run(query, timeout=exec_timeout)

        # Check for execution errors
        if not result.success:
            raise TeamError(f"Team execution failed: {result.stderr or result.output}")

        return result.output

    async def stream(
        self,
        query: str,
        *,
        timeout: float | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Stream the team execution, yielding SSE events.

        Yields StreamEvent objects with types:
        - status: Progress updates
        - code_generated: Code has been generated (includes code preview)
        - tool_call: A tool is being called
        - tool_result: Tool execution completed
        - content: Response content chunk
        - error: An error occurred
        - done: Streaming complete

        Args:
            query: The user's request/question
            timeout: Override default timeout (seconds)

        Yields:
            StreamEvent objects for SSE streaming
        """
        from framework.code_mode.sandbox import Sandbox

        yield StreamEvent("status", {"message": "Generating code..."})

        sandbox = Sandbox(self)
        exec_timeout = timeout or self.timeout

        # Generate code first
        try:
            code = await sandbox.generate_code(query)
            yield StreamEvent(
                "code_generated",
                {
                    "message": "Code generated. Executing...",
                    "code_preview": code[:200] + "..." if len(code) > 200 else code,
                },
            )
        except Exception as e:
            yield StreamEvent("error", {"message": f"Error generating code: {e}"})
            return

        # Execute and stream results
        try:
            result = await sandbox.execute(code, timeout=exec_timeout)

            # Report tool calls
            if result.tool_calls:
                for i, tool_call in enumerate(result.tool_calls):
                    yield StreamEvent(
                        "tool_call",
                        {
                            "index": i,
                            "tool_name": tool_call.get("tool", "unknown"),
                            "arguments": tool_call.get("arguments", {}),
                        },
                    )
                    yield StreamEvent(
                        "tool_result",
                        {
                            "index": i,
                            "tool_name": tool_call.get("tool", "unknown"),
                            "result": tool_call.get("result", ""),
                            "success": "error" not in tool_call,
                        },
                    )

            # Yield final output
            if result.success:
                yield StreamEvent("content", {"text": result.output})
                yield StreamEvent("done", {"status": "complete"})
            else:
                yield StreamEvent(
                    "error", {"message": f"Execution failed: {result.stderr or 'Unknown error'}"}
                )

        except Exception as e:
            yield StreamEvent("error", {"message": f"Execution error: {e}"})
