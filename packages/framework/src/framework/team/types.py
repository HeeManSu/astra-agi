"""
Types, exceptions, and constants for the Team module.

This module contains all foundational definitions used across the team module:
- TeamMember and TeamExecutionContext dataclasses
- Team-specific exceptions
- DELEGATION_TOOL constant
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import TYPE_CHECKING, Any

from framework.agents.agent import Agent
from framework.agents.execution import StreamEvent


if TYPE_CHECKING:
    # Import Team here to avoid circular dependency
    # Reason: TeamMember uses Team type hint, but Team is defined in team.py
    from framework.team.team import Team


# EXCEPTIONS


class TeamError(Exception):
    """Base exception for all team errors."""


class DelegationError(TeamError):
    """Raised when delegation fails."""


class MemberNotFoundError(TeamError):
    """Raised when a requested member doesn't exist."""


class TeamTimeoutError(TeamError):
    """Raised when team execution exceeds timeout."""


# CONSTANTS

DELEGATION_TOOL = {
    "name": "delegate_task_to_member",
    "description": (
        "Delegate a task to a team member. The member will execute the task "
        "and return a result. Use this when the user's request requires "
        "specialized expertise from one of your team members."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "string",
                "description": "The ID of the team member to delegate to. Must match one of the available member IDs.",
            },
            "task": {
                "type": "string",
                "description": (
                    "A clear, specific description of the task for the member to complete. "
                    "Include any context or requirements the member needs to know."
                ),
            },
        },
        "required": ["member_id", "task"],
    },
}


@dataclass
class TeamMember:
    """
    Represents a member agent or team in a team.

    In hierarchical mode, a member can be either:
    - Agent: Regular agent member that executes tasks directly
    - Team: Nested team (for hierarchical mode) that can further delegate

    Attributes:
        id: Unique identifier for the member (used in delegation)
        name: Human-readable name of the member
        description: Description of member's capabilities and responsibilities
        agent: The Agent or Team instance that will execute delegated tasks.
              In hierarchical mode, this can be a Team instance for nested delegation.
        priority: Priority level for routing (future use)
        enabled: Whether this member is currently enabled

    Example:
        ```python
        # Regular agent member
        member = TeamMember(
            id="researcher",
            name="Research Agent",
            description="Conducts research",
            agent=research_agent,  # Agent instance
        )

        # Nested team member (hierarchical mode)
        sub_team = Team(...)
        member = TeamMember(
            id="research-team",
            name="Research Team",
            description="Team of researchers",
            agent=sub_team,  # Team instance
        )
        ```
    """

    id: str
    name: str
    description: str
    agent: Agent | Team  # Can be Agent or Team for hierarchical mode
    priority: int = 0
    enabled: bool = True

    def is_team(self) -> bool:
        """
        Check if this member is a Team instance (for hierarchical mode).

        Returns:
            True if member.agent is a Team instance, False otherwise

        Example:
            ```python
            if member.is_team():
                # Handle nested team delegation
                nested_team = member.agent
            ```
        """
        # Import here to avoid circular dependency at runtime
        # Reason: Team class is defined in team.py, but TYPE_CHECKING handles type hints
        from framework.team.team import Team

        return isinstance(self.agent, Team)

    def is_agent(self) -> bool:
        """
        Check if this member is an Agent instance.

        Returns:
            True if member.agent is an Agent instance, False otherwise

        Example:
            ```python
            if member.is_agent():
                # Handle direct agent execution
                agent = member.agent
            ```
        """
        return isinstance(self.agent, Agent)


@dataclass
class TeamExecutionContext:
    """
    Execution context for team runs.

    Tracks state throughout a team execution including delegation count,
    timing, runtime state, and recursion depth (for hierarchical mode).
    Thread-safe for parallel execution.

    Attributes:
        run_id: Unique identifier for this team run
        thread_id: Conversation thread ID (for memory)
        user_id: User identifier (optional)
        start_time: Timestamp when execution started
        timeout: Global timeout for entire team run (seconds)
        max_delegations: Maximum number of delegations allowed
        delegation_count: Current number of delegations performed
        delegations: List of delegation records
        state: Runtime state dictionary
        elapsed_time: Time elapsed since start
        recursion_depth: Current recursion depth (for hierarchical mode)
        max_recursion_depth: Maximum allowed recursion depth (for hierarchical mode)

    Example:
        ```python
        context = TeamExecutionContext(
            run_id="run-123",
            thread_id="thread-456",
            user_id="user-789",
            start_time=time.time(),
            timeout=300.0,
            max_delegations=10,
            max_recursion_depth=3,  # Allow up to 3 levels of nesting
        )
        ```
    """

    run_id: str
    thread_id: str | None
    user_id: str | None
    start_time: float
    timeout: float
    max_delegations: int

    # Runtime state
    delegation_count: int = 0
    delegations: list[dict[str, Any]] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)

    # Time tracking
    elapsed_time: float = 0.0

    # Recursion tracking for hierarchical mode
    # Reason: Hierarchical mode allows nested teams, so we need to track
    # how deep we've gone to prevent infinite recursion
    recursion_depth: int = 0
    max_recursion_depth: int = 3

    def check_timeout(self) -> None:
        """
        Check if execution has exceeded timeout.

        This method calculates the elapsed time and compares it against
        the timeout threshold. If exceeded, raises TeamTimeoutError.

        Raises:
            TeamTimeoutError: If timeout exceeded

        Example:
            ```python
            context.check_timeout()  # Raises if timeout exceeded
            ```
        """
        # Calculate elapsed time since start
        # Reason: We need to track how long the execution has been running
        self.elapsed_time = time.time() - self.start_time

        # Check if we've exceeded the timeout
        if self.elapsed_time > self.timeout:
            raise TeamTimeoutError(
                f"Team execution exceeded timeout of {self.timeout}s. "
                f"Elapsed: {self.elapsed_time:.2f}s"
            )

    def check_delegation_limit(self) -> None:
        """
        Check if delegation limit has been reached.

        This prevents infinite delegation loops by enforcing a maximum
        number of delegations per team run.

        Raises:
            DelegationError: If max delegations exceeded

        Example:
            ```python
            context.check_delegation_limit()  # Raises if limit exceeded
            ```
        """
        if self.delegation_count >= self.max_delegations:
            raise DelegationError(
                f"Maximum delegations ({self.max_delegations}) exceeded. "
                f"Current count: {self.delegation_count}"
            )

    def increment_delegation_count(self) -> None:
        """
        Increment delegation count (atomic operation).

        This is thread-safe because integer increment is atomic in Python
        (due to GIL). Used to track how many delegations have occurred.

        Example:
            ```python
            context.increment_delegation_count()  # Increment counter
            ```
        """
        self.delegation_count += 1

    def check_recursion_limit(self) -> None:
        """
        Check if recursion depth limit has been exceeded.

        This prevents infinite recursion in hierarchical mode where teams
        can contain nested teams. If the recursion depth exceeds the maximum,
        raises DelegationError.

        Raises:
            DelegationError: If recursion depth exceeded

        Example:
            ```python
            context.check_recursion_limit()  # Raises if depth exceeded
            ```
        """
        if self.recursion_depth >= self.max_recursion_depth:
            raise DelegationError(
                f"Maximum recursion depth ({self.max_recursion_depth}) exceeded. "
                f"Current depth: {self.recursion_depth}"
            )

    def increment_depth(self) -> None:
        """
        Increment recursion depth and check limit.

        Called when delegating to a nested team in hierarchical mode.
        First checks if we've exceeded the limit, then increments.

        Raises:
            DelegationError: If recursion depth would exceed limit

        Example:
            ```python
            context.increment_depth()  # Increment and check limit
            ```
        """
        # Check limit before incrementing
        # Reason: We want to fail fast if we're about to exceed the limit
        self.check_recursion_limit()
        self.recursion_depth += 1

    def decrement_depth(self) -> None:
        """
        Decrement recursion depth (when returning from nested team).

        Called when returning from a nested team invocation in hierarchical mode.
        Ensures depth never goes below 0.

        Example:
            ```python
            context.decrement_depth()  # Decrement when returning
            ```
        """
        # Ensure depth never goes negative
        # Reason: Prevents underflow errors and maintains consistency
        self.recursion_depth = max(0, self.recursion_depth - 1)


# STREAMING EVENT TYPES


@dataclass
class DelegationStartEvent(StreamEvent):
    """
    Event emitted when a delegation to a team member starts.

    This event is yielded during streaming to notify the client that
    a task is being delegated to a specific team member. Useful for
    showing progress and understanding team execution flow.

    Attributes:
        member_id: ID of the member being delegated to
        task: Task description being delegated
        delegation_id: Unique identifier for this delegation

    Example:
        ```python
        async for event in team.stream("Research topic X"):
            if isinstance(event, DelegationStartEvent):
                print(f"Delegating to {event.member_id}: {event.task}")
        ```
    """

    member_id: str
    task: str
    delegation_id: str

    def __init__(self, member_id: str, task: str, delegation_id: str):
        super().__init__(event_type="delegation_start")
        self.member_id = member_id
        self.task = task
        self.delegation_id = delegation_id

    def __str__(self) -> str:
        """Return empty string - events don't render as text."""
        return ""


@dataclass
class DelegationResultEvent(StreamEvent):
    """
    Event emitted when a delegation to a team member completes.

    This event is yielded during streaming to notify the client that
    a delegation has completed, along with its result. Useful for
    tracking member execution and handling errors.

    Attributes:
        member_id: ID of the member that executed the task
        result: Result string from the member (may be truncated)
        success: Whether the delegation succeeded
        delegation_id: Unique identifier for this delegation

    Example:
        ```python
        async for event in team.stream("Research topic X"):
            if isinstance(event, DelegationResultEvent):
                if event.success:
                    print(f"{event.member_id} completed: {event.result[:50]}")
                else:
                    print(f"{event.member_id} failed: {event.result}")
        ```
    """

    member_id: str
    result: str
    success: bool
    delegation_id: str

    def __init__(self, member_id: str, result: str, success: bool, delegation_id: str):
        super().__init__(event_type="delegation_result")
        self.member_id = member_id
        self.result = result
        self.success = success
        self.delegation_id = delegation_id

    def __str__(self) -> str:
        """Return empty string - events don't render as text."""
        return ""


@dataclass
class MemberExecutionEvent(StreamEvent):
    """
    Event emitted when streaming member execution progress.

    This event is yielded when a member agent supports streaming
    and is executing a delegated task. Contains real-time chunks
    from the member's execution.

    Attributes:
        member_id: ID of the member currently executing
        chunk: Text chunk from member's execution
        delegation_id: Unique identifier for this delegation

    Example:
        ```python
        async for event in team.stream("Research topic X"):
            if isinstance(event, MemberExecutionEvent):
                print(event.chunk, end="", flush=True)  # Stream member output
        ```
    """

    member_id: str
    chunk: str
    delegation_id: str

    def __init__(self, member_id: str, chunk: str, delegation_id: str):
        super().__init__(event_type="member_execution")
        self.member_id = member_id
        self.chunk = chunk
        self.delegation_id = delegation_id

    def __str__(self) -> str:
        """Return the chunk content for text rendering."""
        return self.chunk


@dataclass
class SynthesisEvent(StreamEvent):
    """
    Event emitted during synthesis phase (coordinate/collaborate modes).

    This event is yielded when the leader is synthesizing results from
    multiple delegations. Contains real-time chunks from the synthesis
    process.

    Attributes:
        chunk: Text chunk from synthesis process
        stage: Current synthesis stage (e.g., "analyzing", "combining", "finalizing")

    Example:
        ```python
        async for event in team.stream("Research and write article"):
            if isinstance(event, SynthesisEvent):
                print(f"[Synthesis: {event.stage}] {event.chunk}", end="", flush=True)
        ```
    """

    chunk: str
    stage: str

    def __init__(self, chunk: str, stage: str = "synthesizing"):
        super().__init__(event_type="synthesis")
        self.chunk = chunk
        self.stage = stage

    def __str__(self) -> str:
        """Return the chunk content for text rendering."""
        return self.chunk


@dataclass
class TeamStatusEvent(StreamEvent):
    """
    Event emitted for general team execution status updates.

    This event provides status information about team execution progress,
    such as which phase is currently executing, delegation counts, etc.

    Attributes:
        status: Status message describing current phase
        phase: Current execution phase (e.g., "delegating", "executing", "synthesizing")
        metadata: Optional metadata dictionary with additional details

    Example:
        ```python
        async for event in team.stream("Complete project"):
            if isinstance(event, TeamStatusEvent):
                print(f"[{event.phase}] {event.status}")
        ```
    """

    status: str
    phase: str
    metadata: dict[str, Any] | None = None

    def __init__(self, status: str, phase: str, metadata: dict[str, Any] | None = None):
        super().__init__(event_type="team_status")
        self.status = status
        self.phase = phase
        self.metadata = metadata or {}

    def __str__(self) -> str:
        """Return empty string - status events don't render as text."""
        return ""
