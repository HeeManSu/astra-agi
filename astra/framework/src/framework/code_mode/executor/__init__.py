"""
Execution engine — public package exports.

Usage:
    from framework.code_mode.executor import run_plan, ExecutionResult

    result = await run_plan(plan, initial_state, tools)
    if result.ok:
        print(result.response)
    else:
        print(result.error)
"""

from framework.code_mode.executor.models import (
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    JournalEntry,
    NodeResult,
)
from framework.code_mode.executor.runner import run_plan


__all__ = [
    "ExecutionContext",
    "ExecutionResult",
    "ExecutionStatus",
    "JournalEntry",
    "NodeResult",
    "run_plan",
]
