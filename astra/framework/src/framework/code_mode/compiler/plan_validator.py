from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import traceback

from framework.code_mode.compiler.edges import EdgeType
from framework.code_mode.compiler.nodes import NodeType
from framework.code_mode.compiler.workflow_builder import ExecutionWorkflow


@dataclass
class PlanValidationResult:
    success: bool
    errors: list[str] = field(default_factory=list)


def _check_self_loops(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """No edge should have source == target."""
    errors.extend(
        f"Self-loop detected: edge '{edge.id}' ({edge.source} -> {edge.target})"
        for edge in workflow.edges
        if edge.source == edge.target
    )


def _check_branch_if_edge_condition(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """BRANCH_IF edges must have a non-empty condition."""
    errors.extend(
        f"BRANCH_IF edge '{edge.id}' has no condition"
        for edge in workflow.edges
        if edge.type == EdgeType.BRANCH_IF and not edge.condition
    )


def _check_ambiguous_sequential(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """Non-branch/non-loop nodes must not have more than 1 outgoing edge."""
    for node in workflow.nodes:
        if node.type in (NodeType.BRANCH, NodeType.LOOP, NodeType.RESPOND):
            continue
        outgoing = [e for e in workflow.edges if e.source == node.id]
        if len(outgoing) > 1:
            errors.append(
                f"Node '{node.id}' ({node.type.value}) has {len(outgoing)} outgoing edges "
                f"— expected at most 1"
            )


def _check_action_has_tool(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """Every ActionNode must have a non-empty tool name."""
    errors.extend(
        f"ActionNode '{node.id}' has no tool name"
        for node in workflow.nodes
        if node.type == NodeType.ACTION and not getattr(node, "tool", "")
    )


def _check_branch_has_condition(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """Every BranchNode must have a non-empty condition."""
    errors.extend(
        f"BranchNode '{node.id}' has no condition"
        for node in workflow.nodes
        if node.type == NodeType.BRANCH and not getattr(node, "condition", "")
    )


def _check_loop_has_over(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """Every LoopNode must have a non-empty collection to iterate over."""
    errors.extend(
        f"LoopNode '{node.id}' has no collection to iterate over"
        for node in workflow.nodes
        if node.type == NodeType.LOOP and not getattr(node, "over", "")
    )


def _check_has_respond_node(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """Graph must contain at least one RespondNode."""
    if not any(node.type == NodeType.RESPOND for node in workflow.nodes):
        errors.append("Workflow must have at least one RespondNode")


def _check_terminal_no_outgoing(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """RespondNode must have zero outgoing edges."""
    for node in workflow.nodes:
        if node.type != NodeType.RESPOND:
            continue
        outgoing = [e for e in workflow.edges if e.source == node.id]
        if outgoing:
            errors.append(
                f"RespondNode '{node.id}' has {len(outgoing)} outgoing edge(s) — terminal nodes must have none"
            )


def _check_dead_ends(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """Non-terminal nodes with zero outgoing edges are dead ends."""
    for node in workflow.nodes:
        if node.type == NodeType.RESPOND:
            continue
        outgoing = [e for e in workflow.edges if e.source == node.id]
        if not outgoing:
            errors.append(
                f"Node '{node.id}' ({node.type.value}) has no outgoing edges — possible dead end"
            )


def _check_loop_cardinality(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """LoopNode must have exactly 1 LOOP_BODY outgoing and ≥1 LOOP_BACK incoming."""
    for node in workflow.nodes:
        if node.type != NodeType.LOOP:
            continue

        outgoing = [e for e in workflow.edges if e.source == node.id]
        body_count = sum(1 for e in outgoing if e.type == EdgeType.LOOP_BODY)

        incoming = [e for e in workflow.edges if e.target == node.id]
        back_count = sum(1 for e in incoming if e.type == EdgeType.LOOP_BACK)

        if body_count != 1:
            errors.append(f"LoopNode '{node.id}': expected 1 LOOP_BODY edge, found {body_count}")
        if back_count < 1:
            errors.append(f"LoopNode '{node.id}': expected ≥1 LOOP_BACK edge, found {back_count}")


def _check_branch_cardinality(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """BranchNode must have exactly 1 BRANCH_IF and exactly 1 BRANCH_ELSE or BRANCH_DEFAULT."""

    for node in workflow.nodes:
        if node.type != NodeType.BRANCH:
            continue

    outgoing = [edge for edge in workflow.edges if edge.source == node.id]
    true_count = sum(1 for edge in outgoing if edge.type == EdgeType.BRANCH_IF)
    false_count = sum(
        1 for edge in outgoing if edge.type in (EdgeType.BRANCH_ELSE, EdgeType.BRANCH_DEFAULT)
    )

    if true_count != 1:
        errors.append(f"BranchNode '{node.id}': expected 1 BRANCH_IF edge, found {true_count}")
    if false_count != 1:
        errors.append(
            f"BranchNode '{node.id}': expected 1 BRANCH_ELSE or BRANCH_DEFAULT edge, found {false_count}"
        )


def _check_reachability(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """Every node should be reachable from the entry node."""

    visited: set[str] = set()
    queue: deque[str] = deque([workflow.entry])
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(
            edge.target
            for edge in workflow.edges
            if edge.source == current and edge.target not in visited
        )

    errors.extend(
        f"Node '{node.id}' is not reachable from the entry node"
        for node in workflow.nodes
        if node.id not in visited
    )


def _check_edge_references(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """Every edge source and target must reference an existing node."""

    node_ids = {node.id for node in workflow.nodes}
    for edge in workflow.edges:
        if edge.source not in node_ids:
            errors.append(f"Edge '{edge.id}' references unknown source '{edge.source}'")
        if edge.target not in node_ids:
            errors.append(f"Edge '{edge.id}' references unknown target '{edge.target}'")


def _check_duplicate_node_ids(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """All node IDs must be unique."""
    seen: set[str] = set()
    for node in workflow.nodes:
        if node.id in seen:
            errors.append(f"Duplicate node ID: '{node.id}'")
        seen.add(node.id)


def _check_entry_exists(workflow: ExecutionWorkflow, errors: list[str]) -> None:
    """Entry must be non-empty and reference a real node."""
    node_ids = {node.id for node in workflow.nodes}
    if not workflow.entry:
        errors.append("No entry node specified")
    elif workflow.entry not in node_ids:
        errors.append(f"Entry node '{workflow.entry}' does not exist in the graph")


def validate_plan(
    workflow: ExecutionWorkflow,
) -> PlanValidationResult:
    """Run all semantic checks and return a PlanValidationResult."""
    errors: list[str] = []

    try:
        # Graph Structure Checks
        _check_entry_exists(workflow, errors)
        _check_duplicate_node_ids(workflow, errors)
        _check_edge_references(workflow, errors)
        _check_reachability(workflow, errors)

        # Control Flow Cardinality
        _check_branch_cardinality(workflow, errors)
        _check_loop_cardinality(workflow, errors)

        # Terminal & Dead Ends
        _check_has_respond_node(workflow, errors)
        _check_terminal_no_outgoing(workflow, errors)
        _check_dead_ends(workflow, errors)

        # Node Data Integrity
        _check_action_has_tool(workflow, errors)
        _check_branch_has_condition(workflow, errors)
        _check_loop_has_over(workflow, errors)

        # Edge Integrity
        _check_self_loops(workflow, errors)
        _check_branch_if_edge_condition(workflow, errors)
        _check_ambiguous_sequential(workflow, errors)

    except Exception as exc:
        errors.append(f"Internal validation error: {exc}\n{traceback.format_exc()}")

    return PlanValidationResult(success=len(errors) == 0, errors=errors)
