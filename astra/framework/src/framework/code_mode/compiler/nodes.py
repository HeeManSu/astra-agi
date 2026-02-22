"""DSL node definitions for Astra workflow graphs.

Twelve node types across four tiers:

  Tier 1 — Core:          ActionNode, TransformNode, RespondNode
  Tier 2 — Control Flow:  BranchNode, ParallelNode, LoopNode, SubflowNode
  Tier 3 — Reliability:   GateNode, CheckpointNode, FallbackNode
  Tier 4 — Orchestration: ReplanNode, TerminateNode

Every node shares a common base (``DslNode``) that carries identity,
retry/timeout config, and UI position metadata.  Type-specific fields
live on each subclass.

Flow routing (which node connects to which) is handled exclusively
by ``DslEdge`` objects with ``EdgeRole`` tags — node dataclasses do
NOT store target IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import enum
import uuid


class NodeType(str, enum.Enum):
    """Discriminator for the 12 node types."""

    # Tier 1 — Core
    ACTION = "action"  # Calls an external tool or performs a side-effecting operation
    TRANSFORM = "transform"  # Pure data manipulation — no side effects
    RESPOND = "respond"  # Returns the final result to the caller

    # Tier 2 — Control Flow
    BRANCH = "branch"  # Routes execution based on a conditional expression
    PARALLEL = "parallel"  # Executes multiple branches concurrently and joins results
    LOOP = "loop"  # Iterates over a collection and executes a body subgraph
    SUBFLOW = "subflow"  # Delegates execution to another workflow

    # Tier 3 — Reliability
    GATE = "gate"  # Pauses execution awaiting human or external approval
    CHECKPOINT = "checkpoint"  # Persists workflow state for resume or replay
    FALLBACK = "fallback"  # Executes a primary path with fallback and compensation handling

    # Tier 4 — Orchestration
    REPLAN = "replan"  # Sends current state back to planner for dynamic re-routing
    TERMINATE = "terminate"  # Terminates the workflow with a final status


class JoinStrategy(str, enum.Enum):
    """How a parallel node waits for its branches."""

    ALL = "all"  # wait for every branch (default)
    ANY = "any"  # proceed when first branch finishes
    RACE = "race"  # proceed with fastest, cancel others


class ReplanScope(str, enum.Enum):
    """How much of the workflow the planner may re-route."""

    REMAINING = "remaining"  # only unexecuted nodes
    FULL = "full"  # entire workflow (re-plan from scratch)


class TerminateStatus(str, enum.Enum):
    """Final status when a workflow terminates."""

    SUCCESS = "success"
    FAILURE = "failure"
    CANCEL = "cancel"


class GateTimeoutAction(str, enum.Enum):
    """What happens when a gate times out waiting for approval."""

    DENY = "deny"
    APPROVE = "approve"
    FAIL = "fail"


# ── Shared config
@dataclass
class RetryConfig:
    """Retry policy attachable to any node."""

    max_attempts: int = 1
    backoff: str = "exponential"  # "fixed" | "linear" | "exponential"
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0


@dataclass
class Position:
    """XY coordinates for visual builder rendering."""

    x: float = 0.0
    y: float = 0.0


@dataclass
class DslNode:
    """Base for every node in a DSL workflow graph.

    Attributes:
        id:          Unique node identifier.
        type:        Discriminator tag (set by each subclass).
        label:       Human-readable name for UI / logs.
        description: Optional longer description.
        inputs:      Map of input-slot → expression (JSONPath-like).
        outputs:     Map of output-slot → expression.
        retry:       Optional retry policy.
        timeout_seconds:  Max wall-clock time before the node is killed.
        position:    XY for the visual builder canvas.
    """

    type: NodeType
    label: str = ""
    description: str = ""
    id: str = field(default_factory=lambda: f"n_{uuid.uuid4().hex[:8]}")

    # I/O bindings (JSONPath expressions referencing workflow state)
    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)

    # Reliability config (applies to every node type)
    retry: RetryConfig | None = None
    timeout_seconds: float | None = None

    # Visual builder metadata
    position: Position = field(default_factory=Position)


# ── Tier 1: Core
@dataclass
class ActionNode(DslNode):
    """Call an external tool or operation (has side effects).

    This is the workhorse node — maps to a tool call in generated code.

    Example:
        tool = "market_analyst.get_stock_price"
        inputs = {"symbol": "$.user.stock_symbol"}
        outputs = {"price": "$.result.current_price"}
    """

    type: NodeType = field(default=NodeType.ACTION, init=False)

    tool: str = ""  # fully-qualified tool name: agent.method
    is_async: bool = False  # fire-and-forget (don't block on result)


@dataclass
class TransformNode(DslNode):
    """Pure data manipulation — no side effects.

    Runs an expression against the current state and writes the result
    back.  The visual builder renders these differently (no external
    call indicator) so users can distinguish "compute" from "call."

    Example:
        expression = "$.price * $.quantity"
        assign_to  = "$.total_cost"
    """

    type: NodeType = field(default=NodeType.TRANSFORM, init=False)

    expression: str = ""  # computation expression
    assign_to: str = ""  # state path to write result into


@dataclass
class RespondNode(DslNode):
    """Return the final result to the caller.

    Typically the final node in a workflow.  In code-mode, exactly one
    ``RespondNode`` is generated (mirroring ``synthesize_response()``).
    The DSL schema allows multiple respond paths for branching workflows.

    Example:
        message = "$.formatted_response"
    """

    type: NodeType = field(default=NodeType.RESPOND, init=False)

    message: str = ""  # state path or template for final output


# ── Tier 2: Control Flow
@dataclass
class BranchNode(DslNode):
    """Conditional routing (if / else / switch).

    Evaluates ``condition`` and routes via outgoing edges.
    The node stores *only* the condition — routing is fully
    determined by edges:

    - ``EdgeRole.THEN``  → target when condition is truthy
    - ``EdgeRole.ELSE``  → target when condition is falsy (explicit else)
    - ``EdgeRole.ELSE_FALLTHROUGH`` → target when condition is falsy (no else block)

    Example::

        # Python source:
        #   if data:
        #       report = analyst.analyze(data)
        #   else:
        #       report = analyst.fallback()

        BranchNode(id="br_1", condition="data")

        # Edges the builder creates:
        #   conditional("br_1", "analyze_id",  role=EdgeRole.THEN, condition="data")
        #   conditional("br_1", "fallback_id", role=EdgeRole.ELSE, condition="not (data)")

        # If there is no else block, the false-path edge uses ELSE_FALLTHROUGH
        # instead of ELSE, pointing to the next statement after the if.
    """

    type: NodeType = field(default=NodeType.BRANCH, init=False)

    condition: str = ""  # predicate expression


@dataclass
class ParallelNode(DslNode):
    """Execute branches concurrently and join results.

    The node stores *only* the join strategy and merge target.
    Fan-out is defined by outgoing edges with ``EdgeRole.BRANCH``.

    Example::

        ParallelNode(id="par_1", join=JoinStrategy.ALL, merge_to="$.combined")

        # Edges (one per concurrent branch):
        #   sequential("par_1", "branch_a_entry", role=EdgeRole.BRANCH)
        #   sequential("par_1", "branch_b_entry", role=EdgeRole.BRANCH)
    """

    type: NodeType = field(default=NodeType.PARALLEL, init=False)

    join: JoinStrategy = JoinStrategy.ALL
    merge_to: str = ""  # state path to write merged results


@dataclass
class LoopNode(DslNode):
    """Iterate over a collection with a body sub-graph.

    The node stores *only* the collection path, iteration variable, and
    safety cap.  Routing is defined by edges:

    - ``EdgeRole.BODY``      → entry of the loop body
    - ``EdgeRole.BACK_EDGE`` → tail of loop body back to this node (next iteration)
    - Sequential ``NONE``    → exit edge to the statement after the loop

    Example::

        # Python source:
        #   for item in items:
        #       result = analyst.process(item)

        LoopNode(id="loop_1", over="$.items", as_var="item")

        # Edges the builder creates:
        #   sequential("loop_1",    "process_id", role=EdgeRole.BODY)
        #   sequential("process_id", "loop_1",    role=EdgeRole.BACK_EDGE)
        #   sequential("loop_1",    "next_stmt",  role=EdgeRole.NONE)  # loop exit
    """

    type: NodeType = field(default=NodeType.LOOP, init=False)

    over: str = ""  # state path to an iterable
    as_var: str = "item"  # variable name for current element
    max_iterations: int = 1000  # safety cap


@dataclass
class SubflowNode(DslNode):
    """Delegate to another workflow by reference.

    Starts a child workflow execution with its own state, waits for
    completion, and maps the child's output back into parent state.

    Example:
        workflow_id = "risk_assessment_v2"
        inputs = {"portfolio": "$.portfolio"}
        output_map = {"risk_score": "$.child.risk_score"}
    """

    type: NodeType = field(default=NodeType.SUBFLOW, init=False)

    workflow_id: str = ""  # reference to another DslWorkflow
    input_map: dict[str, str] = field(default_factory=dict)  # parent → child state
    output_map: dict[str, str] = field(default_factory=dict)  # child → parent state


# ── Tier 3: Reliability
@dataclass
class GateNode(DslNode):
    """Human-in-the-loop approval gate.

    Pauses execution and waits for external approval (UI click, API
    call, webhook).  Routing is defined by edges:

    - ``EdgeRole.APPROVED`` → target when human approves
    - ``EdgeRole.DENIED``   → target when human denies (or on_timeout)

    Example::

        GateNode(id="gate_1", prompt="Approve trade?", on_timeout=GateTimeoutAction.DENY)

        # Edges:
        #   sequential("gate_1", "execute_trade", role=EdgeRole.APPROVED)
        #   sequential("gate_1", "cancel_trade",  role=EdgeRole.DENIED)
    """

    type: NodeType = field(default=NodeType.GATE, init=False)

    prompt: str = ""  # message shown to the human approver
    on_timeout: GateTimeoutAction = GateTimeoutAction.DENY


@dataclass
class CheckpointNode(DslNode):
    """Save execution state for resume / replay / debugging.

    Captures the full workflow state at this point.  If the executor
    crashes or is restarted, execution resumes from the last checkpoint.

    Example:
        checkpoint_label = "after_data_fetch"
    """

    type: NodeType = field(default=NodeType.CHECKPOINT, init=False)

    checkpoint_label: str = ""  # human-readable label for this snapshot


@dataclass
class FallbackNode(DslNode):
    """Try → catch → compensate pattern.

    The node itself has no fields — it is purely a control-flow
    junction.  Routing is defined by edges:

    - ``EdgeRole.TRY``        → primary execution path
    - ``EdgeRole.CATCH``      → error-handling path (runs if TRY fails)
    - ``EdgeRole.COMPENSATE`` → optional rollback path

    Example::

        FallbackNode(id="fb_1")

        # Edges:
        #   sequential("fb_1", "primary_action",  role=EdgeRole.TRY)
        #   error_edge("fb_1", "error_handler",   role=EdgeRole.CATCH)
        #   sequential("fb_1", "rollback_action", role=EdgeRole.COMPENSATE)
    """

    type: NodeType = field(default=NodeType.FALLBACK, init=False)


# ── Tier 4: Orchestration
@dataclass
class ReplanNode(DslNode):
    """Feed execution state back to the planner for dynamic re-routing.

    When the executor hits a ``ReplanNode``, it pauses, sends the
    current state to the planner (LLM + symbolic), receives a patched
    sub-graph, validates it, and merges it into the remaining workflow.

    This is Astra-specific — not found in n8n, Temporal, or LangGraph.

    Example:
        context = "$.execution_state"
        scope = ReplanScope.REMAINING
    """

    type: NodeType = field(default=NodeType.REPLAN, init=False)

    context: str = ""  # state path to send to planner
    scope: ReplanScope = ReplanScope.REMAINING
    max_replans: int = 2  # safety cap on re-plan depth


@dataclass
class TerminateNode(DslNode):
    """Stop the workflow with a final status.

    Used for early exits, error termination, or explicit success.
    Unlike ``RespondNode``, this does NOT produce a user-facing message —
    it's a control-flow primitive for "stop here."

    Example:
        status = TerminateStatus.FAILURE
        reason = "Risk threshold exceeded"
    """

    type: NodeType = field(default=NodeType.TERMINATE, init=False)

    status: TerminateStatus = TerminateStatus.SUCCESS
    reason: str = ""  # why the workflow stopped
    output: str = ""  # optional state path for final data


# ── Registry
NODE_TYPE_MAP: dict[NodeType, type[DslNode]] = {
    NodeType.ACTION: ActionNode,
    NodeType.TRANSFORM: TransformNode,
    NodeType.RESPOND: RespondNode,
    NodeType.BRANCH: BranchNode,
    NodeType.PARALLEL: ParallelNode,
    NodeType.LOOP: LoopNode,
    NodeType.SUBFLOW: SubflowNode,
    NodeType.GATE: GateNode,
    NodeType.CHECKPOINT: CheckpointNode,
    NodeType.FALLBACK: FallbackNode,
    NodeType.REPLAN: ReplanNode,
    NodeType.TERMINATE: TerminateNode,
}
"""Lookup table: NodeType enum → concrete dataclass."""
