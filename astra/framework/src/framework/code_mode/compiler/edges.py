"""DSL edge definitions for Astra workflow graphs.

Edges connect nodes and define execution flow. Three edge types:

  - Sequential:   default flow from one node to the next
  - Conditional:  routes based on a predicate (used by BranchNode, GateNode)
  - Error:        routes on failure (used by FallbackNode)

Each edge carries an ``EdgeRole`` that encodes its semantic purpose
(e.g. "then", "else", "body", "back_edge") — this is the single source
of truth for flow routing.  Node dataclasses no longer store target IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import enum
from typing import Any
import uuid


class EdgeType(str, enum.Enum):
    """Discriminator for the three edge types."""

    SEQUENTIAL = "sequential"  # default flow: A finishes → B starts
    CONDITIONAL = "conditional"  # predicate-gated: A finishes → if cond → B
    ERROR = "error"  # failure path: A fails → B starts


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
    LOOP_ELSE = "loop_else"  # LoopNode completion → else block
    TRY = "try"  # FallbackNode primary path
    CATCH = "catch"  # FallbackNode failure path
    COMPENSATE = "compensate"  # FallbackNode rollback path
    APPROVED = "approved"  # GateNode approval path
    DENIED = "denied"  # GateNode denial path
    BRANCH = "branch"  # ParallelNode fan-out
    CUSTOM = "custom"  # Forward-compat for programmatic workflows


@dataclass
class DslEdge:
    """A directed connection between two nodes in a DSL workflow.

    Attributes:
        id:        Unique edge identifier.
        source:    ID of the source node.
        target:    ID of the target node.
        type:      Edge type (sequential, conditional, error).
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
) -> DslEdge:
    """Create a sequential edge between two nodes."""
    return DslEdge(source=source, target=target, type=EdgeType.SEQUENTIAL, role=role, **kwargs)


def conditional(
    source: str,
    target: str,
    condition: str,
    label: str = "",
    *,
    role: EdgeRole = EdgeRole.NONE,
    **kwargs: Any,
) -> DslEdge:
    """Create a conditional edge with a predicate expression."""
    return DslEdge(
        source=source,
        target=target,
        type=EdgeType.CONDITIONAL,
        condition=condition,
        label=label or condition,
        role=role,
        **kwargs,
    )


def error_edge(
    source: str, target: str, *, role: EdgeRole = EdgeRole.CATCH, **kwargs: Any
) -> DslEdge:
    """Create an error/fallback edge (triggered on node failure)."""
    return DslEdge(
        source=source,
        target=target,
        type=EdgeType.ERROR,
        label="on_error",
        role=role,
        **kwargs,
    )


# ── Edge collection utilities
def outgoing(edges: list[DslEdge], node_id: str) -> list[DslEdge]:
    """Return all edges leaving a given node, sorted by priority."""
    return sorted(
        [e for e in edges if e.source == node_id],
        key=lambda e: e.priority,
    )


def incoming(edges: list[DslEdge], node_id: str) -> list[DslEdge]:
    """Return all edges arriving at a given node."""
    return [e for e in edges if e.target == node_id]


def targets(edges: list[DslEdge], node_id: str) -> list[str]:
    """Return target node IDs for all outgoing edges from a node."""
    return [e.target for e in outgoing(edges, node_id)]


def sources(edges: list[DslEdge], node_id: str) -> list[str]:
    """Return source node IDs for all incoming edges to a node."""
    return [e.source for e in incoming(edges, node_id)]


def by_role(edges: list[DslEdge], node_id: str, role: EdgeRole) -> DslEdge | None:
    """Find the outgoing edge with a specific role from a node.

    Returns the first matching edge, or None if no edge with that role exists.
    """
    for e in outgoing(edges, node_id):
        if e.role == role:
            return e
    return None
