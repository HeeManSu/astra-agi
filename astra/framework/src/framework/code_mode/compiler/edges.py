"""DSL edge definitions for Astra execution plans.

Edges connect nodes and define execution flow. Two edge types:

  - Sequential:   default flow from one node to the next
  - Conditional:  routes based on a predicate (used by BranchNode)

Each edge carries an ``EdgeRole`` that encodes its semantic purpose
(e.g. "then", "else", "body", "back_edge") — this is the single source
of truth for flow routing.  Node dataclasses do NOT store target IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import enum
from typing import Any
import uuid


class EdgeType(str, enum.Enum):
    """Discriminator for edge types."""

    SEQUENTIAL = "sequential"  # default flow: A finishes → B starts
    CONDITIONAL = "conditional"  # predicate-gated: A finishes → if cond → B


class EdgeRole(str, enum.Enum):
    """Semantic role of an edge — replaces node-internal routing fields.

    This enum is the single source of truth for *why* an edge exists.
    Prevents typos (``EdgeRole("thne")`` → ValueError) and enables
    cardinality validation (e.g. exactly 1 THEN per BranchNode).
    """

    NONE = ""  # plain sequential, no special role
    THEN = "then"  # BranchNode true-path
    ELSE = "else"  # BranchNode false-path (explicit else block)
    ELSE_FALLTHROUGH = "else_fallthrough"  # BranchNode false-path (no else, skip to next)
    BODY = "body"  # LoopNode → first body node
    BACK_EDGE = "back_edge"  # LoopNode body tail → loop (iteration)


@dataclass
class PlanEdge:
    """A directed connection between two nodes in an execution plan.

    Attributes:
        id:        Unique edge identifier.
        source:    ID of the source node.
        target:    ID of the target node.
        type:      Edge type (sequential, conditional).
        role:      Semantic role — why this edge exists (then, else, body, etc.).
        condition: Predicate expression for conditional edges (None for others).
        label:     Human-readable label for UI display.
        priority:  Ordering hint when multiple edges leave one node.
    """

    source: str
    target: str
    type: EdgeType = EdgeType.SEQUENTIAL
    id: str = field(default_factory=lambda: f"e_{uuid.uuid4().hex[:8]}")
    role: EdgeRole = EdgeRole.NONE
    condition: str | None = None  # only for EdgeType.CONDITIONAL
    label: str = ""  # UI display label
    priority: int = 0  # lower = evaluated first


# ── Edge factory helpers
def sequential(
    source: str, target: str, *, role: EdgeRole = EdgeRole.NONE, **kwargs: Any
) -> PlanEdge:
    """Create a sequential edge between two nodes."""
    return PlanEdge(source=source, target=target, type=EdgeType.SEQUENTIAL, role=role, **kwargs)


def conditional(
    source: str,
    target: str,
    condition: str,
    label: str = "",
    *,
    role: EdgeRole = EdgeRole.NONE,
    **kwargs: Any,
) -> PlanEdge:
    """Create a conditional edge with a predicate expression."""
    return PlanEdge(
        source=source,
        target=target,
        type=EdgeType.CONDITIONAL,
        condition=condition,
        label=label or condition,
        role=role,
        **kwargs,
    )
