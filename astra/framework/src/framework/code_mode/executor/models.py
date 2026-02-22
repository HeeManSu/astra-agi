"""
Execution engine data models — pure dataclasses, no logic.

  ExecutionContext  - mutable state carried through the main loop
  JournalEntry     - one record per node execution (append-only)
  NodeResult       - what a handler returns (status + outputs + next cursor)
  ExecutionResult  - final outcome returned to the caller
"""

from __future__ import annotations

from dataclasses import dataclass, field
import enum
import time
from typing import Any

from framework.code_mode.compiler.schema import DslWorkflow


# ── Status ------------------------------------------------------------------


class ExecutionStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"  # GateNode paused
    CANCELLED = "cancelled"  # externally cancelled via cancel_event


# ── Per-node record ---------------------------------------------------------


@dataclass
class JournalEntry:
    """Immutable record written once per node execution."""

    node_id: str
    node_type: str
    label: str
    status: str  # "ok" | "error" | "skipped" | "timeout"
    started_at: float  # time.monotonic()
    duration_ms: float
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    error: str | None = None
    # Populated when a tool returns {"__token_usage__": {"prompt_tokens": N, ...}}
    token_usage: dict[str, int] = field(default_factory=dict)


# ── What each handler returns -----------------------------------------------


@dataclass
class NodeResult:
    """Value returned by every node handler to the runner."""

    status: str  # "ok" | "error" | "timeout"
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    # If a handler already knows the next node (e.g. RespondNode terminates),
    # it can signal it here. None means runner resolves via _resolve_next.
    override_next: str | None = None


# ── Mutable execution context -----------------------------------------------


@dataclass
class ExecutionContext:
    """All mutable state carried through a single workflow run."""

    workflow: DslWorkflow
    state: dict[str, Any]  # live workflow state
    journal: list[JournalEntry]  # append-only
    current_node_id: str  # cursor — where we are now
    visited_count: dict[str, int]  # node_id → times visited (loop safety)
    status: ExecutionStatus
    start_time: float  # time.monotonic() at run start
    retry_counts: dict[str, int] = field(default_factory=dict)

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.start_time

    def visit(self, node_id: str) -> None:
        self.visited_count[node_id] = self.visited_count.get(node_id, 0) + 1


# ── Final outcome -----------------------------------------------------------


@dataclass
class ExecutionResult:
    """Returned by run_workflow() to the caller."""

    ok: bool
    status: ExecutionStatus
    response: str | None  # from RespondNode.message
    state: dict[str, Any]  # final state snapshot
    journal: list[JournalEntry]  # complete execution log
    error: str | None = None
    duration_ms: float = 0.0
    # Sum of all token_usage fields across the journal (prompt_tokens, completion_tokens, etc.)
    total_token_usage: dict[str, int] = field(default_factory=dict)
