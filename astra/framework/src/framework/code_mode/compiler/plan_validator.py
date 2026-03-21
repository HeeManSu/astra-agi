"""Plan validator — semantic checks on an assembled ExecutionPlan graph.

Runs *after* the builder, *before* the runtime.  Each check is a flat
function that appends to ``errors`` or ``warnings``.

Checks
------
1. branch_cardinality   - BranchNode has exactly 1 THEN + 1 ELSE/FALLTHROUGH
2. loop_cardinality     - LoopNode has exactly 1 BODY + ≥1 BACK_EDGE
3. terminal_edges       - RespondNode has 0 outgoing edges
4. dead_ends            - non-terminal nodes with 0 outgoing edges
5. tool_whitelist       - ActionNode.tool is in allowed set
6. self_loops           - no edge where source == target
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import traceback

from framework.code_mode.compiler.edges import EdgeRole
from framework.code_mode.compiler.nodes import NodeType
from framework.code_mode.compiler.schema import ExecutionPlan


log = logging.getLogger(__name__)


# ── Result ───────────────────────────────────────────────────────────────────


@dataclass
class PlanValidationResult:
    """Outcome of ``validate_plan``."""

    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Public API ───────────────────────────────────────────────────────────────


def validate_plan(
    workflow: ExecutionPlan,
    *,
    allowed_tools: set[str] | None = None,
) -> PlanValidationResult:
    """Run all semantic checks and return a ``PlanValidationResult``."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        _check_branch_cardinality(workflow, errors)
        _check_loop_cardinality(workflow, errors)
        _check_terminal_edges(workflow, errors)
        _check_dead_ends(workflow, warnings)
        _check_tool_whitelist(workflow, allowed_tools, warnings)
        _check_self_loops(workflow, errors)
    except Exception as exc:
        log.exception("validate_plan: unexpected error during validation")
        errors.append(f"Internal validation error: {exc}\n{traceback.format_exc()}")

    return PlanValidationResult(ok=len(errors) == 0, errors=errors, warnings=warnings)


# ── Individual checks ────────────────────────────────────────────────────────


def _check_branch_cardinality(wf: ExecutionPlan, errors: list[str]) -> None:
    """Every BranchNode must have exactly 1 THEN edge and a false-path.

    The false-path can be:
      - An explicit ELSE or ELSE_FALLTHROUGH edge, OR
      - A SEQUENTIAL edge (if-without-else: branch chains forward directly)

    EdgeRole.NONE does NOT count — that is an unclassified edge and
    must not silently satisfy the false-path requirement.
    """
    for node in wf.nodes:
        if node.type != NodeType.BRANCH:
            continue

        outgoing = wf.outgoing_edges(node.id)
        then_count = sum(1 for e in outgoing if e.role == EdgeRole.THEN)
        false_count = sum(
            1 for e in outgoing if e.role in (EdgeRole.ELSE, EdgeRole.ELSE_FALLTHROUGH)
        )

        if then_count != 1:
            errors.append(
                f"BranchNode '{node.label}' ({node.id}): expected 1 THEN edge, found {then_count}"
            )
        if false_count < 1:
            errors.append(
                f"BranchNode '{node.label}' ({node.id}): "
                f"expected >=1 false-path edge (ELSE/FALLTHROUGH/SEQUENTIAL), found 0"
            )


def _check_loop_cardinality(wf: ExecutionPlan, errors: list[str]) -> None:
    """Every LoopNode must have exactly 1 BODY edge and at least 1 BACK_EDGE."""
    for node in wf.nodes:
        if node.type != NodeType.LOOP:
            continue

        outgoing = wf.outgoing_edges(node.id)
        body_count = sum(1 for e in outgoing if e.role == EdgeRole.BODY)

        incoming = wf.incoming_edges(node.id)
        back_count = sum(1 for e in incoming if e.role == EdgeRole.BACK_EDGE)

        if body_count != 1:
            errors.append(
                f"LoopNode '{node.label}' ({node.id}): expected 1 BODY edge, found {body_count}"
            )
        if back_count < 1:
            errors.append(
                f"LoopNode '{node.label}' ({node.id}): expected ≥1 BACK_EDGE, found {back_count}"
            )


def _check_terminal_edges(wf: ExecutionPlan, errors: list[str]) -> None:
    """RespondNode must have zero outgoing edges."""
    terminal_types = {NodeType.RESPOND}
    for node in wf.nodes:
        if node.type not in terminal_types:
            continue

        outgoing = wf.outgoing_edges(node.id)
        if outgoing:
            targets = ", ".join(e.target for e in outgoing)
            errors.append(
                f"Terminal node '{node.label}' ({node.id}) has "
                f"{len(outgoing)} outgoing edge(s) -> [{targets}]"
            )


def _check_dead_ends(wf: ExecutionPlan, warnings: list[str]) -> None:
    """Non-terminal nodes with zero outgoing edges are suspicious."""
    terminal_types = {NodeType.RESPOND}
    for node in wf.nodes:
        if node.type in terminal_types:
            continue
        outgoing = wf.outgoing_edges(node.id)
        if not outgoing:
            warnings.append(
                f"Node '{node.label}' ({node.id}, {node.type.value}) "
                f"has no outgoing edges — possible dead end"
            )


def _check_tool_whitelist(
    wf: ExecutionPlan,
    allowed_tools: set[str] | None,
    warnings: list[str],
) -> None:
    """Warn if an ActionNode references a tool not in the whitelist."""
    if not allowed_tools:
        return
    for node in wf.nodes:
        if node.type != NodeType.ACTION:
            continue
        tool = getattr(node, "tool", None)
        if tool and tool not in allowed_tools:
            warnings.append(
                f"ActionNode '{node.label}' ({node.id}) uses tool "
                f"'{tool}' which is not in allowed_tools"
            )


def _check_self_loops(wf: ExecutionPlan, errors: list[str]) -> None:
    """No edge should have source == target."""
    for edge in wf.edges:
        if edge.source == edge.target:
            errors.append(f"Self-loop detected: edge '{edge.id}' ({edge.source} -> {edge.target})")
