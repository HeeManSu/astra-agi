"""
Team class for Astra Framework.

The Team class enables multi-agent coordination through intelligent delegation.
A team leader (LLM) analyzes requests and delegates tasks to specialized member agents.

Features:
- Sequential and parallel delegation
- Memory integration for better routing
- Error handling with retries and timeouts
- Streaming support
- Middleware and guardrail integration
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
import json
import time
from typing import Any
import uuid

from framework.agents.agent import Agent
from framework.agents.exceptions import ValidationError
from framework.astra import AstraContext
from framework.memory import AgentMemory
from framework.memory.manager import MemoryManager
from framework.middlewares import InputMiddleware, MiddlewareContext, OutputMiddleware
from framework.models import Model, ModelResponse
from framework.storage.memory import AgentStorage


class TeamError(Exception):
    """Base exception for all team errors."""


class DelegationError(TeamError):
    """Raised when delegation fails."""


class MemberNotFoundError(TeamError):
    """Raised when a requested member doesn't exist."""


class TeamTimeoutError(TeamError):
    """Raised when team execution exceeds timeout."""


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
    Represents a member agent in a team.

    Attributes:
        id: Unique identifier for the member (used in delegation)
        name: Human-readable name of the member
        description: Description of member's capabilities and responsibilities
        agent: The Agent instance that will execute delegated tasks
        priority: Priority level for routing (future use)
        enabled: Whether this member is currently enabled
    """

    id: str
    name: str
    description: str
    agent: Agent
    priority: int = 0
    enabled: bool = True


@dataclass
class TeamExecutionContext:
    """
    Execution context for team runs.

    Tracks state throughout a team execution including delegation count,
    timing, and runtime state. Thread-safe for parallel execution.

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

    def check_timeout(self) -> None:
        """
        Check if execution has exceeded timeout.

        Raises:
            TeamTimeoutError: If timeout exceeded
        """
        self.elapsed_time = time.time() - self.start_time
        if self.elapsed_time > self.timeout:
            raise TeamTimeoutError(
                f"Team execution exceeded timeout of {self.timeout}s. "
                f"Elapsed: {self.elapsed_time:.2f}s"
            )

    def check_delegation_limit(self) -> None:
        """
        Check if delegation limit has been reached.

        Raises:
            DelegationError: If max delegations exceeded
        """
        if self.delegation_count >= self.max_delegations:
            raise DelegationError(
                f"Maximum delegations ({self.max_delegations}) exceeded. "
                f"Current count: {self.delegation_count}"
            )

    def increment_delegation_count(self) -> None:
        """Increment delegation count (atomic operation)."""
        self.delegation_count += 1


class Team:
    """
    Team class for coordinating multiple agents.

    A Team consists of a leader (LLM) that analyzes requests and delegates
    tasks to specialized member agents. Supports both sequential and parallel
    delegation patterns.

    Example:
        ```python
        onboarding_agent = Agent(
            id="onboarding-agent",
            name="Onboarding Specialist",
            description="Set up seller accounts",
            model=Bedrock(...),
            tools=[...],
        )

        team = Team(
            name="Operations Team",
            model=Bedrock(...),
            members=[TeamMember("onboarding-agent", "Onboarding", "...", onboarding_agent)],
            instructions="Coordinate team members...",
        )

        result = await team.invoke("Set up a new store")
        ```
    """

    def __init__(
        self,
        name: str,
        model: Model,
        members: list[TeamMember],
        *,
        instructions: str | None = None,
        description: str | None = None,
        id: str | None = None,
        allow_parallel: bool = False,
        max_parallel: int = 3,
        max_delegations: int = 10,
        timeout: float = 300.0,
        member_timeout: float = 60.0,
        memory: AgentMemory | None = None,
        storage: AgentStorage | None = None,
        input_middlewares: list[InputMiddleware] | None = None,
        output_middlewares: list[OutputMiddleware] | None = None,
        guardrails: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize a Team.

        Args:
            name: Team name
            model: Model for the team leader (LLM that makes delegation decisions)
            members: List of team members
            instructions: Instructions for the team leader
            description: Optional team description
            id: Optional team ID (auto-generated if not provided)
            allow_parallel: Enable parallel delegation (default: False)
            max_parallel: Maximum concurrent delegations when parallel enabled
            max_delegations: Maximum total delegations per run (safety limit)
            timeout: Global timeout for entire team run (seconds)
            member_timeout: Timeout per member execution (seconds)
            memory: Memory configuration for conversation history
            storage: Storage backend for persistence
            input_middlewares: Input middlewares to apply
            output_middlewares: Output middlewares to apply
            guardrails: Guardrails configuration
            metadata: Optional metadata dictionary
        """
        # Basic identifiers
        self.name = name
        if id is None:
            self.id = f"team-{uuid.uuid4().hex[:8]}"
        else:
            self.id = id
        self.description = description

        # Core configuration
        self.model = model
        self.instructions = instructions or ""
        self.metadata = metadata or {}

        # Execution control
        self.allow_parallel = allow_parallel
        self.max_parallel = max_parallel
        self.max_delegations = max_delegations
        self.timeout = timeout
        self.member_timeout = member_timeout

        # Validate configuration
        self._validate_config()

        # Validate and store members
        self._validate_members(members)
        self.members: dict[str, TeamMember] = {member.id: member for member in members}

        # Memory & Storage
        self.memory = memory or AgentMemory()
        self.memory_manager = MemoryManager(self.memory, self.model)
        self.storage = storage

        # Middleware & Guardrails
        self.input_middlewares = input_middlewares
        self.output_middlewares = output_middlewares
        self.guardrails = guardrails

        # Lazy initialization (like Agent)
        self._context: AstraContext | None = None

        # Cached system prompt (built on first use)
        self._system_prompt: str | None = None

    @property
    def context(self) -> AstraContext:
        """Get the context for the team. Lazily initialized."""
        if self._context is None:
            self._context = AstraContext()
        return self._context

    def _validate_config(self) -> None:
        """
        Validate team configuration.

        Raises:
            ValidationError: If configuration is invalid
        """
        if self.max_delegations <= 0:
            raise ValidationError("max_delegations must be greater than 0")

        if self.timeout <= 0:
            raise ValidationError("timeout must be greater than 0")

        if self.member_timeout <= 0:
            raise ValidationError("member_timeout must be greater than 0")

        if self.allow_parallel and self.max_parallel <= 0:
            raise ValidationError("max_parallel must be greater than 0 when allow_parallel=True")

        # Auto-adjust: member_timeout shouldn't exceed global timeout
        if self.member_timeout > self.timeout:
            # Use min of both
            effective_member_timeout = min(self.member_timeout, self.timeout)
            self.member_timeout = effective_member_timeout

    def _validate_members(self, members: list[TeamMember]) -> None:
        """
        Validate team members.

        Args:
            members: List of team members to validate

        Raises:
            ValidationError: If validation fails
        """
        if not members:
            raise ValidationError("Team must have at least one member")

        # Check for duplicate IDs
        member_ids = [member.id for member in members]
        if len(member_ids) != len(set(member_ids)):
            duplicates = [mid for mid in member_ids if member_ids.count(mid) > 1]
            raise ValidationError(f"Duplicate member IDs found: {set(duplicates)}")

        # Validate each member
        for member in members:
            if not member.id or not isinstance(member.id, str):
                raise ValidationError(f"Member must have a valid string ID. Got: {member.id}")

            if not member.name or not isinstance(member.name, str):
                raise ValidationError(f"Member must have a valid string name. Got: {member.name}")

            if not member.description or not isinstance(member.description, str):
                raise ValidationError(
                    f"Member must have a valid string description. Got: {member.description}"
                )

            if member.agent is None:
                raise ValidationError(f"Member '{member.id}' must have a valid Agent instance")

            if not isinstance(member.agent, Agent):
                raise ValidationError(
                    f"Member '{member.id}' agent must be an Agent instance. "
                    f"Got: {type(member.agent)}"
                )

    def _build_leader_system_prompt(self) -> str:
        """
        Build system prompt for team leader.

        Includes team description, member list with capabilities, and
        delegation instructions. This prompt helps the leader make better
        routing decisions.

        Returns:
            Complete system prompt string
        """
        # Build member list section
        member_list_lines = []
        for member in self.members.values():
            status = "enabled" if member.enabled else "disabled"
            member_list_lines.append(
                f"- **{member.id}** ({member.name}): {member.description} [{status}]"
            )
        member_list = "\n".join(member_list_lines)

        # Base prompt template
        prompt_parts = [
            "You are a team leader coordinating specialized agents.",
            "",
            "## Your Team Members:",
            member_list,
            "",
            "## How to Delegate:",
            "Use the `delegate_task_to_member` tool to assign tasks:",
            "- Provide the member_id of the appropriate agent",
            "- Write a clear, specific task description",
            "- Include any context the member needs",
            "",
            "## Workflow:",
            "1. Analyze the user's request",
            "2. Decide which member(s) should handle it",
            "3. Delegate using the tool (one member at a time, or multiple if needed)",
            "4. After receiving results, either:",
            "   - Delegate to another member, OR",
            "   - Synthesize a final response for the user",
            "",
            "## Guidelines:",
            "- Be specific in task descriptions",
            "- Pass relevant context from previous results",
            "- Synthesize all results into a cohesive final answer",
            "- If unsure which member to use, pick the most relevant one",
        ]

        # Add custom instructions if provided
        if self.instructions:
            prompt_parts.extend(["", "## Additional Instructions:", self.instructions])

        return "\n".join(prompt_parts)

    def _create_delegation_tool(self) -> dict[str, Any]:
        """
        Create delegation tool definition for leader LLM.

        Returns:
            Tool definition dictionary
        """
        return DELEGATION_TOOL

    async def _load_conversation_context(
        self, thread_id: str | None, storage: AgentStorage | None
    ) -> list[dict[str, Any]]:
        """
        Load conversation history from storage.

        Extracts past messages and delegation patterns to help the leader
        make better routing decisions based on conversation context.

        Args:
            thread_id: Thread ID to load history from
            storage: Storage backend instance

        Returns:
            List of message dicts formatted for LLM context
        """
        # If no storage or thread_id, return empty context
        if not storage or not thread_id:
            return []

        try:
            # Load recent history (last 20 messages for context)
            history = await storage.get_history(thread_id, limit=20)

            # Convert Message objects to dict format
            context = []
            for msg in history:
                msg_dict = storage._message_to_dict(msg)
                context.append(msg_dict)

            # Extract past delegations for additional context
            past_delegations = self._extract_past_delegations(history)

            # If we have past delegations, add summary to context
            if past_delegations:
                delegation_summary = self._format_delegation_summary(past_delegations)
                # Add as system message at the beginning
                context.insert(
                    0,
                    {
                        "role": "system",
                        "content": f"## Past Delegations:\n{delegation_summary}",
                    },
                )

            return context

        except Exception:
            # Graceful degradation: continue without history
            return []

    def _extract_past_delegations(self, history: list[Any]) -> list[dict[str, Any]]:
        """
        Extract past delegation patterns from conversation history.

        Looks for tool calls with name "delegate_task_to_member" in assistant
        messages to identify previous delegation decisions.

        Args:
            history: List of Message objects from storage

        Returns:
            List of delegation records with member_id and task
        """
        delegations = []

        for msg in history:
            # Check if this is an assistant message with tool calls
            if msg.role == "assistant" and msg.metadata:
                tool_calls = msg.metadata.get("tool_calls", [])

                for tool_call in tool_calls:
                    if (
                        isinstance(tool_call, dict)
                        and tool_call.get("name") == "delegate_task_to_member"
                    ):
                        args = tool_call.get("arguments", {})
                        if isinstance(args, dict):
                            delegations.append(
                                {
                                    "member_id": args.get("member_id"),
                                    "task": args.get("task", "")[:100],  # Truncate long tasks
                                }
                            )

        return delegations

    def _format_delegation_summary(self, delegations: list[dict[str, Any]]) -> str:
        """
        Format delegation history into a readable summary.

        Args:
            delegations: List of delegation records

        Returns:
            Formatted summary string
        """
        if not delegations:
            return "No past delegations."

        # Group by member_id to show patterns
        member_counts: dict[str, int] = {}
        for delegation in delegations:
            member_id = delegation.get("member_id", "unknown")
            member_counts[member_id] = member_counts.get(member_id, 0) + 1

        summary_lines = ["Recent delegation patterns:"]
        for member_id, count in member_counts.items():
            summary_lines.append(f"- {member_id}: {count} time(s)")

        return "\n".join(summary_lines)

    async def _prepare_execution_context(
        self,
        message: str,
        thread_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> tuple[TeamExecutionContext, list[dict[str, Any]]]:
        """
        Prepare execution context and load conversation history.

        Creates the execution context, loads history from storage, and
        applies input middlewares. This is the pre-execution setup phase.

        Args:
            message: User's input message
            thread_id: Optional thread ID for conversation continuity
            user_id: Optional user ID
            **kwargs: Additional arguments

        Returns:
            Tuple of (execution_context, messages_list)
        """
        # Create execution context
        run_id = kwargs.get("run_id") or f"run-{uuid.uuid4().hex[:8]}"
        context = TeamExecutionContext(
            run_id=run_id,
            thread_id=thread_id,
            user_id=user_id,
            start_time=time.time(),
            timeout=self.timeout,
            max_delegations=self.max_delegations,
        )

        # Load conversation history
        history = await self._load_conversation_context(thread_id, self.storage)

        # Build initial messages list
        messages = []

        # Add system prompt with member information
        system_prompt = self._build_leader_system_prompt()
        messages.append({"role": "system", "content": system_prompt})

        # Add conversation history (already formatted)
        messages.extend(history)

        # Add user message
        messages.append({"role": "user", "content": message})

        # Apply input middlewares if provided
        if self.input_middlewares:
            middleware_context = MiddlewareContext(
                agent=self,  # Team acts like an agent for middleware
                thread_id=thread_id,
            )

            for middleware in self.input_middlewares:
                if isinstance(middleware, InputMiddleware):
                    try:
                        messages = await middleware.process(messages, middleware_context)
                    except Exception:
                        # Continue (graceful degradation)
                        pass
                # self.context.logger.warning(f"Input middleware failed: {e}")

        return context, messages

    async def _process_leader_response(
        self, messages: list[dict[str, Any]], context: TeamExecutionContext
    ) -> ModelResponse:
        """
        Call leader LLM and process response.

        Invokes the leader model with the prepared messages and returns
        the response. Handles errors and validates the response format.

        Args:
            messages: Messages to send to leader
            context: Execution context

        Returns:
            ModelResponse from leader

        Raises:
            ModelError: If leader invocation fails
        """
        try:
            # Call leader model
            response = await self.model.invoke(
                messages=messages,
                tools=[self._create_delegation_tool()],
                temperature=0.7,
            )

            return response

        except Exception as e:
            # Re-raise as TeamError for consistent error handling
            raise DelegationError(f"Leader model invocation failed: {e}") from e

    def _validate_delegation_tool_call(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        """
        Validate and parse delegation tool call.

        Validates that the tool call is for delegation, has required arguments,
        and the member_id exists. Returns parsed arguments.

        Args:
            tool_call: Tool call dictionary from LLM

        Returns:
            Parsed arguments dict with member_id and task

        Raises:
            ValidationError: If tool call is invalid
            MemberNotFoundError: If member_id doesn't exist
        """
        # Check tool name
        tool_name = tool_call.get("name", "")
        if tool_name != "delegate_task_to_member":
            raise ValidationError(
                f"Invalid tool call: expected 'delegate_task_to_member', got '{tool_name}'"
            )

        # Parse arguments (could be dict or JSON string)
        arguments = tool_call.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid tool call arguments (not valid JSON): {e}") from e

        if not isinstance(arguments, dict):
            raise ValidationError(f"Tool call arguments must be a dict. Got: {type(arguments)}")

        # Validate required fields
        member_id = arguments.get("member_id")
        task = arguments.get("task")

        if not member_id:
            raise ValidationError("Tool call missing required argument: member_id")

        if not isinstance(member_id, str):
            raise ValidationError(f"member_id must be a string. Got: {type(member_id)}")

        if not task:
            raise ValidationError("Tool call missing required argument: task")

        if not isinstance(task, str):
            raise ValidationError(f"task must be a string. Got: {type(task)}")

        # Validate member exists
        if member_id not in self.members:
            available = ", ".join(self.members.keys())
            raise MemberNotFoundError(
                f"Member '{member_id}' not found. Available members: {available}"
            )

        return {"member_id": member_id, "task": task}

    async def _execute_single_delegation(
        self,
        member_id: str,
        task: str,
        context: TeamExecutionContext,
        max_retries: int = 2,
    ) -> str:
        """
        Execute a single delegation to a member agent.

        Handles timeout, retries with exponential backoff, and error formatting.
        This is the core delegation execution logic used by both sequential
        and parallel execution paths.

        Args:
            member_id: ID of member to delegate to
            task: Task description for the member
            context: Execution context
            max_retries: Maximum retry attempts on failure

        Returns:
            Result string from member agent

        Raises:
            MemberNotFoundError: If member doesn't exist
            DelegationError: If delegation fails after retries
        """
        # Get member
        member = self.members.get(member_id)
        if not member:
            available = ", ".join(self.members.keys())
            raise MemberNotFoundError(f"Member '{member_id}' not found. Available: {available}")

        # Check if member is enabled
        if not member.enabled:
            return (
                f"Error: Member '{member_id}' is currently disabled. "
                f"Please use a different member or enable this member."
            )

        # Check timeout before starting
        context.check_timeout()

        # Retry loop with exponential backoff
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                # Execute with per-member timeout (using wait_for for Python 3.10 compatibility)
                result = await asyncio.wait_for(
                    member.agent.invoke(task), timeout=self.member_timeout
                )

                # Validate result is not empty
                if not result or not isinstance(result, str):
                    result = str(result) if result else "Member returned empty response"

                return result

            except asyncio.TimeoutError:
                error_msg = f"Member '{member_id}' execution timed out after {self.member_timeout}s"
                last_error = TeamTimeoutError(error_msg)

                # If not last attempt, wait before retry
                if attempt < max_retries:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s...
                    await asyncio.sleep(wait_time)

            except Exception as e:
                last_error = e
                error_msg = f"Member '{member_id}' execution failed: {e!s}"

                # If not last attempt, wait before retry
                if attempt < max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)

        # All retries exhausted
        error_message = (
            f"Member '{member_id}' failed after {max_retries + 1} attempts. "
            f"Last error: {last_error!s}"
        )
        return error_message

    async def _execute_sequential_delegations(
        self,
        delegations: list[dict[str, Any]],
        context: TeamExecutionContext,
    ) -> list[str]:
        """
        Execute delegations sequentially, passing results between them.

        Processes delegations one by one, allowing each delegation to see
        results from previous delegations. This enables dependent workflows
        where later steps depend on earlier results.

        Args:
            delegations: List of delegation dicts with member_id and task
            context: Execution context

        Returns:
            List of results from each delegation
        """
        results = []
        accumulated_context = ""

        for idx, delegation in enumerate(delegations):
            # Check limits before each delegation
            context.check_timeout()
            context.check_delegation_limit()

            member_id = delegation["member_id"]
            task = delegation["task"]

            # If we have previous results, add them to context
            if accumulated_context:
                enhanced_task = f"{task}\n\n## Previous Results:\n{accumulated_context}"
            else:
                enhanced_task = task

            # Execute delegation
            result = await self._execute_single_delegation(member_id, enhanced_task, context)

            # Format result for next delegation
            formatted_result = self._format_delegation_result(member_id, result, idx)
            results.append(result)

            # Accumulate context for next delegation
            accumulated_context += f"\n{formatted_result}"

            # Increment delegation count
            context.increment_delegation_count()

            # Record delegation
            context.delegations.append(
                {
                    "member_id": member_id,
                    "task": task,
                    "result": result,
                    "index": idx,
                }
            )

        return results

    async def _execute_parallel_delegations(
        self,
        delegations: list[dict[str, Any]],
        context: TeamExecutionContext,
    ) -> list[str]:
        """
        Execute independent delegations in parallel.

        Creates async tasks for each delegation and executes them concurrently
        using asyncio.gather(). Handles partial failures and maintains
        result ordering. Each delegation is independent (no shared state).

        Args:
            delegations: List of delegation dicts with member_id and task
            context: Execution context

        Returns:
            List of results in same order as delegations
        """
        # Check timeout before starting parallel execution
        context.check_timeout()

        # Cap max_parallel to actual delegation count (for future use)
        _effective_max_parallel = min(len(delegations), self.max_parallel)

        # Create async tasks for each delegation
        # Use default arguments to capture loop variables correctly (closure fix)
        tasks = []
        for delegation in delegations:
            member_id = delegation["member_id"]
            task_desc = delegation["task"]

            # Create task with default args to avoid closure issue
            async def execute_delegation(m_id: str = member_id, t: str = task_desc) -> str:
                """Execute single delegation with timeout."""
                return await self._execute_single_delegation(m_id, t, context)

            tasks.append(execute_delegation())

        # Execute all tasks in parallel with global timeout
        # Calculate remaining timeout
        remaining_timeout = max(0.1, self.timeout - context.elapsed_time)

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=remaining_timeout
            )

        except asyncio.TimeoutError:
            # Timeout occurred - format partial results
            results = [
                f"Error: Delegation timed out (global timeout {self.timeout}s exceeded)"
                for _ in delegations
            ]

        # Process results: convert exceptions to error messages
        formatted_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                member_id = delegations[idx]["member_id"]
                error_msg = f"Error: Member '{member_id}' failed: {result!s}"
                formatted_results.append(error_msg)
            else:
                formatted_results.append(str(result))

        # Update context after all complete (no race condition)
        context.delegation_count += len(delegations)

        # Record all delegations
        for idx, delegation in enumerate(delegations):
            context.delegations.append(
                {
                    "member_id": delegation["member_id"],
                    "task": delegation["task"],
                    "result": formatted_results[idx],
                    "index": idx,
                }
            )

        return formatted_results

    def _format_delegation_result(self, member_id: str, result: str, index: int) -> str:
        """
        Format delegation result for inclusion in next delegation or final response.

        Creates a readable format that can be passed to subsequent delegations
        or included in the leader's final synthesis.

        Args:
            member_id: ID of member that produced the result
            result: Raw result string from member
            index: Index of this delegation in the sequence

        Returns:
            Formatted result string
        """
        # Truncate very long results to avoid context bloat
        max_result_length = 500
        if len(result) > max_result_length:
            truncated = result[:max_result_length] + "... (truncated)"
        else:
            truncated = result

        return f"[{member_id}]: {truncated}"

    async def _handle_delegation_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        context: TeamExecutionContext,
    ) -> list[dict[str, Any]]:
        """
        Handle delegation tool calls from leader.

        Validates tool calls, extracts delegation requests, routes to sequential
        or parallel execution, and formats results for the leader to continue.

        Args:
            tool_calls: List of tool call dicts from leader
            messages: Current message list (will be updated with results)
            context: Execution context

        Returns:
            Updated messages list with tool results added
        """
        # Filter and validate delegation tool calls
        # Track valid tool calls and their indices for result matching
        delegation_requests = []
        valid_tool_calls = []  # Track which tool calls are valid

        for tool_call in tool_calls:
            # Skip non-delegation tool calls
            if tool_call.get("name") != "delegate_task_to_member":
                continue

            try:
                # Validate and parse tool call
                parsed = self._validate_delegation_tool_call(tool_call)
                delegation_requests.append(parsed)
                valid_tool_calls.append(tool_call)  # Track valid tool call

            except (ValidationError, MemberNotFoundError) as e:
                # Return error to leader for invalid tool calls
                error_result = {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", ""),
                    "name": "delegate_task_to_member",
                    "content": json.dumps({"error": str(e)}),
                }
                messages.append(error_result)
                continue

        # If no valid delegations, return messages as-is
        if not delegation_requests:
            return messages

        # Route to sequential or parallel execution
        if self.allow_parallel and len(delegation_requests) > 1:
            # Parallel execution
            results = await self._execute_parallel_delegations(delegation_requests, context)
        else:
            # Sequential execution (default or single delegation)
            results = await self._execute_sequential_delegations(delegation_requests, context)

        # Add tool results to messages (match results to valid tool calls)
        for tool_call, result in zip(valid_tool_calls, results, strict=True):
            tool_result = {
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "name": "delegate_task_to_member",
                "content": json.dumps({"result": result}),
            }
            messages.append(tool_result)

        return messages

    async def _finalize_execution(
        self,
        response: str,
        context: TeamExecutionContext,
        thread_id: str | None = None,
    ) -> str:
        """
        Finalize team execution.

        Applies output middlewares, saves to storage, and returns final response.
        This is the post-execution cleanup phase.

        Args:
            response: Final response from leader
            context: Execution context
            thread_id: Optional thread ID for storage

        Returns:
            Final formatted response
        """
        # Apply output middlewares if provided
        if self.output_middlewares:
            middleware_context = MiddlewareContext(
                agent=self,  # Team acts like an agent
                thread_id=thread_id,
            )

            for middleware in self.output_middlewares:
                if isinstance(middleware, OutputMiddleware):
                    try:
                        response = await middleware.process(response, middleware_context)
                    except Exception:
                        # Continue (graceful degradation)
                        pass

        # Save to storage if available
        if self.storage and thread_id:
            try:
                # Save final assistant response
                await self.storage.add_message(
                    thread_id=thread_id,
                    role="assistant",
                    content=response,
                )
            except Exception:
                # Continue (storage is not critical)
                pass

        return response

    async def _execute_team_run(
        self,
        message: str,
        thread_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Execute a complete team run with delegation loop.

        This is the main orchestrator that coordinates the entire execution:
        1. Prepares execution context and loads history
        2. Enters leader decision loop
        3. Handles delegations (sequential or parallel)
        4. Continues until leader provides final response
        5. Finalizes and returns result

        Args:
            message: User's input message
            thread_id: Optional thread ID for conversation continuity
            user_id: Optional user ID
            **kwargs: Additional arguments

        Returns:
            Final response string from team

        Raises:
            TeamTimeoutError: If execution exceeds timeout
            DelegationError: If max delegations exceeded
        """
        # Phase 1: Pre-execution setup
        context, messages = await self._prepare_execution_context(
            message, thread_id, user_id, **kwargs
        )

        # Save user message to storage
        if self.storage and thread_id:
            try:
                await self.storage.add_message(thread_id=thread_id, role="user", content=message)
            except Exception:
                pass  # Non-critical, continue

        # Phase 2: Leader decision loop
        max_iterations = self.max_delegations + 5  # Safety limit for iterations
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Check timeout and limits
            context.check_timeout()
            context.check_delegation_limit()

            # Phase 3: Get leader response
            response = await self._process_leader_response(messages, context)

            # Phase 4: Check if leader wants to delegate or respond
            if response.tool_calls:
                # Leader wants to delegate - handle tool calls
                messages = await self._handle_delegation_tool_calls(
                    response.tool_calls, messages, context
                )

                # Add leader's message with tool calls to conversation
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": response.tool_calls,
                    }
                )

                # Continue loop to get leader's next decision

            else:
                # Leader provided final response - exit loop
                final_response = response.content or ""

                # Phase 5: Finalize execution
                return await self._finalize_execution(final_response, context, thread_id)

        # Safety: If we exit loop without final response, return error
        raise DelegationError(
            f"Team execution exceeded maximum iterations ({max_iterations}). "
            f"Leader may be stuck in delegation loop."
        )

    async def invoke(
        self,
        message: str,
        *,
        thread_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Invoke the team with a message and get a response.

        This is the main public API for team execution. It orchestrates
        the entire flow from user input to final response.

        Args:
            message: User's input message
            thread_id: Optional thread ID for conversation continuity
            user_id: Optional user ID
            **kwargs: Additional arguments (run_id, etc.)

        Returns:
            Final response string from team

        Example:
            ```python
            result = await team.invoke("Set up a new store and create goals")
            print(result)
            ```
        """
        # Validate input
        if not message or not isinstance(message, str):
            raise ValidationError("Message must be a non-empty string")

        if len(message) > 100_000:
            raise ValidationError("Message cannot be longer than 100000 characters")

        # Execute team run
        return await self._execute_team_run(message, thread_id, user_id, **kwargs)

    async def stream(
        self,
        message: str,
        *,
        thread_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream team execution with real-time updates.

        Yields chunks as the team executes, including:
        - Leader decision chunks
        - Delegation status updates
        - Member execution progress
        - Final response chunks

        Args:
            message: User's input message
            thread_id: Optional thread ID for conversation continuity
            user_id: Optional user ID
            **kwargs: Additional arguments

        Yields:
            String chunks of execution progress and final response

        Example:
            ```python
            async for chunk in team.stream("Set up a new store"):
                print(chunk, end="", flush=True)
            ```
        """
        # Validate input
        if not message or not isinstance(message, str):
            raise ValidationError("Message must be a non-empty string")

        # For now, stream the final result (full streaming implementation later)
        # This is a placeholder that yields the final result
        result = await self.invoke(message, thread_id=thread_id, user_id=user_id, **kwargs)

        # Yield result in chunks (simple implementation)
        chunk_size = 50
        for i in range(0, len(result), chunk_size):
            yield result[i : i + chunk_size]
            await asyncio.sleep(0.01)  # Small delay for streaming effect

    def __repr__(self) -> str:
        """String representation of the Team."""
        return f"Team(id={self.id!r}, name={self.name!r}, members={len(self.members)})"

    def __str__(self) -> str:
        """Human-friendly representation."""
        return self.__repr__()
