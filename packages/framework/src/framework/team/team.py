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
- Multiple execution modes: route, coordinate, collaborate, hierarchical
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import json
import time
from typing import TYPE_CHECKING, Any
import uuid

from framework.agents.agent import Agent
from framework.agents.exceptions import ValidationError
from framework.astra import AstraContext
from framework.memory import AgentMemory
from framework.memory.manager import MemoryManager
from framework.middlewares import InputMiddleware, MiddlewareContext, OutputMiddleware
from framework.models import Model, ModelResponse
from framework.storage.memory import AgentStorage
from framework.team.execution import (
    execute_collaborate_mode,
    execute_parallel_delegations,
    execute_sequential_delegations,
    execute_single_delegation,
    load_conversation_context,
    synthesize_collaborate_results,
)
from framework.team.types import (
    DELEGATION_TOOL,
    DelegationError,
    DelegationResultEvent,
    DelegationStartEvent,
    MemberExecutionEvent,
    MemberNotFoundError,
    SynthesisEvent,
    TeamExecutionContext,
    TeamMember,
    TeamStatusEvent,
    TeamTimeoutError,
)


if TYPE_CHECKING:
    # Import Team here to avoid circular dependency
    # Reason: TeamMember uses Team type hint, but Team is defined later in this file
    from framework.team.team import Team


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
        execution_mode: str = "coordinate",
        instructions: str | None = None,
        description: str | None = None,
        id: str | None = None,
        allow_parallel: bool = False,
        max_parallel: int = 3,
        max_delegations: int = 10,
        timeout: float = 300.0,
        member_timeout: float = 60.0,
        memory: AgentMemory | None = None,
        storage: Any | None = None,
        input_middlewares: list[InputMiddleware] | None = None,
        output_middlewares: list[OutputMiddleware] | None = None,
        guardrails: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        max_recursion_depth: int = 3,
    ):
        """
        Initialize a Team.

        Args:
            name: Team name
            model: Model for the team leader (LLM that makes delegation decisions)
            members: List of team members (can be Agents or Teams for hierarchical mode)
            execution_mode: Execution mode for the team. Must be one of:
                - "route": Leader selects single best member, returns response directly
                - "coordinate": Leader decomposes task, delegates to multiple members, synthesizes (default)
                - "collaborate": All members work on same task simultaneously, leader combines responses
                - "hierarchical": Supports nested teams with multi-level delegation
            instructions: Instructions for the team leader
            description: Optional team description
            id: Optional team ID (auto-generated if not provided)
            allow_parallel: Enable parallel delegation (only used in coordinate mode)
            max_parallel: Maximum concurrent delegations when parallel enabled
            max_delegations: Maximum total delegations per run (safety limit)
            timeout: Global timeout for entire team run (seconds)
            member_timeout: Timeout per member execution (seconds)
            memory: Memory configuration for conversation history
            storage: Storage backend for persistence (StorageBackend instance,
                will be wrapped in AgentStorage internally)
            input_middlewares: Input middlewares to apply
            output_middlewares: Output middlewares to apply
            guardrails: Guardrails configuration
            metadata: Optional metadata dictionary
            max_recursion_depth: Maximum recursion depth for hierarchical mode (default: 3)

        Example:
            ```python
            # Route mode - simple routing
            team = Team(
                name="Support Team",
                model=model,
                members=[agent1, agent2],
                execution_mode="route",
            )

            # Coordinate mode - decompose and synthesize (default)
            team = Team(
                name="Research Team",
                model=model,
                members=[researcher, writer, editor],
                execution_mode="coordinate",
                allow_parallel=True,
            )

            # Collaborate mode - all members work together
            team = Team(
                name="Brainstorming Team",
                model=model,
                members=[member1, member2, member3],
                execution_mode="collaborate",
            )

            # Hierarchical mode - nested teams
            sub_team = Team(...)
            team = Team(
                name="Management Team",
                model=model,
                members=[sub_team, agent1],
                execution_mode="hierarchical",
                max_recursion_depth=3,
            )
            ```
        """
        # Basic identifiers
        self.name = name
        if id is None:
            # Generate unique ID if not provided
            # Reason: Ensures each team has a unique identifier for tracking
            self.id = f"team-{uuid.uuid4().hex[:8]}"
        else:
            self.id = id
        self.description = description

        # Core configuration
        self.model = model
        self.instructions = instructions or ""
        self.metadata = metadata or {}

        # Execution mode configuration
        # Reason: Different execution modes require different delegation strategies
        self.execution_mode = execution_mode
        self.max_recursion_depth = max_recursion_depth

        # Execution control (for coordinate mode)
        # Reason: These parameters control parallel execution in coordinate mode
        self.allow_parallel = allow_parallel
        self.max_parallel = max_parallel
        self.max_delegations = max_delegations
        self.timeout = timeout
        self.member_timeout = member_timeout

        # Validate and store members
        # Reason: Ensure members are valid and unique before storing
        self._validate_members(members)
        # Store members as dict for O(1) lookup by ID
        # Reason: Fast member lookup during delegation
        self.members: dict[str, TeamMember] = {member.id: member for member in members}

        # Validate configuration
        # Reason: Ensure all parameters are valid before proceeding
        self._validate_config()

        # Memory & Storage
        self.memory = memory or AgentMemory()
        # Memory manager is lazily initialized (only created when needed)
        # Reason: Reduces initialization time and memory footprint
        # MemoryManager is lightweight but only needed during execution
        self._memory_manager: MemoryManager | None = None

        # Wrap storage backend in AgentStorage (consistent with Agent)
        # Reason: Team uses same storage pattern as Agent for consistency
        # AgentStorage provides high-level interface over StorageBackend
        self.storage: AgentStorage | None = None
        if storage:
            # Pass max_messages from memory config to storage (for legacy support/defaults)
            self.storage = AgentStorage(
                storage=storage, max_messages=self.memory.num_history_responses
            )

        # Middleware & Guardrails
        self.input_middlewares = input_middlewares
        self.output_middlewares = output_middlewares
        self.guardrails = guardrails

        # Lazy initialization (like Agent)
        # Reason: Context is only created when needed, saving resources
        self._context: AstraContext | None = None

        # Cached system prompt (built on first use)
        # Reason: System prompt is expensive to build, so we cache it
        self._system_prompt: str | None = None

    # PROPERTIES

    @property
    def context(self) -> AstraContext:
        """
        Get the context for the team. Lazily initialized.

        Returns:
            AstraContext instance for this team

        Example:
            ```python
            ctx = team.context  # Lazily creates context if not exists
            ```
        """
        if self._context is None:
            self._context = AstraContext()
        return self._context

    @property
    def memory_manager(self) -> MemoryManager:
        """
        Get the memory manager for the team. Lazily initialized.

        MemoryManager is only created when needed (during execution when loading
        conversation context). This reduces initialization time and memory footprint.

        Returns:
            MemoryManager instance for this team

        Example:
            ```python
            manager = team.memory_manager  # Lazily creates manager if not exists
            ```
        """
        if self._memory_manager is None:
            self._memory_manager = MemoryManager(self.memory, self.model)
        return self._memory_manager

    # VALIDATION METHODS

    def _validate_execution_mode(self) -> None:
        """
        Validate execution mode parameter and mode-specific requirements.

        This method ensures:
        1. Execution mode is one of the valid values
        2. Mode-specific requirements are met (e.g., minimum members)

        Raises:
            ValidationError: If execution mode is invalid or requirements not met

        Example:
            ```python
            # This will raise ValidationError
            team = Team(
                name="Team",
                model=model,
                members=[],  # Empty members
                execution_mode="collaborate",  # Requires at least 2 members
            )
            ```
        """
        # Define valid execution modes
        # Reason: Centralized list of valid modes makes it easy to add new modes
        valid_modes = {"route", "coordinate", "collaborate", "hierarchical"}

        # Check if execution mode is valid
        if self.execution_mode not in valid_modes:
            raise ValidationError(
                f"Invalid execution_mode '{self.execution_mode}'. Must be one of: {valid_modes}"
            )

        # Mode-specific validations
        # Reason: Each mode has different requirements that must be validated

        # Route mode: Requires at least 1 member (to route to)
        if self.execution_mode == "route":
            if len(self.members) < 1:
                raise ValidationError(
                    "Route mode requires at least 1 member to route to. "
                    f"Found {len(self.members)} members."
                )

        # Collaborate mode: Requires at least 2 members (to collaborate)
        if self.execution_mode == "collaborate":
            if len(self.members) < 2:
                raise ValidationError(
                    "Collaborate mode requires at least 2 members to collaborate. "
                    f"Found {len(self.members)} members."
                )

        # Hierarchical mode: Validate recursion depth
        if self.execution_mode == "hierarchical":
            if self.max_recursion_depth < 1:
                raise ValidationError(
                    f"max_recursion_depth must be >= 1 for hierarchical mode. "
                    f"Got: {self.max_recursion_depth}"
                )

    def _validate_config(self) -> None:
        """
        Validate team configuration.

        This method validates all configuration parameters including:
        - Execution mode and mode-specific requirements
        - Timeout settings
        - Delegation limits
        - Parallel execution settings

        Raises:
            ValidationError: If configuration is invalid

        Example:
            ```python
            # This will raise ValidationError
            team = Team(
                name="Team",
                model=model,
                members=[member1],
                max_delegations=0,  # Invalid: must be > 0
            )
            ```
        """
        # Validate execution mode first
        # Reason: Other validations may depend on execution mode
        self._validate_execution_mode()

        # Validate delegation limits
        # Reason: Prevents infinite loops and ensures reasonable limits
        if self.max_delegations <= 0:
            raise ValidationError("max_delegations must be greater than 0")

        # Validate timeout settings
        # Reason: Ensures timeouts are positive and reasonable
        if self.timeout <= 0:
            raise ValidationError("timeout must be greater than 0")

        if self.member_timeout <= 0:
            raise ValidationError("member_timeout must be greater than 0")

        # Validate parallel execution settings
        # Reason: Ensures parallel execution is properly configured
        if self.allow_parallel and self.max_parallel <= 0:
            raise ValidationError("max_parallel must be greater than 0 when allow_parallel=True")

        # Auto-adjust: member_timeout shouldn't exceed global timeout
        # Reason: Prevents confusion where member timeout is longer than team timeout
        if self.member_timeout > self.timeout:
            # Use min of both to ensure consistency
            effective_member_timeout = min(self.member_timeout, self.timeout)
            self.member_timeout = effective_member_timeout

    def _validate_members(self, members: list[TeamMember]) -> None:
        """
        Validate team members.

        This method validates:
        1. At least one member exists
        2. No duplicate member IDs
        3. Each member has valid ID, name, description
        4. Each member has valid Agent or Team instance (for hierarchical mode)

        Args:
            members: List of team members to validate

        Raises:
            ValidationError: If validation fails

        Example:
            ```python
            # This will raise ValidationError
            team = Team(
                name="Team",
                model=model,
                members=[
                    TeamMember("id1", "Name1", "Desc1", agent1),
                    TeamMember("id1", "Name2", "Desc2", agent2),  # Duplicate ID
                ],
            )
            ```
        """
        # Check that we have at least one member
        # Reason: A team without members cannot function
        if not members:
            raise ValidationError("Team must have at least one member")

        # Check for duplicate IDs
        # Reason: Member IDs must be unique for proper delegation
        member_ids = [member.id for member in members]
        if len(member_ids) != len(set(member_ids)):
            duplicates = [mid for mid in member_ids if member_ids.count(mid) > 1]
            raise ValidationError(f"Duplicate member IDs found: {set(duplicates)}")

        # Validate each member
        # Reason: Ensure all members are properly configured
        for member in members:
            # Validate member ID
            if not member.id or not isinstance(member.id, str):
                raise ValidationError(f"Member must have a valid string ID. Got: {member.id}")

            # Validate member name
            if not member.name or not isinstance(member.name, str):
                raise ValidationError(f"Member must have a valid string name. Got: {member.name}")

            # Validate member description
            if not member.description or not isinstance(member.description, str):
                raise ValidationError(
                    f"Member must have a valid string description. Got: {member.description}"
                )

            # Validate member agent/team instance
            # Reason: Member must have a valid Agent or Team instance to execute tasks
            if member.agent is None:
                raise ValidationError(
                    f"Member '{member.id}' must have a valid Agent or Team instance"
                )

            # Check if it's Agent or Team (for hierarchical mode support)
            # Reason: In hierarchical mode, members can be nested Teams
            # Import Team here to avoid circular dependency at module level
            from framework.team.team import Team as TeamClass

            if not isinstance(member.agent, (Agent, TeamClass)):
                raise ValidationError(
                    f"Member '{member.id}' agent must be an Agent or Team instance. "
                    f"Got: {type(member.agent)}"
                )

    # PROMPT BUILDING METHODS

    def _build_leader_system_prompt(self) -> str:
        """
        Build system prompt for team leader with mode-specific instructions.

        This method constructs a comprehensive system prompt that includes:
        1. Base member information (all modes)
        2. Mode-specific instructions (route, coordinate, collaborate, hierarchical)
        3. Custom instructions if provided

        The prompt is tailored to the execution mode to guide the leader's behavior:
        - Route mode: Select single best member
        - Coordinate mode: Decompose task, delegate to multiple members, synthesize
        - Collaborate mode: Delegate same task to all members, combine responses
        - Hierarchical mode: Support nested teams with recursion

        Returns:
            Complete system prompt string with mode-specific instructions

        Example:
            ```python
            # Route mode prompt will instruct leader to select single member
            team = Team(..., execution_mode="route")
            prompt = team._build_leader_system_prompt()
            # Prompt includes: "You MUST delegate to EXACTLY ONE member"
            ```
        """
        # Build member list section
        # Reason: Leader needs to know available members and their capabilities
        member_list_lines = []
        for member in self.members.values():
            # Show member status (enabled/disabled)
            # Reason: Leader should know which members are available
            status = "enabled" if member.enabled else "disabled"
            member_list_lines.append(
                f"- **{member.id}** ({member.name}): {member.description} [{status}]"
            )
        member_list = "\n".join(member_list_lines)

        # Base prompt template (common to all modes)
        # Reason: All modes need basic information about members and delegation
        prompt_parts = [
            "You are a team leader coordinating specialized agents.",
            "",
            "## Your Team Members:",
            member_list,
            "",
        ]

        # Mode-specific instructions
        # Reason: Each execution mode requires different behavior from the leader
        if self.execution_mode == "route":
            # Route mode: Simple routing to single best member
            # Reason: Leader should select one member and return their response directly
            mode_instructions = """
## Execution Mode: ROUTE

You are a router. Your job is to select the SINGLE best team member for the user's request.

IMPORTANT RULES:
- You MUST delegate to EXACTLY ONE member
- Do NOT delegate to multiple members
- Do NOT synthesize responses
- Simply select the best member and delegate
- The member's response will be returned directly to the user

Workflow:
1. Analyze the user's request
2. Identify which member is best suited for this task
3. Delegate to that ONE member using delegate_task_to_member tool
4. Return the member's response as-is (no synthesis needed)

Example:
User: "Help me with customer support"
→ Analyze: This is a support request
→ Select: "support-agent" (best match)
→ Delegate: delegate_task_to_member(member_id="support-agent", task="Help with customer support")
→ Return: Member's response directly to user
"""

        elif self.execution_mode == "coordinate":
            # Coordinate mode: Decompose task, delegate to multiple members, synthesize
            # Reason: Leader should break down complex tasks and coordinate multiple members
            parallel_note = ""
            if self.allow_parallel:
                parallel_note = f"\n- Parallel execution is enabled (up to {self.max_parallel} concurrent delegations)"

            mode_instructions = f"""
## Execution Mode: COORDINATE

You are coordinating a team that works together on complex tasks. Your job is to:
1. Decompose the user's request into subtasks
2. Delegate each subtask to the appropriate member(s)
3. Synthesize all results into a unified response

IMPORTANT RULES:
- Break down complex tasks into smaller, manageable subtasks
- Delegate each subtask to the most appropriate member
- You can delegate to multiple members (sequentially or in parallel){parallel_note}
- After receiving all results, synthesize them into a cohesive answer
- Pass relevant context from previous results to subsequent delegations

Workflow:
1. Analyze the user's request
2. Identify the subtasks needed to complete it
3. Delegate each subtask to appropriate member(s) using delegate_task_to_member tool
4. Wait for all results
5. Synthesize all results into a comprehensive final answer
6. Return the synthesized response

Example:
User: "Research and write an article about AI"
→ Decompose:
  - Subtask 1: Research AI trends (delegate to researcher)
  - Subtask 2: Write article based on research (delegate to writer)
→ Delegate:
  - delegate_task_to_member(member_id="researcher", task="Research latest AI trends")
  - delegate_task_to_member(member_id="writer", task="Write article based on research results")
→ Synthesize: Combine research and article into final response
"""

        elif self.execution_mode == "collaborate":
            # Collaborate mode: All members work on same task simultaneously
            # Reason: Leader should have all members contribute perspectives on the same task
            enabled_members = [m for m in self.members.values() if m.enabled]
            member_ids = [m.id for m in enabled_members]

            mode_instructions = f"""
## Execution Mode: COLLABORATE

You are coordinating a collaborative session. Your job is to have ALL team members work on the SAME task simultaneously, then synthesize their responses.

IMPORTANT RULES:
- You MUST delegate the SAME task to ALL enabled members
- Current enabled members: {", ".join(member_ids)}
- All members will work in parallel on the same task
- After all members complete, you will synthesize their responses
- This mode is ideal for brainstorming, multi-perspective analysis, or consensus building

Workflow:
1. Receive user's request
2. Delegate the SAME task to ALL enabled members using multiple delegate_task_to_member tool calls
3. Wait for all members to complete
4. Synthesize all responses into a unified answer that integrates all perspectives
5. Return the synthesized response

Example:
User: "Analyze the pros and cons of remote work"
→ Delegate to ALL members:
  - delegate_task_to_member(member_id="member1", task="Analyze the pros and cons of remote work")
  - delegate_task_to_member(member_id="member2", task="Analyze the pros and cons of remote work")
  - delegate_task_to_member(member_id="member3", task="Analyze the pros and cons of remote work")
→ Wait for all responses
→ Synthesize: Combine all three perspectives into unified analysis
"""

        elif self.execution_mode == "hierarchical":
            # Hierarchical mode: Support nested teams with multi-level delegation
            # Reason: Leader should understand which members are teams vs agents
            team_members = [m for m in self.members.values() if m.is_team()]
            agent_members = [m for m in self.members.values() if m.is_agent()]

            team_list = ""
            if team_members:
                team_list = "\n".join(f"- {m.id} ({m.name}): {m.description}" for m in team_members)
            else:
                team_list = "- None"

            agent_list = ""
            if agent_members:
                agent_list = "\n".join(
                    f"- {m.id} ({m.name}): {m.description}" for m in agent_members
                )
            else:
                agent_list = "- None"

            mode_instructions = f"""
## Execution Mode: HIERARCHICAL

You are coordinating a hierarchical team structure. Some members are sub-teams that can further delegate to their own members.

Team Members (can delegate to their own members - nested teams):
{team_list}

Agent Members (execute tasks directly):
{agent_list}

IMPORTANT RULES:
- You can delegate to both team members and agent members
- Team members will further delegate to their own members (recursive delegation)
- Maximum recursion depth: {self.max_recursion_depth}
- Delegate based on task complexity and member capabilities
- If a task requires multiple sub-tasks, consider delegating to a team member
- If a task is straightforward, delegate to an agent member

Workflow:
1. Analyze the user's request
2. Decide which member(s) should handle it
   - For complex tasks: Consider delegating to a team member
   - For simple tasks: Delegate to an agent member
3. Delegate using delegate_task_to_member tool
4. If delegating to a team member, it will handle further delegation internally
5. Synthesize results from all delegations
6. Return the synthesized response

Example:
User: "Complete a research project"
→ Analyze: Complex task requiring multiple steps
→ Delegate to team: delegate_task_to_member(member_id="research-team", task="Complete research project")
→ Research team internally delegates to its members (researcher, writer, editor)
→ Results bubble up through hierarchy
→ Synthesize final response
"""

        else:
            # Fallback for unknown modes (should not happen due to validation)
            # Reason: Safety fallback in case validation misses something
            mode_instructions = f"""
## Execution Mode: {self.execution_mode.upper()}

Unknown execution mode. Please use one of: route, coordinate, collaborate, hierarchical.
"""

        # Add mode-specific instructions
        prompt_parts.append(mode_instructions)

        # Add common delegation instructions (for modes that use delegation)
        # Reason: All modes need to know how to use the delegation tool
        if self.execution_mode != "collaborate":
            # Collaborate mode handles delegation differently (automatic to all)
            prompt_parts.extend(
                [
                    "",
                    "## How to Delegate:",
                    "Use the `delegate_task_to_member` tool to assign tasks:",
                    "- Provide the member_id of the appropriate agent",
                    "- Write a clear, specific task description",
                    "- Include any context the member needs",
                ]
            )

        # Add custom instructions if provided
        # Reason: Allow users to customize leader behavior
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

    # MEMORY & CONTEXT METHODS

    async def _load_conversation_context(
        self, thread_id: str | None, storage: AgentStorage | None
    ) -> list[dict[str, Any]]:
        """
        Load conversation history from storage.

        Wrapper around execution.load_conversation_context for backward compatibility.

        Args:
            thread_id: Thread ID to load history from
            storage: Storage backend instance

        Returns:
            List of message dicts formatted for LLM context
        """
        return await load_conversation_context(self, thread_id, storage)

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

    # DELEGATION EXECUTION METHODS

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

    # DELEGATION HANDLING METHODS

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
        # Reason: If leader didn't delegate, we can't proceed
        if not delegation_requests:
            return messages

        # MODE-SPECIFIC: Route mode validation
        # Reason: Route mode requires exactly ONE delegation, no more, no less
        if self.execution_mode == "route":
            if len(delegation_requests) > 1:
                # Leader tried to delegate to multiple members - error
                # Reason: Route mode is for simple routing to single best member
                error_msg = (
                    "Route mode requires delegating to exactly ONE member. "
                    f"You attempted to delegate to {len(delegation_requests)} members. "
                    "Please select the single best member and delegate again."
                )
                messages.append(
                    {
                        "role": "system",
                        "content": error_msg,
                    }
                )
                return messages  # Return error, leader will retry

            if len(delegation_requests) == 0:
                # Leader didn't delegate - error
                # Reason: Route mode requires delegation to proceed
                error_msg = (
                    "Route mode requires delegating to exactly ONE member. "
                    "Please use the delegate_task_to_member tool to select a member."
                )
                messages.append(
                    {
                        "role": "system",
                        "content": error_msg,
                    }
                )
                return messages

        # Route to sequential or parallel execution (for coordinate mode)
        # Reason: Coordinate mode supports both sequential and parallel execution
        if self.execution_mode == "coordinate":
            if self.allow_parallel and len(delegation_requests) > 1:
                # Parallel execution
                # Reason: Multiple independent tasks can run simultaneously
                results = await execute_parallel_delegations(self, delegation_requests, context)
            else:
                # Sequential execution (default or single delegation)
                # Reason: Dependent tasks or single delegation must run sequentially
                results = await execute_sequential_delegations(self, delegation_requests, context)
        else:
            # For route mode, we only have one delegation request
            # Reason: Route mode already validated single delegation above
            if len(delegation_requests) == 1:
                # Execute single delegation
                result = await execute_single_delegation(
                    self,
                    delegation_requests[0]["member_id"],
                    delegation_requests[0]["task"],
                    context,
                )
                results = [result]
            else:
                # Fallback: sequential execution
                # Reason: Safety fallback for unexpected cases
                results = await execute_sequential_delegations(self, delegation_requests, context)

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

    # EXECUTION FINALIZATION METHODS

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

    # MAIN EXECUTION METHODS

    async def _execute_team_run(
        self,
        message: str,
        thread_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Execute a complete team run with mode-specific execution flow.

        This is the main orchestrator that coordinates the entire execution.
        The execution flow varies by execution mode:

        - Route mode: Leader selects single member, returns response directly
        - Coordinate mode: Leader decomposes task, delegates, synthesizes (default)
        - Collaborate mode: All members work on same task, leader synthesizes
        - Hierarchical mode: Supports nested teams with recursion

        Args:
            message: User's input message
            thread_id: Optional thread ID for conversation continuity
            user_id: Optional user ID
            **kwargs: Additional arguments (run_id, etc.)

        Returns:
            Final response string from team

        Raises:
            TeamTimeoutError: If execution exceeds timeout
            DelegationError: If max delegations exceeded

        Example:
            ```python
            # Route mode - simple routing
            result = await team._execute_team_run("Help with support", ...)

            # Coordinate mode - decompose and synthesize
            result = await team._execute_team_run("Research and write article", ...)

            # Collaborate mode - all members work together
            result = await team._execute_team_run("Brainstorm ideas", ...)
            ```
        """
        # Phase 1: Pre-execution setup
        # Reason: All modes need context and message preparation
        context, messages = await self._prepare_execution_context(
            message, thread_id, user_id, **kwargs
        )

        # Set recursion depth in context (for hierarchical mode)
        # Reason: Track recursion depth from the start
        context.max_recursion_depth = self.max_recursion_depth

        # Save user message to storage
        # Reason: Persist conversation history for future reference
        if self.storage and thread_id:
            try:
                await self.storage.add_message(thread_id=thread_id, role="user", content=message)
            except Exception:
                pass  # Non-critical, continue

        # MODE-SPECIFIC: Collaborate mode - direct execution
        # Reason: Collaborate mode bypasses leader loop - all members work on same task
        if self.execution_mode == "collaborate":
            # Execute collaborate mode: delegate same task to all members
            # Reason: All members work simultaneously on the same task
            member_results_list = await execute_collaborate_mode(self, message, context)

            # Format results for synthesis
            # Reason: Synthesis needs structured data with member IDs
            member_results = []
            enabled_members = [m for m in self.members.values() if m.enabled]
            for member, result in zip(enabled_members, member_results_list, strict=True):
                member_results.append(
                    {
                        "member_id": member.id,
                        "task": message,  # Same task for all
                        "result": result,
                    }
                )

            # Synthesize all results into unified response
            # Reason: Combine multiple perspectives into cohesive answer
            synthesized = await synthesize_collaborate_results(
                self, message, member_results, context
            )

            # Finalize and return
            return await self._finalize_execution(synthesized, context, thread_id)

        # Phase 2: Leader decision loop (for route, coordinate, hierarchical modes)
        # Reason: These modes use leader to make delegation decisions
        max_iterations = self.max_delegations + 5  # Safety limit for iterations
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Check timeout and limits before each iteration
            # Reason: Prevent infinite loops and timeout violations
            context.check_timeout()
            context.check_delegation_limit()

            # Phase 3: Get leader response
            # Reason: Leader decides whether to delegate or respond
            # LLM call
            response = await self._process_leader_response(messages, context)

            # Phase 4: Check if leader wants to delegate or respond
            if response.tool_calls:
                # Leader wants to delegate - handle tool calls
                # Reason: Leader identified members to delegate to
                messages = await self._handle_delegation_tool_calls(
                    response.tool_calls, messages, context
                )

                # Add leader's message with tool calls to conversation
                # Reason: Maintain conversation history for context
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": response.tool_calls,
                    }
                )

                # MODE-SPECIFIC: Route mode - return result immediately
                # Reason: Route mode returns member response directly, no synthesis
                if self.execution_mode == "route":
                    # Extract result from tool response
                    # Reason: Last message should be tool result with member's response
                    tool_results = [msg for msg in messages if msg.get("role") == "tool"]
                    if tool_results:
                        # Parse result from tool response
                        # Reason: Tool responses contain JSON with result
                        result_content = json.loads(tool_results[-1].get("content", "{}"))
                        member_result = result_content.get("result", "")

                        # Finalize and return (no synthesis)
                        # Reason: Route mode returns member response as-is
                        return await self._finalize_execution(member_result, context, thread_id)

                # Continue loop to get leader's next decision (for coordinate/hierarchical)
                # Reason: These modes may need multiple delegation rounds

            else:
                # Leader provided final response - exit loop
                # Reason: Leader synthesized results and provided final answer
                final_response = response.content or ""

                # Phase 5: Finalize execution
                return await self._finalize_execution(final_response, context, thread_id)

        # Safety: If we exit loop without final response, return error
        # Reason: Prevent infinite loops if leader gets stuck
        raise DelegationError(
            f"Team execution exceeded maximum iterations ({max_iterations}). "
            f"Leader may be stuck in delegation loop."
        )

    # PUBLIC API METHODS

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

    # STREAMING METHODS

    async def _stream_team_run(
        self,
        message: str,
        thread_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[
        str
        | DelegationStartEvent
        | DelegationResultEvent
        | MemberExecutionEvent
        | SynthesisEvent
        | TeamStatusEvent
    ]:
        """
        Stream team execution with real-time updates and events.

        This method provides production-grade streaming that yields:
        - Real-time text chunks from leader model
        - Delegation events (start/result)
        - Member execution progress (if members support streaming)
        - Synthesis progress (for coordinate/collaborate modes)
        - Status updates throughout execution

        The streaming flow varies by execution mode:
        - Route mode: Stream leader decision → delegation event → member result
        - Coordinate mode: Stream leader → delegations → synthesis
        - Collaborate mode: Stream parallel delegations → synthesis
        - Hierarchical mode: Stream nested team execution recursively

        Args:
            message: User's input message
            thread_id: Optional thread ID for conversation continuity
            user_id: Optional user ID
            **kwargs: Additional arguments (run_id, etc.)

        Yields:
            Union of:
            - str: Text chunks from leader or members
            - DelegationStartEvent: When delegation starts
            - DelegationResultEvent: When delegation completes
            - MemberExecutionEvent: Real-time chunks from member execution
            - SynthesisEvent: Synthesis progress chunks
            - TeamStatusEvent: Status updates

        Raises:
            TeamTimeoutError: If execution exceeds timeout
            DelegationError: If max delegations exceeded

        Example:
            ```python
            async for event in team._stream_team_run("Research topic X"):
                if isinstance(event, str):
                    print(event, end="", flush=True)  # Text chunk
                elif isinstance(event, DelegationStartEvent):
                    print(f"\\n[Delegating to {event.member_id}]")
                elif isinstance(event, DelegationResultEvent):
                    print(f"\\n[{event.member_id} completed]")
            ```
        """
        # Phase 1: Pre-execution setup
        # Reason: All modes need context and message preparation
        context, messages = await self._prepare_execution_context(
            message, thread_id, user_id, **kwargs
        )

        # Set recursion depth in context (for hierarchical mode)
        # Reason: Track recursion depth from the start
        context.max_recursion_depth = self.max_recursion_depth

        # Save user message to storage
        # Reason: Persist conversation history for future reference
        if self.storage and thread_id:
            try:
                await self.storage.add_message(thread_id=thread_id, role="user", content=message)
            except Exception:
                pass  # Non-critical, continue

        # Emit initial status event
        # Reason: Inform client that execution has started
        yield TeamStatusEvent(
            status=f"Starting team execution in {self.execution_mode} mode",
            phase="initializing",
            metadata={"execution_mode": self.execution_mode, "member_count": len(self.members)},
        )

        # MODE-SPECIFIC: Collaborate mode - direct execution with streaming
        # Reason: Collaborate mode bypasses leader loop - all members work on same task
        if self.execution_mode == "collaborate":
            # Emit status for collaborate mode
            yield TeamStatusEvent(
                status="Delegating same task to all members",
                phase="delegating",
            )

            # Execute collaborate mode: delegate same task to all members
            # Reason: All members work simultaneously on the same task
            member_results_list = await execute_collaborate_mode(self, message, context)

            # Format results for synthesis
            # Reason: Synthesis needs structured data with member IDs
            member_results = []
            enabled_members = [m for m in self.members.values() if m.enabled]
            for member, result in zip(enabled_members, member_results_list, strict=True):
                member_results.append(
                    {
                        "member_id": member.id,
                        "task": message,  # Same task for all
                        "result": result,
                    }
                )

            # Emit status for synthesis phase
            # Reason: Inform client that synthesis is starting
            yield TeamStatusEvent(
                status="Synthesizing results from all members",
                phase="synthesizing",
                metadata={"member_count": len(member_results)},
            )

            # Synthesize all results into unified response with streaming
            # Reason: Stream synthesis process for real-time feedback
            async for chunk in self._stream_synthesis(message, member_results, context):
                yield chunk

            # Finalize execution (no need to yield final response - already streamed)
            # Reason: Synthesis already yielded the final response
            return

        # Phase 2: Leader decision loop (for route, coordinate, hierarchical modes)
        # Reason: These modes use leader to make delegation decisions
        max_iterations = self.max_delegations + 5  # Safety limit for iterations
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Check timeout and limits before each iteration
            # Reason: Prevent infinite loops and timeout violations
            context.check_timeout()
            context.check_delegation_limit()

            # Emit status for leader decision phase
            # Reason: Inform client that leader is making a decision
            yield TeamStatusEvent(
                status=f"Leader analyzing request (iteration {iteration})",
                phase="analyzing",
                metadata={"iteration": iteration},
            )

            # Phase 3: Stream leader response
            # Reason: Stream leader's decision-making process in real-time
            accumulated_content = ""
            accumulated_tool_calls: list[dict[str, Any]] = []

            try:
                # Stream response from leader model
                # Reason: Get real-time chunks from leader as it thinks
                stream_iter = self.model.stream(
                    messages=messages,
                    tools=[self._create_delegation_tool()],
                    temperature=0.7,
                )

                async for chunk in stream_iter:  # type: ignore[union-attr]
                    # Yield text content immediately for streaming
                    # Reason: Client sees leader's thinking process in real-time
                    if chunk.content:
                        accumulated_content += chunk.content
                        yield chunk.content

                    # Accumulate tool calls (check for non-empty list)
                    # Reason: Need to collect all tool calls before executing
                    if chunk.tool_calls and len(chunk.tool_calls) > 0:
                        # Merge tool calls, avoiding duplicates
                        # Reason: Some models send partial tool calls that need merging
                        for tc in chunk.tool_calls:
                            if tc not in accumulated_tool_calls:
                                accumulated_tool_calls.append(tc)

                    # Track final chunk for usage metadata
                    # Reason: Log usage statistics for observability
                    if chunk.metadata.get("final"):
                        # Usage logging can be added here if needed
                        pass

            except Exception as e:
                # Stream error event
                # Reason: Inform client of streaming failure
                yield TeamStatusEvent(
                    status=f"Leader model streaming failed: {e}",
                    phase="error",
                    metadata={"error": str(e)},
                )
                raise DelegationError(f"Leader model streaming failed: {e}") from e

            # Phase 4: Check if leader wants to delegate or respond
            if accumulated_tool_calls:
                # Leader wants to delegate - handle tool calls with streaming
                # Reason: Stream delegation process for transparency

                # Add leader's message with tool calls to conversation
                # Reason: Maintain conversation history for context
                messages.append(
                    {
                        "role": "assistant",
                        "content": accumulated_content or "",
                        "tool_calls": accumulated_tool_calls,
                    }
                )

                # Stream delegation handling with events
                # Reason: Provide real-time updates on delegation process
                async for event in self._stream_delegation_handling(
                    accumulated_tool_calls, messages, context
                ):
                    yield event

                # Update messages from delegation handling
                # Reason: Get updated messages list with tool results
                # Note: _stream_delegation_handling returns updated messages as last yield
                # We'll handle this in the implementation

                # MODE-SPECIFIC: Route mode - return result immediately
                # Reason: Route mode returns member response directly, no synthesis
                if self.execution_mode == "route":
                    # Extract result from tool response
                    # Reason: Last message should be tool result with member's response
                    tool_results = [msg for msg in messages if msg.get("role") == "tool"]
                    if tool_results:
                        # Parse result from tool response
                        # Reason: Tool responses contain JSON with result
                        result_content = json.loads(tool_results[-1].get("content", "{}"))
                        member_result = result_content.get("result", "")

                        # Finalize and return (no synthesis)
                        # Reason: Route mode returns member response as-is
                        final_response = await self._finalize_execution(
                            member_result, context, thread_id
                        )
                        # Result already streamed via delegation events, just return
                        return

                # Continue loop to get leader's next decision (for coordinate/hierarchical)
                # Reason: These modes may need multiple delegation rounds

            else:
                # Leader provided final response - stream it and exit
                # Reason: Leader synthesized results and provided final answer
                final_response = accumulated_content or ""

                # Emit status for finalization
                # Reason: Inform client that execution is completing
                yield TeamStatusEvent(
                    status="Finalizing response",
                    phase="finalizing",
                )

                # Phase 5: Finalize execution
                final_response = await self._finalize_execution(final_response, context, thread_id)

                # Yield final response if not already streamed
                # Reason: Ensure client receives complete response
                if final_response and final_response != accumulated_content:
                    yield final_response

                return

        # Safety: If we exit loop without final response, emit error
        # Reason: Prevent infinite loops if leader gets stuck
        yield TeamStatusEvent(
            status=f"Team execution exceeded maximum iterations ({max_iterations})",
            phase="error",
            metadata={"max_iterations": max_iterations},
        )
        raise DelegationError(
            f"Team execution exceeded maximum iterations ({max_iterations}). "
            f"Leader may be stuck in delegation loop."
        )

    async def _stream_delegation_handling(
        self,
        tool_calls: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        context: TeamExecutionContext,
    ) -> AsyncIterator[
        DelegationStartEvent
        | DelegationResultEvent
        | MemberExecutionEvent
        | SynthesisEvent
        | TeamStatusEvent
    ]:
        """
        Stream delegation handling with real-time events.

        Validates tool calls, extracts delegation requests, executes delegations
        with streaming support, and yields events throughout the process.

        Args:
            tool_calls: List of tool call dicts from leader
            messages: Current message list (will be updated with results)
            context: Execution context

        Yields:
            Union of:
            - str: Text chunks (if any)
            - DelegationStartEvent: When each delegation starts
            - DelegationResultEvent: When each delegation completes
            - MemberExecutionEvent: Real-time chunks from member execution (if supported)
        """
        # Filter and validate delegation tool calls
        # Reason: Only process valid delegation requests
        delegation_requests = []
        valid_tool_calls = []

        for tool_call in tool_calls:
            # Skip non-delegation tool calls
            if tool_call.get("name") != "delegate_task_to_member":
                continue

            try:
                # Validate and parse tool call
                parsed = self._validate_delegation_tool_call(tool_call)
                delegation_requests.append(parsed)
                valid_tool_calls.append(tool_call)

            except (ValidationError, MemberNotFoundError) as e:
                # Return error to leader for invalid tool calls
                # Reason: Leader needs to know about validation errors
                error_result = {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", ""),
                    "name": "delegate_task_to_member",
                    "content": json.dumps({"error": str(e)}),
                }
                messages.append(error_result)
                continue

        # If no valid delegations, return early
        # Reason: Nothing to delegate
        if not delegation_requests:
            return

        # MODE-SPECIFIC: Route mode validation
        # Reason: Route mode requires exactly ONE delegation
        if self.execution_mode == "route":
            if len(delegation_requests) > 1:
                error_msg = (
                    "Route mode requires delegating to exactly ONE member. "
                    f"You attempted to delegate to {len(delegation_requests)} members."
                )
                messages.append({"role": "system", "content": error_msg})
                return
            if len(delegation_requests) == 0:
                error_msg = (
                    "Route mode requires delegating to exactly ONE member. "
                    "Please use the delegate_task_to_member tool."
                )
                messages.append({"role": "system", "content": error_msg})
                return

        # Execute delegations with streaming support
        # Reason: Stream delegation execution for real-time feedback
        results = []

        if self.execution_mode == "coordinate":
            # Coordinate mode: sequential or parallel execution
            # Reason: Choose execution strategy based on configuration
            if self.allow_parallel and len(delegation_requests) > 1:
                # Parallel execution with streaming
                # Reason: Multiple independent tasks can run simultaneously
                async for event in self._stream_parallel_delegations(delegation_requests, context):
                    yield event
                    # Collect results from DelegationResultEvent
                    if isinstance(event, DelegationResultEvent):
                        results.append(event.result)
            else:
                # Sequential execution with streaming
                # Reason: Dependent tasks or single delegation must run sequentially
                async for event in self._stream_sequential_delegations(
                    delegation_requests, context
                ):
                    yield event
                    # Collect results from DelegationResultEvent
                    if isinstance(event, DelegationResultEvent):
                        results.append(event.result)
        else:
            # Route mode or fallback: single delegation
            # Reason: Route mode already validated single delegation above
            if len(delegation_requests) == 1:
                async for event in self._stream_single_delegation(
                    delegation_requests[0]["member_id"],
                    delegation_requests[0]["task"],
                    context,
                ):
                    yield event
                    # Collect result from DelegationResultEvent
                    if isinstance(event, DelegationResultEvent):
                        results.append(event.result)
            else:
                # Fallback: sequential execution
                # Reason: Safety fallback for unexpected cases
                async for event in self._stream_sequential_delegations(
                    delegation_requests, context
                ):
                    yield event
                    if isinstance(event, DelegationResultEvent):
                        results.append(event.result)

        # Add tool results to messages (match results to valid tool calls)
        # Reason: Update conversation history with delegation results
        for tool_call, result in zip(valid_tool_calls, results, strict=True):
            tool_result = {
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "name": "delegate_task_to_member",
                "content": json.dumps({"result": result}),
            }
            messages.append(tool_result)

    async def _stream_single_delegation(
        self,
        member_id: str,
        task: str,
        context: TeamExecutionContext,
        max_retries: int = 2,
    ) -> AsyncIterator[
        DelegationStartEvent
        | DelegationResultEvent
        | MemberExecutionEvent
        | SynthesisEvent
        | TeamStatusEvent
    ]:
        """
        Stream a single delegation to a member with real-time events.

        Yields events as delegation progresses:
        - DelegationStartEvent when delegation begins
        - MemberExecutionEvent for real-time member output (if supported)
        - DelegationResultEvent when delegation completes

        Args:
            member_id: ID of member to delegate to
            task: Task description for the member
            context: Execution context
            max_retries: Maximum retry attempts on failure

        Yields:
            DelegationStartEvent, MemberExecutionEvent (optional), DelegationResultEvent
        """
        # Generate unique delegation ID
        # Reason: Track individual delegations for event correlation
        delegation_id = f"delegation-{uuid.uuid4().hex[:8]}"

        # Emit delegation start event
        # Reason: Inform client that delegation has started
        yield DelegationStartEvent(member_id=member_id, task=task, delegation_id=delegation_id)

        # Get member from team's member dictionary
        # Reason: O(1) lookup for fast member access
        member = self.members.get(member_id)
        if not member:
            available = ", ".join(self.members.keys())
            yield DelegationResultEvent(
                member_id=member_id,
                result=f"Error: Member '{member_id}' not found. Available: {available}",
                success=False,
                delegation_id=delegation_id,
            )
            return

        # Check if member is enabled
        # Reason: Disabled members should not execute tasks
        if not member.enabled:
            yield DelegationResultEvent(
                member_id=member_id,
                result=f"Error: Member '{member_id}' is currently disabled.",
                success=False,
                delegation_id=delegation_id,
            )
            return

        # Check timeout before starting
        # Reason: Fail fast if we've already exceeded timeout
        try:
            context.check_timeout()
        except TeamTimeoutError as e:
            yield DelegationResultEvent(
                member_id=member_id,
                result=f"Error: {e}",
                success=False,
                delegation_id=delegation_id,
            )
            return

        # HIERARCHICAL MODE: Check if member is a Team instance
        # Reason: In hierarchical mode, members can be nested teams
        if member.is_team():
            # Validate that hierarchical mode is enabled
            # Reason: Nested teams only work in hierarchical mode
            if self.execution_mode != "hierarchical":
                yield DelegationResultEvent(
                    member_id=member_id,
                    result=(
                        f"Error: Member '{member_id}' is a Team, but execution_mode is "
                        f"'{self.execution_mode}'. Hierarchical mode is required."
                    ),
                    success=False,
                    delegation_id=delegation_id,
                )
                return

            # Increment recursion depth before delegating to nested team
            # Reason: Track how deep we've gone to prevent infinite recursion
            context.increment_depth()

            try:
                # Recursively stream from nested team
                # Reason: Nested teams handle their own delegation internally
                from framework.team.team import Team as TeamClass

                nested_team: TeamClass = member.agent  # type: ignore

                # Create new context for nested team
                # Reason: Nested team needs its own context but shares constraints
                nested_context = TeamExecutionContext(
                    run_id=f"{context.run_id}-nested-{context.recursion_depth}",
                    thread_id=context.thread_id,
                    user_id=context.user_id,
                    start_time=time.time(),
                    timeout=context.timeout - context.elapsed_time,
                    max_delegations=context.max_delegations - context.delegation_count,
                    recursion_depth=context.recursion_depth,
                    max_recursion_depth=context.max_recursion_depth,
                )

                # Stream from nested team recursively
                # Reason: Forward nested team's stream events
                accumulated_result = ""
                async for event in nested_team._stream_team_run(
                    task,
                    thread_id=context.thread_id,
                    user_id=context.user_id,
                    run_id=nested_context.run_id,
                ):
                    # Forward nested team events, but wrap member execution events
                    # Reason: Maintain event hierarchy for client
                    if isinstance(event, str):
                        accumulated_result += event
                        yield MemberExecutionEvent(
                            member_id=member_id, chunk=event, delegation_id=delegation_id
                        )
                    elif isinstance(event, MemberExecutionEvent):
                        # Re-wrap to maintain delegation_id
                        yield MemberExecutionEvent(
                            member_id=member_id, chunk=event.chunk, delegation_id=delegation_id
                        )
                    else:
                        # Forward other events (status, synthesis, etc.)
                        # Reason: Maintain event hierarchy for nested teams
                        yield event  # type: ignore[misc]

                # Emit delegation result event
                # Reason: Inform client that nested team delegation completed
                yield DelegationResultEvent(
                    member_id=member_id,
                    result=accumulated_result,
                    success=True,
                    delegation_id=delegation_id,
                )

            finally:
                # Decrement recursion depth when returning from nested team
                # Reason: Maintain accurate recursion tracking
                context.decrement_depth()

            return

        # REGULAR AGENT: Execute with streaming support
        # Reason: Agents execute tasks directly, teams delegate further
        elif member.is_agent():
            agent: Agent = member.agent  # type: ignore

            # Try to stream from agent if it supports streaming
            # Reason: Provide real-time feedback from member execution
            try:
                # Check if agent has stream method and supports streaming
                # Reason: Not all agents may support streaming
                if hasattr(agent, "stream"):
                    # Stream from agent
                    # Reason: Get real-time chunks from member execution
                    accumulated_result = ""
                    async for chunk in agent.stream(task):
                        # Handle different chunk types from agent
                        # Reason: Agent may yield strings or events
                        if isinstance(chunk, str):
                            accumulated_result += chunk
                            yield MemberExecutionEvent(
                                member_id=member_id, chunk=chunk, delegation_id=delegation_id
                            )
                        # Agent may also yield ToolStartEvent/ToolResultEvent
                        # We can forward these or convert to MemberExecutionEvent
                        # For now, skip non-string events from members

                    # Emit delegation result event
                    # Reason: Inform client that member execution completed
                    yield DelegationResultEvent(
                        member_id=member_id,
                        result=accumulated_result,
                        success=True,
                        delegation_id=delegation_id,
                    )
                    return

            except Exception:
                # Fallback to non-streaming execution if streaming fails
                # Reason: Graceful degradation - continue with invoke()
                pass

            # Fallback: Execute without streaming (with retries)
            # Reason: Some agents may not support streaming or streaming failed
            last_error: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    result = await asyncio.wait_for(agent.invoke(task), timeout=self.member_timeout)

                    if not result or not isinstance(result, str):
                        result = str(result) if result else "Member returned empty response"

                    # Emit delegation result event
                    # Reason: Inform client that member execution completed
                    yield DelegationResultEvent(
                        member_id=member_id,
                        result=result,
                        success=True,
                        delegation_id=delegation_id,
                    )
                    return

                except asyncio.TimeoutError:  # noqa: PERF203
                    # Handle timeout errors
                    # Reason: Timeouts should be retried with exponential backoff
                    # Note: try-except in loop is intentional for retry logic
                    error_msg = (
                        f"Member '{member_id}' execution timed out after {self.member_timeout}s"
                    )
                    last_error = TeamTimeoutError(error_msg)
                    if attempt < max_retries:
                        await asyncio.sleep(2**attempt)

                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        await asyncio.sleep(2**attempt)

            # All retries exhausted
            # Reason: Emit error event after all retries failed
            error_message = (
                f"Member '{member_id}' failed after {max_retries + 1} attempts. "
                f"Last error: {last_error!s}"
            )
            yield DelegationResultEvent(
                member_id=member_id,
                result=error_message,
                success=False,
                delegation_id=delegation_id,
            )

        else:
            # Invalid member type
            # Reason: Member should be either Agent or Team
            yield DelegationResultEvent(
                member_id=member_id,
                result=f"Error: Member '{member_id}' has invalid type: {type(member.agent)}",
                success=False,
                delegation_id=delegation_id,
            )

    async def _stream_sequential_delegations(
        self,
        delegations: list[dict[str, Any]],
        context: TeamExecutionContext,
    ) -> AsyncIterator[
        DelegationStartEvent
        | DelegationResultEvent
        | MemberExecutionEvent
        | SynthesisEvent
        | TeamStatusEvent
    ]:
        """
        Stream sequential delegations with real-time events.

        Processes delegations one by one, allowing each delegation to see
        results from previous delegations. Yields events for each delegation.

        Args:
            delegations: List of delegation dicts with member_id and task
            context: Execution context

        Yields:
            DelegationStartEvent, MemberExecutionEvent (optional), DelegationResultEvent for each delegation
        """
        accumulated_context = ""

        for idx, delegation in enumerate(delegations):
            # Check limits before each delegation
            # Reason: Prevent infinite loops and timeout violations
            try:
                context.check_timeout()
                context.check_delegation_limit()
            except (TeamTimeoutError, DelegationError) as e:
                # Emit error event
                # Reason: Inform client of limit exceeded
                yield DelegationResultEvent(
                    member_id=delegation["member_id"],
                    result=f"Error: {e}",
                    success=False,
                    delegation_id=f"delegation-{idx}",
                )
                return

            member_id = delegation["member_id"]
            task = delegation["task"]

            # If we have previous results, add them to context
            # Reason: Enable dependent workflows where later steps depend on earlier results
            if accumulated_context:
                enhanced_task = f"{task}\n\n## Previous Results:\n{accumulated_context}"
            else:
                enhanced_task = task

            # Stream single delegation
            # Reason: Get real-time events from member execution
            last_result = ""
            async for event in self._stream_single_delegation(member_id, enhanced_task, context):
                yield event
                # Collect result from DelegationResultEvent
                if isinstance(event, DelegationResultEvent):
                    last_result = event.result

            # Accumulate context for next delegation
            # Reason: Pass results to subsequent delegations
            if last_result:
                formatted_result = f"[{member_id}]: {last_result[:500]}"
                accumulated_context += f"\n{formatted_result}"

            # Increment delegation count
            # Reason: Track delegation progress
            context.increment_delegation_count()

            # Record delegation
            # Reason: Maintain delegation history
            context.delegations.append(
                {
                    "member_id": member_id,
                    "task": task,
                    "result": last_result,
                    "index": idx,
                }
            )

    async def _stream_parallel_delegations(
        self,
        delegations: list[dict[str, Any]],
        context: TeamExecutionContext,
    ) -> AsyncIterator[
        DelegationStartEvent
        | DelegationResultEvent
        | MemberExecutionEvent
        | SynthesisEvent
        | TeamStatusEvent
    ]:
        """
        Stream parallel delegations with real-time events.

        Creates async tasks for each delegation and executes them concurrently.
        Yields events as they occur from any delegation.

        Args:
            delegations: List of delegation dicts with member_id and task
            context: Execution context

        Yields:
            DelegationStartEvent, MemberExecutionEvent (optional), DelegationResultEvent from any delegation
        """
        # Check timeout before starting parallel execution
        # Reason: Fail fast if timeout already exceeded
        try:
            context.check_timeout()
        except TeamTimeoutError as e:
            # Emit error events for all delegations
            # Reason: Inform client that timeout exceeded
            for delegation in delegations:
                yield DelegationResultEvent(
                    member_id=delegation["member_id"],
                    result=f"Error: {e}",
                    success=False,
                    delegation_id=f"delegation-{delegation['member_id']}",
                )
            return

        # Create async tasks for each delegation with streaming
        # Reason: Execute all delegations concurrently
        async def stream_delegation_with_events(
            delegation: dict[str, Any],
        ) -> tuple[str, list[DelegationStartEvent | DelegationResultEvent | MemberExecutionEvent]]:
            """Stream single delegation and collect events."""
            events = []
            result = ""
            async for event in self._stream_single_delegation(
                delegation["member_id"], delegation["task"], context
            ):
                events.append(event)
                if isinstance(event, DelegationResultEvent):
                    result = event.result
            return result, events

        # Execute all delegations in parallel
        # Reason: Get results from all delegations concurrently
        tasks = [stream_delegation_with_events(d) for d in delegations]

        # Calculate remaining timeout
        # Reason: Ensure we don't exceed global timeout
        remaining_timeout = max(0.1, self.timeout - context.elapsed_time)

        try:
            # Gather results with timeout
            # Reason: Prevent hanging on slow members
            results_and_events = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=remaining_timeout
            )

        except asyncio.TimeoutError:
            # Timeout occurred - emit error events
            # Reason: Inform client that timeout exceeded
            for delegation in delegations:
                yield DelegationResultEvent(
                    member_id=delegation["member_id"],
                    result=f"Error: Delegation timed out (global timeout {self.timeout}s exceeded)",
                    success=False,
                    delegation_id=f"delegation-{delegation['member_id']}",
                )
            return

        # Yield events from all delegations (in order)
        # Reason: Maintain event order for client processing
        for idx, result_or_exception in enumerate(results_and_events):
            if isinstance(result_or_exception, Exception):
                # Emit error event
                # Reason: Inform client of execution failure
                yield DelegationResultEvent(
                    member_id=delegations[idx]["member_id"],
                    result=f"Error: {result_or_exception!s}",
                    success=False,
                    delegation_id=f"delegation-{idx}",
                )
            else:
                # Yield all events from this delegation
                # Reason: Forward all events to client
                if isinstance(result_or_exception, tuple):
                    _, events = result_or_exception
                    for event in events:
                        yield event

        # Update context after all complete
        # Reason: Track delegation progress
        context.delegation_count += len(delegations)

        # Record all delegations
        # Reason: Maintain delegation history
        for idx, delegation in enumerate(delegations):
            result = ""
            result_item = results_and_events[idx]
            if not isinstance(result_item, Exception) and isinstance(result_item, tuple):
                result, _ = result_item
            context.delegations.append(
                {
                    "member_id": delegation["member_id"],
                    "task": delegation["task"],
                    "result": result,
                    "index": idx,
                }
            )

    async def _stream_synthesis(
        self,
        original_query: str,
        member_results: list[dict[str, Any]],
        context: TeamExecutionContext,
    ) -> AsyncIterator[str | SynthesisEvent]:
        """
        Stream synthesis process with real-time chunks.

        Builds synthesis prompt and streams from leader model to provide
        real-time feedback during synthesis.

        Args:
            original_query: Original user query
            member_results: List of dicts with member_id, task, and result
            context: Execution context

        Yields:
            str or SynthesisEvent: Real-time chunks from synthesis process
        """
        # Build synthesis prompt with all member responses
        # Reason: Leader needs to see all responses to synthesize them effectively
        results_text = []
        for result in member_results:
            member_id = result["member_id"]
            result_content = result["result"]
            results_text.append(f"### {member_id}'s Response:\n{result_content}\n")

        # Create synthesis prompt
        # Reason: Clear instructions help leader create better synthesis
        synthesis_prompt = f"""
You are synthesizing responses from multiple team members who all worked on the same task.

Original User Query: {original_query}

## Member Responses (all addressing the same query):
{chr(10).join(results_text)}

## Your Task:
Synthesize all the above responses into a unified, comprehensive answer that:
1. Integrates insights from all members
2. Highlights common themes and patterns
3. Notes different perspectives or approaches when they exist
4. Eliminates redundancy while preserving important information
5. Provides a well-rounded, complete answer that benefits from multiple viewpoints

Write your synthesized response:
"""

        # Stream from leader model for synthesis
        # Reason: Provide real-time feedback during synthesis
        messages = [
            {"role": "system", "content": self._build_leader_system_prompt()},
            {"role": "user", "content": synthesis_prompt},
        ]

        # Stream synthesis response
        # Reason: Get real-time chunks from leader as it synthesizes
        try:
            stream_iter = self.model.stream(
                messages=messages,
                tools=None,  # No tools needed for synthesis
                temperature=0.7,
            )

            async for chunk in stream_iter:  # type: ignore[union-attr]
                if chunk.content:
                    # Yield synthesis chunk
                    # Reason: Client sees synthesis progress in real-time
                    yield SynthesisEvent(chunk=chunk.content, stage="synthesizing")
                    yield chunk.content  # Also yield as string for backward compatibility

        except Exception as e:
            # Emit error event
            # Reason: Inform client of synthesis failure
            yield SynthesisEvent(chunk=f"Error during synthesis: {e}", stage="error")

    async def stream(
        self,
        message: str,
        *,
        thread_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[
        str
        | DelegationStartEvent
        | DelegationResultEvent
        | MemberExecutionEvent
        | SynthesisEvent
        | TeamStatusEvent
    ]:
        """
        Stream team execution with real-time updates and events.

        Production-grade streaming that yields:
        - Real-time text chunks from leader model
        - Delegation events (start/result) for transparency
        - Member execution progress (if members support streaming)
        - Synthesis progress (for coordinate/collaborate modes)
        - Status updates throughout execution

        The streaming flow varies by execution mode:
        - Route mode: Stream leader decision → delegation event → member result
        - Coordinate mode: Stream leader → delegations → synthesis
        - Collaborate mode: Stream parallel delegations → synthesis
        - Hierarchical mode: Stream nested team execution recursively

        Args:
            message: User's input message
            thread_id: Optional thread ID for conversation continuity
            user_id: Optional user ID
            **kwargs: Additional arguments

        Yields:
            Union of:
            - str: Text chunks from leader or members
            - DelegationStartEvent: When delegation starts (member_id, task, delegation_id)
            - DelegationResultEvent: When delegation completes (member_id, result, success, delegation_id)
            - MemberExecutionEvent: Real-time chunks from member execution (member_id, chunk, delegation_id)
            - SynthesisEvent: Synthesis progress chunks (chunk, stage)
            - TeamStatusEvent: Status updates (status, phase, metadata)

        Example:
            ```python
            async for event in team.stream("Research topic X"):
                if isinstance(event, str):
                    print(event, end="", flush=True)  # Text chunk
                elif isinstance(event, DelegationStartEvent):
                    print(f"\\n[Delegating to {event.member_id}]")
                elif isinstance(event, DelegationResultEvent):
                    if event.success:
                        print(f"\\n[{event.member_id} completed]")
                    else:
                        print(f"\\n[{event.member_id} failed: {event.result}]")
                elif isinstance(event, MemberExecutionEvent):
                    print(event.chunk, end="", flush=True)  # Member output
                elif isinstance(event, SynthesisEvent):
                    print(f"[Synthesis] {event.chunk}", end="", flush=True)
                elif isinstance(event, TeamStatusEvent):
                    print(f"\\n[Status: {event.phase}] {event.status}")
            ```
        """
        # Validate input
        # Reason: Ensure input is valid before processing
        if not message or not isinstance(message, str):
            raise ValidationError("Message must be a non-empty string")

        if len(message) > 100_000:
            raise ValidationError("Message cannot be longer than 100000 characters")

        # Stream team execution with real-time events
        # Reason: Provide production-grade streaming with full event support
        async for event in self._stream_team_run(
            message, thread_id=thread_id, user_id=user_id, **kwargs
        ):
            yield event

    def __repr__(self) -> str:
        """String representation of the Team."""
        return f"Team(id={self.id!r}, name={self.name!r}, members={len(self.members)})"

    def __str__(self) -> str:
        """Human-friendly representation."""
        return self.__repr__()
