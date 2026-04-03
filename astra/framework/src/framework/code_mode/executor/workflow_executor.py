"""
Workflow Executor — walks an ExecutionWorkflow graph and executes nodes.

Input:  ExecutionWorkflow (nodes, edges, entry, config) + tools: dict[str, Callable]
Output: ExecutionResult  (success, response, state, journal, error, duration_ms)

Flow:
    1. Start at workflow.entry
    2. Execute the current node based on its type
    3. Follow outgoing edges to find next node
    4. Repeat until RespondNode or no next node
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
import time
from typing import Any

from framework.code_mode.compiler.edges import Edge, EdgeType
from framework.code_mode.compiler.nodes import (
    ActionNode,
    BranchNode,
    LoopNode,
    NodeType,
    RespondNode,
    TransformNode,
)
from framework.code_mode.compiler.workflow_builder import ExecutionWorkflow, WorkFlowConfig


@dataclass
class WorkflowStep:
    """One entry per node execution — forms the full trace of a run."""

    node_id: str
    type: str
    label: str
    status: str  # "success" | "error"
    duration_ms: float
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ExecutionResult:
    """Final result of workflow execution."""

    success: bool
    response: Any = None
    state: dict[str, Any] = field(default_factory=dict)
    steps: list[WorkflowStep] = field(default_factory=list)
    error: str | None = None
    duration_ms: float = 0


@dataclass
class ExecutionContext:
    """Snapshot of runtime state passed to guardrail checks."""

    t_start: float
    config: WorkFlowConfig
    state: dict[str, Any]
    steps: list[WorkflowStep]
    visit_counts: dict[str, int]
    total_visits: int
    current_node_id: str


SAFE_BUILTINS: dict[str, Any] = {
    "len": len,
    "range": range,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "sorted": sorted,
    "reversed": reversed,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "any": any,
    "all": all,
    "round": round,
    "isinstance": isinstance,
    "type": type,
    "True": True,
    "False": False,
    "None": None,
}


def evaluate_expression(expression: str, state: dict[str, Any]) -> Any:
    """Safely evaluate a Python expression using workflow state as the namespace.

    How it works:
        1. The expression string originates from ``ast.unparse()`` in the
           workflow builder, so it is always syntactically valid Python.
        2. Variable names inside the expression correspond to keys in ``state``
           (e.g. "len(results) + offset" expects ``results`` and ``offset`` in state).
        3. ``__builtins__`` is set to ``{}`` — this blocks access to dangerous
           functions like ``open()``, ``exec()``, ``__import__()``, etc.
        4. Only whitelisted pure functions from ``SAFE_BUILTINS`` are available.

    Args:
        expression: A Python expression string (from ast.unparse).
        state:      The current workflow state dict — keys become variable names.

    Returns:
        The evaluated result of the expression.

    Raises:
        NameError:   If the expression references a variable not in state or SAFE_BUILTINS.
        SyntaxError: If the expression is somehow malformed.
    """
    namespace = {**SAFE_BUILTINS, **state}
    return eval(expression, {"__builtins__": {}}, namespace)


def _execute_loop(
    node: LoopNode,
    state: dict[str, Any],
    loop_state: dict[str, tuple[list, int]],
) -> bool:
    """Initialize or advance a loop iterator. Returns True if items remain."""

    if node.id not in loop_state:
        # First visit — resolve the collection expression
        collection = evaluate_expression(node.over, state)
        items = list(collection)
        loop_state[node.id] = (items, 0)
    else:
        # Re-visit — advance index
        items, idx = loop_state[node.id]
        loop_state[node.id] = (items, idx + 1)

    items, idx = loop_state[node.id]

    if idx >= len(items):
        # Exhausted - clean up
        del loop_state[node.id]
        return False

    if idx >= node.max_iterations:
        del loop_state[node.id]
        return False

    state[node.as_var] = items[idx]
    return True


def _execute_branch(node: BranchNode, state: dict[str, Any]) -> bool:
    """Evaluate branch condition, return True/False."""
    return bool(evaluate_expression(node.condition, state))


def _execute_respond(node: RespondNode, state: dict[str, Any]) -> Any:
    """Evaluate the response message expression and return the result."""
    return evaluate_expression(node.message, state)


def _execute_transform(node: TransformNode, state: dict[str, Any]) -> dict[str, Any]:
    """Evaluate expression and write result to state[assign_to]."""

    result = evaluate_expression(node.expression, state)
    if node.assign_to:
        state[node.assign_to] = result

    return {"expression": node.expression, "result": result}


async def _execute_action(
    node: ActionNode, state: dict[str, Any], tools: dict[str, Callable]
) -> dict[str, Any]:
    """Resolve input expressions, call the tool, write result to state."""

    tool_fn = tools.get(node.tool)
    if tool_fn is None:
        raise ValueError(f"Tool not found: '{node.tool}'")

    # Resolve each input expression against current state
    resolved_args: dict[str, Any] = {}
    for param_name, expr in node.inputs.items():
        resolved_args[param_name] = evaluate_expression(expr, state)

    # Call the tool — support both sync and async callables
    if asyncio.iscoroutinefunction(tool_fn):
        result = await tool_fn(**resolved_args)
    else:
        result = tool_fn(**resolved_args)

    # Write result to state if an output binding exists
    output_var = node.outputs.get("result")
    if output_var:
        state[output_var] = result

    return {"inputs": resolved_args, "outputs": result}


def find_next_node(
    node_type: NodeType,
    node_id: str,
    edge_index: dict[str, list[Edge]],
    branch_result: bool | None = None,
    loop_has_items: bool | None = None,
) -> str | None:
    """Follow outgoing edges from a node to determine the next node to execute.

    Rules:
        ActionNode / TransformNode  → follow SEQUENTIAL
        BranchNode                  → BRANCH_IF if true, BRANCH_ELSE or BRANCH_DEFAULT if false
        LoopNode                    → LOOP_BODY if items remain, SEQUENTIAL if exhausted
        RespondNode                 → None (halt)
    """
    if node_type == NodeType.RESPOND:
        return None

    outgoing = edge_index.get(node_id, [])

    if node_type in (NodeType.ACTION, NodeType.TRANSFORM):
        for edge in outgoing:
            if edge.type == EdgeType.SEQUENTIAL:
                return edge.target
        return None

    if node_type == NodeType.BRANCH:
        if branch_result:
            for edge in outgoing:
                if edge.type == EdgeType.BRANCH_IF:
                    return edge.target
        else:
            for edge in outgoing:
                if edge.type == EdgeType.BRANCH_ELSE:
                    return edge.target
            for edge in outgoing:
                if edge.type == EdgeType.BRANCH_DEFAULT:
                    return edge.target
        return None

    if node_type == NodeType.LOOP:
        if loop_has_items:
            for edge in outgoing:
                if edge.type == EdgeType.LOOP_BODY:
                    return edge.target
        else:
            for edge in outgoing:
                if edge.type == EdgeType.SEQUENTIAL:
                    return edge.target
        return None

    return None


def check_guardrails(ctx: ExecutionContext) -> ExecutionResult | None:
    """Return an error ExecutionResult if any guardrail is breached, else None."""
    elapsed = time.monotonic() - ctx.t_start

    if elapsed > ctx.config.max_execution_seconds:
        return ExecutionResult(
            success=False,
            state=ctx.state,
            steps=ctx.steps,
            error=f"Timeout: exceeded {ctx.config.max_execution_seconds}s",
            duration_ms=elapsed * 1000,
        )

    if ctx.total_visits > ctx.config.max_nodes:
        return ExecutionResult(
            success=False,
            state=ctx.state,
            steps=ctx.steps,
            error=f"Max total node visits exceeded ({ctx.config.max_nodes})",
            duration_ms=elapsed * 1000,
        )

    if ctx.visit_counts[ctx.current_node_id] > ctx.config.max_visits_per_node:
        return ExecutionResult(
            success=False,
            state=ctx.state,
            steps=ctx.steps,
            error=f"Node '{ctx.current_node_id}' exceeded max visits ({ctx.config.max_visits_per_node})",
            duration_ms=elapsed * 1000,
        )

    return None


async def run_workflow(workflow: ExecutionWorkflow, tools: dict[str, Callable]) -> ExecutionResult:
    """Walk the ExecutionWorkflow graph, execute every node, and return the result.

    Algorithm:
        1. Build lookup indices (node_map, edge_index).
        2. Initialize cursor at workflow.entry.
        3. Loop:
            a. Check guardrails (timeout, visit counts).
            b. Look up current node.
            c. Dispatch to the appropriate handler.
            d. Record a WorkflowStep.
            e. Resolve the next node via find_next_node.
        4. Return ExecutionResult with final state, response, steps, and duration.
    """

    t_start = time.monotonic()
    config = workflow.config

    # Build lookup indices for O(1) access
    node_map = {node.id: node for node in workflow.nodes}
    edge_index: dict[str, list[Edge]] = defaultdict(list)
    for edge in workflow.edges:
        edge_index[edge.source].append(edge)

    # Runtime state
    state: dict[str, Any] = {}
    steps: list[WorkflowStep] = []
    loop_state: dict[str, tuple[list, int]] = {}  # node_id → (items, current_index)
    visit_counts: dict[str, int] = defaultdict(int)
    total_visits = 0
    response = None

    cursor: str | None = workflow.entry

    while cursor is not None:
        # Track visits
        total_visits += 1
        visit_counts[cursor] += 1

        # Check guardrails before executing
        guardrail_failure = check_guardrails(
            ExecutionContext(
                t_start=t_start,
                config=config,
                state=state,
                steps=steps,
                visit_counts=visit_counts,
                total_visits=total_visits,
                current_node_id=cursor,
            )
        )
        if guardrail_failure is not None:
            return guardrail_failure

        # Look up the current node
        node = node_map.get(cursor)
        if node is None:
            return ExecutionResult(
                success=False,
                state=state,
                steps=steps,
                error=f"Node not found: '{cursor}'",
                duration_ms=(time.monotonic() - t_start) * 1000,
            )

        # Prepare the step entry (timing starts here)
        t_node = time.monotonic()
        step = WorkflowStep(
            node_id=node.id,
            type=node.type.value,
            label=node.label,
            status="success",
            duration_ms=0,
        )

        branch_result: bool | None = None
        loop_has_items: bool | None = None

        try:
            if isinstance(node, ActionNode):
                meta = await _execute_action(node, state, tools)
                step.inputs = meta["inputs"]
                step.outputs = meta["outputs"]

            elif isinstance(node, TransformNode):
                meta = _execute_transform(node, state)
                step.outputs = meta

            elif isinstance(node, BranchNode):
                branch_result = _execute_branch(node, state)
                step.outputs = {"condition": node.condition, "result": branch_result}

            elif isinstance(node, RespondNode):
                response = _execute_respond(node, state)
                step.outputs = {"response": response}

            elif isinstance(node, LoopNode):
                loop_has_items = _execute_loop(node, state, loop_state)
                step.outputs = {"has_items": loop_has_items, "current": state.get(node.as_var)}

        except Exception as exc:
            step.status = "error"
            step.error = f"{type(exc).__name__}: {exc}"
            step.duration_ms = (time.monotonic() - t_node) * 1000
            steps.append(step)
            return ExecutionResult(
                success=False,
                state=state,
                steps=steps,
                error=step.error,
                duration_ms=(time.monotonic() - t_start) * 1000,
            )

        # Record the step
        step.duration_ms = (time.monotonic() - t_node) * 1000
        steps.append(step)

        # Stop on RespondNode — we have our answer
        if isinstance(node, RespondNode):
            break

        # Advance to the next node
        cursor = find_next_node(
            node_type=node.type,
            node_id=node.id,
            edge_index=edge_index,
            branch_result=branch_result,
            loop_has_items=loop_has_items,
        )

    return ExecutionResult(
        success=True,
        response=response,
        state=state,
        steps=steps,
        duration_ms=(time.monotonic() - t_start) * 1000,
    )
