"""
WorkflowRunner — deterministic DSL execution engine.

Public API:
    result = await run_plan(workflow, initial_state, tools)

The runner owns:
  - The main execution loop (cursor → dispatch → journal → advance)
  - Edge-based next-node resolution (_resolve_next)
  - Timeout guard (workflow-level max_execution_seconds)
  - Max-nodes guard (infinite loop prevention)
  - Journal building (one JournalEntry per node)

It does NOT own:
  - Node business logic   → dispatcher.py
  - State expressions     → dispatcher._resolve / _write_outputs
"""

from __future__ import annotations

from collections.abc import Callable
import logging
import time
import traceback
from typing import Any

from framework.code_mode.compiler.edges import EdgeRole
from framework.code_mode.compiler.nodes import NodeType
from framework.code_mode.compiler.schema import ExecutionPlan
from framework.code_mode.executor.dispatcher import dispatch
from framework.code_mode.executor.models import (
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    JournalEntry,
    NodeResult,
)


log = logging.getLogger(__name__)


# ── Edge resolution ---------------------------------------------------------


def _resolve_next(ctx: ExecutionContext) -> str | None:
    """Determine the next node to execute based on outgoing edges."""
    workflow = ctx.workflow
    node_id = ctx.current_node_id
    node = workflow.get_node(node_id)

    if node is None:
        return None

    edges = workflow.outgoing_edges(node_id)
    if not edges:
        return None  # natural terminal

    # ── BranchNode: THEN or ELSE/ELSE_FALLTHROUGH
    if node.type == NodeType.BRANCH:
        cond_result = ctx.state.get("__branch_result__", False)
        for edge in edges:
            if cond_result and edge.role == EdgeRole.THEN:
                return edge.target
            if not cond_result and edge.role in (EdgeRole.ELSE, EdgeRole.ELSE_FALLTHROUGH):
                return edge.target
        # No matching THEN/ELSE edge — graph is malformed.  Fail loudly.
        ctx.state["__next_resolution_error__"] = (
            f"Malformed branch graph at node '{node_id}': "
            f"missing {'THEN' if cond_result else 'ELSE/ELSE_FALLTHROUGH'} edge"
        )
        return None

    # ── LoopNode: BODY while items remain, sequential exit when exhausted
    if node.type == NodeType.LOOP:
        items_key = f"__loop_{node_id}_items"
        idx_key = f"__loop_{node_id}_idx"
        items = ctx.state.get(items_key, [])
        idx = ctx.state.get(idx_key, 0)
        if idx < len(items):
            body_edge = next((e for e in edges if e.role == EdgeRole.BODY), None)
            if body_edge:
                return body_edge.target
            ctx.state["__next_resolution_error__"] = (
                f"Malformed loop graph at node '{node_id}': missing BODY edge while loop has items"
            )
            return None
        else:
            exit_edge = next((e for e in edges if e.role == EdgeRole.NONE), None)
            if exit_edge:
                return exit_edge.target
            for edge in edges:
                if edge.role not in (EdgeRole.BODY, EdgeRole.BACK_EDGE):
                    return edge.target
            ctx.state["__next_resolution_error__"] = (
                f"Malformed loop graph at node '{node_id}': missing loop exit edge"
            )
            return None

    # ── Default: first sequential edge
    seq = next((e for e in edges if e.role == EdgeRole.NONE), None)
    if seq:
        return seq.target
    ctx.state["__next_resolution_error__"] = (
        f"Malformed graph at node '{node_id}': missing sequential edge for node type '{node.type.value}'"
    )
    return None


# ── Journal helper ----------------------------------------------------------


def _journal(node, result, started_at: float, inputs: dict[str, Any]) -> JournalEntry:
    elapsed = (time.monotonic() - started_at) * 1000  # ms
    # Extract token usage if the tool reported it, then strip from outputs so
    # __token_usage__ doesn't leak into workflow state.
    outputs = dict(result.outputs)  # shallow copy — don't mutate result
    token_usage: dict[str, int] = {}
    raw_usage = outputs.pop("__token_usage__", None)
    if isinstance(raw_usage, dict):
        token_usage = {k: int(v) for k, v in raw_usage.items() if isinstance(v, (int, float))}
    return JournalEntry(
        node_id=node.id,
        node_type=node.type.value,
        label=node.label,
        status=result.status,
        started_at=started_at,
        duration_ms=elapsed,
        inputs=inputs,
        outputs=outputs,
        error=result.error,
        token_usage=token_usage,
    )


# ── Main loop ---------------------------------------------------------------


async def run_plan(
    workflow: ExecutionPlan,
    initial_state: dict[str, Any],
    tools: dict[str, Callable],
) -> ExecutionResult:
    """Run a compiled ExecutionPlan deterministically.

    Args:
        workflow:          A validated ExecutionPlan.
        initial_state:     Caller-supplied state values.
        tools:             Tool registry: {"agent.method": callable, ...}

    Returns:
        ExecutionResult with ok, status, response, state, journal.
    """
    start = time.monotonic()
    cfg = workflow.config

    # Validate entry
    if not workflow.entry or workflow.get_node(workflow.entry) is None:
        return ExecutionResult(
            ok=False,
            status=ExecutionStatus.FAILED,
            response=None,
            state=initial_state,
            journal=[],
            error=f"Invalid or missing entry node: '{workflow.entry}'",
            duration_ms=0.0,
        )

    start_state = dict(initial_state)
    entry = workflow.entry

    ctx = ExecutionContext(
        workflow=workflow,
        state=start_state,
        journal=[],
        current_node_id=entry,
        visited_count={},
        status=ExecutionStatus.RUNNING,
        start_time=start,
    )

    log.info("run_plan started: %s", workflow.summary())

    while ctx.status == ExecutionStatus.RUNNING:
        # ── Timeout guard
        if ctx.elapsed_seconds > cfg.max_execution_seconds:
            ctx.status = ExecutionStatus.FAILED
            error_msg = f"Workflow timeout: exceeded {cfg.max_execution_seconds}s"
            log.warning(error_msg)
            return _build_result(ctx, ok=False, error=error_msg, start=start)

        # ── Max total-visits guard (prevents runaway workflows)
        if len(ctx.journal) >= cfg.max_nodes:
            ctx.status = ExecutionStatus.FAILED
            error_msg = (
                f"Max total node visits exceeded ({cfg.max_nodes}). "
                f"Increase PlanConfig.max_nodes for large loop workflows."
            )
            log.warning(error_msg)
            return _build_result(ctx, ok=False, error=error_msg, start=start)

        # ── Fetch current node
        node = ctx.workflow.get_node(ctx.current_node_id)
        if node is None:
            ctx.status = ExecutionStatus.FAILED
            error_msg = f"Node '{ctx.current_node_id}' not found in workflow graph"
            log.error(error_msg)
            return _build_result(ctx, ok=False, error=error_msg, start=start)

        ctx.visit(node.id)
        log.debug("executing node: %s (%s)", node.id, node.type.value)

        # ── Per-node visit cap (catches true infinite loops on a single node)
        if cfg.max_visits_per_node > 0:
            node_visits = ctx.visited_count.get(node.id, 0)
            if node_visits > cfg.max_visits_per_node:
                ctx.status = ExecutionStatus.FAILED
                error_msg = (
                    f"Node '{node.id}' visited {node_visits} times "
                    f"(max_visits_per_node={cfg.max_visits_per_node}). "
                    f"Probable infinite loop."
                )
                log.warning(error_msg)
                return _build_result(ctx, ok=False, error=error_msg, start=start)

        # ── Capture inputs snapshot for the journal (before handler modifies state)
        from framework.code_mode.executor.dispatcher import _resolve_inputs

        inputs_snapshot = _resolve_inputs(node, ctx.state)

        # ── Dispatch node handler
        node_started = time.monotonic()
        try:
            result = await dispatch(node, ctx, tools)
        except Exception as exc:
            log.exception(
                "run_plan: unhandled exception dispatching node '%s' (%s)",
                node.id,
                node.type.value,
            )
            result = NodeResult(
                status="error",
                error=f"Unhandled error in node '{node.id}' ({node.type.value}): {exc}\n{traceback.format_exc()}",
            )

        # ── Write journal entry
        journal_entry = _journal(node, result, node_started, inputs_snapshot)
        ctx.journal.append(journal_entry)

        # ── State size guard (prevents silent memory bloat)
        if cfg.state_size_limit_mb > 0:
            import json as _json

            try:
                state_bytes = len(_json.dumps(ctx.state, default=str).encode())
                limit_bytes = cfg.state_size_limit_mb * 1024 * 1024
                if state_bytes >= limit_bytes:
                    ctx.status = ExecutionStatus.FAILED
                    error_msg = (
                        f"State size limit exceeded: {state_bytes / 1024 / 1024:.1f} MB "
                        f"> {cfg.state_size_limit_mb} MB limit after node '{node.id}'"
                    )
                    log.error(error_msg)
                    return _build_result(ctx, ok=False, error=error_msg, start=start)
                elif state_bytes >= limit_bytes * 0.8:
                    log.warning(
                        "State size warning: %.1f MB (%.0f%% of %d MB limit) after node '%s'",
                        state_bytes / 1024 / 1024,
                        state_bytes / limit_bytes * 100,
                        cfg.state_size_limit_mb,
                        node.id,
                    )
            except Exception:
                log.debug(
                    "run_plan: state size check failed after node '%s'", node.id, exc_info=True
                )

        # ── Handle error
        if result.status in ("error", "timeout"):
            ctx.status = ExecutionStatus.FAILED
            log.error("node %s failed: %s", node.id, result.error)
            return _build_result(ctx, ok=False, error=result.error, start=start)

        # ── Handle override signals
        if result.override_next == "__COMPLETED__":
            ctx.status = ExecutionStatus.COMPLETED
            break
        if result.override_next == "__FAILED__":
            ctx.status = ExecutionStatus.FAILED
            return _build_result(ctx, ok=False, error=result.error, start=start)

        # ── Resolve next node via edges
        next_id = _resolve_next(ctx)
        if next_id is None:
            resolution_error = ctx.state.pop("__next_resolution_error__", None)
            if resolution_error:
                ctx.status = ExecutionStatus.FAILED
                return _build_result(ctx, ok=False, error=str(resolution_error), start=start)
            # No outgoing edge — natural end of graph
            ctx.status = ExecutionStatus.COMPLETED
            break

        ctx.current_node_id = next_id

    log.info(
        "run_plan finished: status=%s nodes=%d duration=%.1fms",
        ctx.status.value,
        len(ctx.journal),
        (time.monotonic() - start) * 1000,
    )
    return _build_result(ctx, ok=(ctx.status == ExecutionStatus.COMPLETED), start=start)


# ── Result builder ----------------------------------------------------------


def _build_result(
    ctx: ExecutionContext,
    ok: bool,
    start: float,
    error: str | None = None,
) -> ExecutionResult:
    """Assemble the final ExecutionResult from context."""
    # Sum token usage across all journal entries (prompt_tokens, completion_tokens, etc.)
    total_tokens: dict[str, int] = {}
    for entry in ctx.journal:
        for key, count in entry.token_usage.items():
            total_tokens[key] = total_tokens.get(key, 0) + count
    return ExecutionResult(
        ok=ok,
        status=ctx.status,
        response=ctx.state.get("__response__"),
        state=ctx.state,
        journal=ctx.journal,
        error=error,
        duration_ms=(time.monotonic() - start) * 1000,
        total_token_usage=total_tokens,
    )
