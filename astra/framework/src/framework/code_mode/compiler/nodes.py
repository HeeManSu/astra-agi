"""DSL node definitions for Astra execution plans.

Five node types used by the code-generation pipeline:

  Core:          ActionNode, TransformNode, RespondNode
  Control Flow:  BranchNode, LoopNode

Every node shares a common base (``PlanNode``) that carries identity
and I/O bindings.  Type-specific fields live on each subclass.

Flow routing (which node connects to which) is handled exclusively
by ``PlanEdge`` objects with ``EdgeRole`` tags — node dataclasses do
NOT store target IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import enum
import uuid


class NodeType(str, enum.Enum):
    """Discriminator for node types."""

    ACTION = "action"  # Calls an external tool (side-effecting)
    TRANSFORM = "transform"  # Pure data manipulation
    RESPOND = "respond"  # Returns final result to the caller
    BRANCH = "branch"  # Conditional routing (if/else)
    LOOP = "loop"  # Iterates over a collection


@dataclass
class PlanNode:
    """Base for every node in a DSL execution plan.

    Attributes:
        id:          Unique node identifier.
        type:        Discriminator tag (set by each subclass).
        label:       Human-readable name for UI / logs.
        description: Optional longer description.
        inputs:      Map of input-slot → expression (JSONPath-like).
        outputs:     Map of output-slot → expression.
    """

    type: NodeType
    label: str = ""
    description: str = ""
    id: str = field(default_factory=lambda: f"n_{uuid.uuid4().hex[:8]}")

    # I/O bindings (JSONPath expressions referencing workflow state)
    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)


# ── Core nodes
@dataclass
class ActionNode(PlanNode):
    """Call an external tool or operation (has side effects).

    This is the workhorse node — maps to a tool call in generated code.

    Example:
        tool = "market_analyst.get_stock_price"
        inputs = {"symbol": "$.user.stock_symbol"}
        outputs = {"price": "$.result.current_price"}
    """

    type: NodeType = field(default=NodeType.ACTION, init=False)

    tool: str = ""  # "domain.tool-slug" identifier
    is_async: bool = False  # future: concurrent tool calls


@dataclass
class TransformNode(PlanNode):
    """Pure data manipulation — no side effects.

    Runs an expression against the current state and writes the result
    back.  Used for assignments that don't map to tool calls.

    Example:
        expression = "$.price * $.quantity"
        assign_to  = "$.total_cost"
    """

    type: NodeType = field(default=NodeType.TRANSFORM, init=False)

    expression: str = ""  # Python expression to evaluate
    assign_to: str = ""  # state path to write result


@dataclass
class RespondNode(PlanNode):
    """Return the final result to the caller.

    Typically the final node in an execution plan.  In code-mode, exactly
    one ``RespondNode`` is generated (mirroring ``synthesize_response()``).

    Example:
        message = "$.formatted_response"
    """

    type: NodeType = field(default=NodeType.RESPOND, init=False)

    message: str = ""  # expression or template for the response


# ── Control flow nodes
@dataclass
class BranchNode(PlanNode):
    """Conditional routing (if / else / switch).

    Evaluates ``condition`` and routes via outgoing edges.
    The node stores *only* the condition — routing is fully
    determined by edges:

    - ``EdgeRole.THEN``             → target when condition is truthy
    - ``EdgeRole.ELSE``             → target when condition is falsy (explicit else)
    - ``EdgeRole.ELSE_FALLTHROUGH`` → target when condition is falsy (no else block)

    Example::

        BranchNode(id="br_1", condition="risk_score > threshold")
    """

    type: NodeType = field(default=NodeType.BRANCH, init=False)

    condition: str = ""  # predicate expression


@dataclass
class LoopNode(PlanNode):
    """Iterate over a collection with a body sub-graph.

    The node stores *only* the collection path, iteration variable, and
    safety cap.  Routing is defined by edges:

    - ``EdgeRole.BODY``      → entry of the loop body
    - ``EdgeRole.BACK_EDGE`` → tail of loop body back to this node (next iteration)
    - Sequential ``NONE``    → exit edge to the statement after the loop

    Example::

        LoopNode(id="loop_1", over="$.items", as_var="item")
    """

    type: NodeType = field(default=NodeType.LOOP, init=False)

    over: str = ""  # state path to an iterable
    as_var: str = "item"  # variable name for current element
    max_iterations: int = 1000  # safety cap


# ── Registry
PLAN_NODE_MAP: dict[NodeType, type[PlanNode]] = {
    NodeType.ACTION: ActionNode,
    NodeType.TRANSFORM: TransformNode,
    NodeType.RESPOND: RespondNode,
    NodeType.BRANCH: BranchNode,
    NodeType.LOOP: LoopNode,
}
"""Lookup table: NodeType enum → concrete dataclass."""
