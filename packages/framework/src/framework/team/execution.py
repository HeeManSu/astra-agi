"""
Execution logic for Team module.

This module contains all execution-related functions including:
- Execution modes (route, coordinate, collaborate, hierarchical)
- Delegation methods (single, sequential, parallel)
- Memory & context methods
- Result formatting

Functions in this module take `team: Team` as the first parameter to access
Team attributes while keeping execution logic separate from orchestration.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from framework.agents.agent import Agent
from framework.storage.memory import AgentStorage
from framework.team.types import (
    MemberNotFoundError,
    TeamError,
    TeamExecutionContext,
    TeamTimeoutError,
)


if TYPE_CHECKING:
    from framework.team.team import Team


# MEMORY & CONTEXT METHODS


async def load_conversation_context(
    team: Team, thread_id: str | None, storage: AgentStorage | None
) -> list[dict[str, Any]]:
    """
    Load conversation history from storage.

    Extracts past messages and delegation patterns to help the leader
    make better routing decisions based on conversation context.

    Args:
        team: Team instance (for accessing methods)
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
        limit = 20
        if team.memory and team.memory.num_history_responses:
            limit = team.memory.num_history_responses * 2
        history = await storage.get_history(thread_id, limit=limit)

        # Convert Message objects to dict format
        context = []
        for msg in history:
            msg_dict = storage._message_to_dict(msg)
            context.append(msg_dict)

        # Extract past delegations for additional context
        past_delegations = extract_past_delegations(team, history)

        # If we have past delegations, add summary to context
        if past_delegations:
            delegation_summary = format_delegation_summary(team, past_delegations)
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


def extract_past_delegations(team: Team, history: list[Any]) -> list[dict[str, Any]]:
    """
    Extract past delegation patterns from conversation history.

    Looks for tool calls with name "delegate_task_to_member" in assistant
    messages to identify previous delegation decisions.

    Args:
        team: Team instance (unused but kept for consistency)
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


def format_delegation_summary(team: Team, delegations: list[dict[str, Any]]) -> str:
    """
    Format delegation history into a readable summary.

    Args:
        team: Team instance (unused but kept for consistency)
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


# DELEGATION EXECUTION METHODS


async def execute_single_delegation(
    team: Team,
    member_id: str,
    task: str,
    context: TeamExecutionContext,
    max_retries: int = 2,
) -> str:
    """
    Execute a single delegation to a member agent or team.

    This function handles delegation to both Agent instances (regular members)
    and Team instances (nested teams for hierarchical mode). It supports:
    - Regular agent execution with retries
    - Nested team execution with recursion tracking
    - Timeout handling and error formatting

    Args:
        team: Team instance (for accessing members and configuration)
        member_id: ID of member to delegate to
        task: Task description for the member
        context: Execution context (includes recursion tracking for hierarchical mode)
        max_retries: Maximum retry attempts on failure (only for agents)

    Returns:
        Result string from member agent or nested team

    Raises:
        MemberNotFoundError: If member doesn't exist
        DelegationError: If delegation fails after retries or recursion limit exceeded

    Example:
        ```python
        # Regular agent delegation
        result = await execute_single_delegation(team, "researcher", "Research topic X", context)

        # Nested team delegation (hierarchical mode)
        result = await execute_single_delegation(
            team, "research-team", "Complete research project", context
        )
        ```
    """
    # Get member from team's member dictionary
    # Reason: O(1) lookup for fast member access
    member = team.members.get(member_id)
    if not member:
        available = ", ".join(team.members.keys())
        raise MemberNotFoundError(f"Member '{member_id}' not found. Available: {available}")

    # Check if member is enabled
    # Reason: Disabled members should not execute tasks
    if not member.enabled:
        return (
            f"Error: Member '{member_id}' is currently disabled. "
            f"Please use a different member or enable this member."
        )

    # Check timeout before starting
    # Reason: Fail fast if we've already exceeded timeout
    context.check_timeout()

    # HIERARCHICAL MODE: Check if member is a Team instance
    # Reason: In hierarchical mode, members can be nested teams
    if member.is_team():
        # Validate that hierarchical mode is enabled
        # Reason: Nested teams only work in hierarchical mode
        if team.execution_mode != "hierarchical":
            return (
                f"Error: Member '{member_id}' is a Team, but execution_mode is "
                f"'{team.execution_mode}'. Hierarchical mode is required for nested teams."
            )

        # Increment recursion depth before delegating to nested team
        # Reason: Track how deep we've gone to prevent infinite recursion
        context.increment_depth()

        try:
            # Recursively invoke the nested team
            # Reason: Nested teams handle their own delegation internally
            from framework.team.team import Team as TeamClass

            nested_team: TeamClass = member.agent  # type: ignore

            # Create new context for nested team (inherit some settings)
            # Reason: Nested team needs its own context but shares some constraints
            nested_context = TeamExecutionContext(
                run_id=f"{context.run_id}-nested-{context.recursion_depth}",
                thread_id=context.thread_id,
                user_id=context.user_id,
                start_time=time.time(),
                timeout=context.timeout - context.elapsed_time,  # Remaining timeout
                max_delegations=context.max_delegations
                - context.delegation_count,  # Remaining delegations
                recursion_depth=context.recursion_depth,
                max_recursion_depth=context.max_recursion_depth,
            )

            # Invoke nested team recursively
            # Reason: Nested team will handle its own delegation internally
            result = await nested_team.invoke(
                task,
                thread_id=context.thread_id,
                user_id=context.user_id,
                run_id=nested_context.run_id,
            )

            return result

        finally:
            # Decrement recursion depth when returning from nested team
            # Reason: Maintain accurate recursion tracking
            context.decrement_depth()

    # REGULAR AGENT: Execute normally with retries
    # Reason: Agents execute tasks directly, teams delegate further
    elif member.is_agent():
        # Get agent instance
        agent: Agent = member.agent  # type: ignore

        # Retry loop with exponential backoff
        # Reason: Transient failures should be retried with increasing delays
        # Note: try-except in loop is intentional for retry logic (not a performance issue)
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                # Execute with per-member timeout
                # Reason: Each member should have its own timeout to prevent blocking
                result = await asyncio.wait_for(agent.invoke(task), timeout=team.member_timeout)

                # Validate result is not empty
                # Reason: Empty results indicate potential issues
                if not result or not isinstance(result, str):
                    result = str(result) if result else "Member returned empty response"

                return result

            except asyncio.TimeoutError:  # noqa: PERF203
                # Handle timeout errors
                # Reason: Timeouts should be retried with exponential backoff
                # Note: try-except in loop is intentional for retry logic
                error_msg = f"Member '{member_id}' execution timed out after {team.member_timeout}s"
                last_error = TeamTimeoutError(error_msg)

                # If not last attempt, wait before retry
                # Reason: Exponential backoff reduces load on failing systems
                if attempt < max_retries:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s...
                    await asyncio.sleep(wait_time)

            except Exception as e:
                # Handle other exceptions
                # Reason: Various errors can occur (network, model, etc.)
                # Note: try-except in loop is intentional for retry logic (not a performance issue)
                last_error = e
                error_msg = f"Member '{member_id}' execution failed: {e!s}"

                # If not last attempt, wait before retry
                # Reason: Exponential backoff for transient errors
                if attempt < max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)

        # All retries exhausted
        # Reason: After max retries, return error message instead of raising
        error_message = (
            f"Member '{member_id}' failed after {max_retries + 1} attempts. "
            f"Last error: {last_error!s}"
        )
        return error_message

    else:
        # Invalid member type
        # Reason: Member should be either Agent or Team
        return f"Error: Member '{member_id}' has invalid type: {type(member.agent)}"


async def execute_sequential_delegations(
    team: Team,
    delegations: list[dict[str, Any]],
    context: TeamExecutionContext,
) -> list[str]:
    """
    Execute delegations sequentially, passing results between them.

    Processes delegations one by one, allowing each delegation to see
    results from previous delegations. This enables dependent workflows
    where later steps depend on earlier results.

    Args:
        team: Team instance (for accessing execution methods)
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
        result = await execute_single_delegation(team, member_id, enhanced_task, context)

        # Format result for next delegation
        formatted_result = format_delegation_result(team, member_id, result, idx)
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


async def execute_parallel_delegations(
    team: Team,
    delegations: list[dict[str, Any]],
    context: TeamExecutionContext,
) -> list[str]:
    """
    Execute independent delegations in parallel.

    Creates async tasks for each delegation and executes them concurrently
    using asyncio.gather(). Handles partial failures and maintains
    result ordering. Each delegation is independent (no shared state).

    Args:
        team: Team instance (for accessing execution methods)
        delegations: List of delegation dicts with member_id and task
        context: Execution context

    Returns:
        List of results in same order as delegations
    """
    # Check timeout before starting parallel execution
    context.check_timeout()

    # Cap max_parallel to actual delegation count (for future use)
    _effective_max_parallel = min(len(delegations), team.max_parallel)

    # Create async tasks for each delegation
    # Use default arguments to capture loop variables correctly (closure fix)
    tasks = []
    for delegation in delegations:
        member_id = delegation["member_id"]
        task_desc = delegation["task"]

        # Create task with default args to avoid closure issue
        async def execute_delegation(m_id: str = member_id, t: str = task_desc) -> str:
            """Execute single delegation with timeout."""
            return await execute_single_delegation(team, m_id, t, context)

        tasks.append(execute_delegation())

    # Execute all tasks in parallel with global timeout
    # Calculate remaining timeout
    remaining_timeout = max(0.1, team.timeout - context.elapsed_time)

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True), timeout=remaining_timeout
        )

    except asyncio.TimeoutError:
        # Timeout occurred - format partial results
        results = [
            f"Error: Delegation timed out (global timeout {team.timeout}s exceeded)"
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


# RESULT FORMATTING METHODS


def format_delegation_result(team: Team, member_id: str, result: str, index: int) -> str:
    """
    Format delegation result for inclusion in next delegation or final response.

    Creates a readable format that can be passed to subsequent delegations
    or included in the leader's final synthesis.

    Args:
        team: Team instance (unused but kept for consistency)
        member_id: ID of member that produced the result
        result: Raw result string from member
        index: Index of this delegation in the sequence

    Returns:
        Formatted result string

    Example:
        ```python
        formatted = format_delegation_result(team, "researcher", "Found 10 sources", 0)
        # Returns: "[researcher]: Found 10 sources"
        ```
    """
    # Truncate very long results to avoid context bloat
    # Reason: Very long results can cause token limit issues in LLM context
    max_result_length = 500
    if len(result) > max_result_length:
        truncated = result[:max_result_length] + "... (truncated)"
    else:
        truncated = result

    return f"[{member_id}]: {truncated}"


# COLLABORATE MODE METHODS


async def execute_collaborate_mode(
    team: Team,
    message: str,
    context: TeamExecutionContext,
) -> list[str]:
    """
    Execute collaborate mode: all members work on same task simultaneously.

    In collaborate mode, the leader delegates the SAME task to ALL enabled
    members. All members execute in parallel, and their results are collected
    for synthesis. This is useful for brainstorming, multi-perspective analysis,
    or consensus building.

    Args:
        team: Team instance (for accessing members and execution methods)
        message: User's original message (same task for all members)
        context: Execution context for tracking state

    Returns:
        List of results from all members (in order of enabled members)

    Raises:
        TeamError: If no enabled members are available

    Example:
        ```python
        # All members work on the same task
        results = await execute_collaborate_mode(
            team, "Analyze pros and cons of remote work", context
        )
        # Returns: [result1, result2, result3] - one result per member
        ```
    """
    # Get all enabled members
    # Reason: Only enabled members should participate in collaboration
    enabled_members = [member for member in team.members.values() if member.enabled]

    # Check that we have at least one enabled member
    # Reason: Cannot collaborate with zero members
    if not enabled_members:
        raise TeamError("No enabled members available for collaboration")

    # Create delegation requests for all members (same task)
    # Reason: In collaborate mode, all members work on the same task
    delegation_requests = [
        {
            "member_id": member.id,
            "task": message,  # Same task for all members
        }
        for member in enabled_members
    ]

    # Execute all delegations in parallel
    # Reason: All members work simultaneously on the same task
    results = await execute_parallel_delegations(team, delegation_requests, context)

    return results


async def synthesize_collaborate_results(
    team: Team,
    original_query: str,
    member_results: list[dict[str, Any]],
    context: TeamExecutionContext,
) -> str:
    """
    Synthesize results from collaborate mode into unified response.

    In collaborate mode, all members worked on the same task, so we need to
    combine their different perspectives into a unified answer. This function
    builds a synthesis prompt and uses the leader model to create a cohesive
    response that integrates insights from all members.

    Args:
        team: Team instance (for accessing model and prompt building)
        original_query: Original user query that all members addressed
        member_results: List of dicts with member_id, task, and result
        context: Execution context (not used but kept for consistency)

    Returns:
        Synthesized response string that combines all member perspectives

    Example:
        ```python
        member_results = [
            {"member_id": "member1", "task": "Analyze X", "result": "Perspective 1"},
            {"member_id": "member2", "task": "Analyze X", "result": "Perspective 2"},
        ]
        synthesized = await synthesize_collaborate_results(
            team, "Analyze X", member_results, context
        )
        # Returns: Unified response combining both perspectives
        ```
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

    # Call leader model for synthesis
    # Reason: Leader model is best positioned to synthesize multiple perspectives
    messages = [
        {"role": "system", "content": team._build_leader_system_prompt()},
        {"role": "user", "content": synthesis_prompt},
    ]

    # Invoke leader model without tools (synthesis doesn't need delegation)
    # Reason: Synthesis is a text generation task, not a delegation task
    response = await team.model.invoke(
        messages=messages,
        tools=None,  # No tools needed for synthesis
        temperature=0.7,  # Reasonable temperature for creative synthesis
    )

    return response.content or ""
