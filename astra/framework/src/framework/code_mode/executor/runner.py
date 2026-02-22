"""
WorkflowRunner — deterministic DSL execution engine, Phase 1.

Public API:
    result = await run_workflow(workflow, initial_state, tools)

The runner owns:
  - The main execution loop (cursor → dispatch → journal → advance)
  - Edge-based next-node resolution (_resolve_next)
  - Retry logic (exponential backoff per RetryConfig)
  - Timeout guard (workflow-level max_execution_seconds)
  - Max-nodes guard (infinite loop prevention)
  - Journal building (one JournalEntry per node)

It does NOT own:
  - Node business logic   → dispatcher.py
  - State expressions     → dispatcher._resolve / _write_outputs
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
import time
from typing import Any

from framework.code_mode.compiler.edges import EdgeRole
from framework.code_mode.compiler.nodes import (
    NodeType,
    RetryConfig,
)
from framework.code_mode.compiler.schema import DslWorkflow
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

    # ── GateNode: APPROVED or DENIED based on approval result stashed by handle_gate
    if node.type == NodeType.GATE:
        approved = ctx.state.pop(f"__gate_{node_id}_approved__", False)
        for edge in edges:
            if approved and edge.role == EdgeRole.APPROVED:
                return edge.target
            if not approved and edge.role == EdgeRole.DENIED:
                return edge.target
        ctx.state["__next_resolution_error__"] = (
            f"Malformed gate graph at node '{node_id}': "
            f"missing {'APPROVED' if approved else 'DENIED'} edge"
        )
        return None  # no matching edge

    # ── ParallelNode / FallbackNode: sub-paths run inside handler; follow sequential exit
    if node.type in (NodeType.PARALLEL, NodeType.FALLBACK):
        exit_edge = next((e for e in edges if e.role == EdgeRole.NONE), None)
        if exit_edge:
            return exit_edge.target
        ctx.state["__next_resolution_error__"] = (
            f"Malformed control graph at node '{node_id}': missing sequential exit edge"
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


# ── Retry helpers -----------------------------------------------------------


def _should_retry(retry: RetryConfig | None, attempt: int) -> bool:
    """Return True if another retry is allowed."""
    if retry is None:
        return False
    return attempt < (retry.max_attempts - 1)


async def _backoff(retry: RetryConfig, attempt: int) -> None:
    """Sleep before the next retry attempt."""
    delay = retry.initial_delay_seconds
    if retry.backoff == "exponential":
        delay = min(retry.initial_delay_seconds * (2**attempt), retry.max_delay_seconds)
    elif retry.backoff == "linear":
        delay = min(retry.initial_delay_seconds * (attempt + 1), retry.max_delay_seconds)
    await asyncio.sleep(delay)


# ── Sub-branch runner (used by ParallelNode + FallbackNode) ----------------


async def _run_branch(
    workflow: DslWorkflow,
    start_node_id: str,
    state: dict[str, Any],
    tools: dict[str, Callable],
    *,
    max_nodes: int = 50,
) -> tuple[dict[str, Any], list[JournalEntry], str | None]:
    """Walk a sub-path from start_node_id until no outgoing sequential edge.

    Used by handle_parallel and handle_fallback for isolated sub-executions.
    Nested GateNode / ParallelNode / FallbackNode are not supported here (Phase 3).

    Returns:
        (final_state, journal_entries, error_or_None)
    """
    from framework.code_mode.executor.dispatcher import (
        _resolve_inputs,  # avoid circular at module level
    )

    branch_journal: list[JournalEntry] = []
    node_id: str | None = start_node_id
    steps = 0

    while node_id is not None and steps < max_nodes:
        node = workflow.get_node(node_id)
        if node is None:
            return state, branch_journal, f"Branch node '{node_id}' not found in graph"

        # Minimal ctx sharing the same state dict (mutations are reflected in the returned state)
        ctx = ExecutionContext(
            workflow=workflow,
            state=state,
            journal=branch_journal,
            current_node_id=node_id,
            visited_count={},
            status=ExecutionStatus.RUNNING,
            start_time=time.monotonic(),
        )

        inputs_snap = _resolve_inputs(node, state)
        node_started = time.monotonic()
        # gate_fn=None, run_branch=None — nested phase-2 nodes unsupported inside branches
        result = await dispatch(node, ctx, tools)
        branch_journal.append(_journal(node, result, node_started, inputs_snap))

        if result.status in ("error", "timeout", "waiting"):
            errmsg = result.error or f"Node '{node_id}' returned '{result.status}'"
            return state, branch_journal, errmsg

        if result.override_next == "__FAILED__":
            return state, branch_journal, result.error or "Branch terminated with FAILED"
        if result.override_next == "__COMPLETED__":
            break

        # Advance: follow sequential edge, skip structural roles
        edges = workflow.outgoing_edges(node_id)
        if node.type == NodeType.BRANCH:
            cond = state.get("__branch_result__", False)
            next_edge = next(
                (
                    e
                    for e in edges
                    if (cond and e.role == EdgeRole.THEN)
                    or (not cond and e.role in (EdgeRole.ELSE, EdgeRole.ELSE_FALLTHROUGH))
                ),
                None,
            )
        else:
            next_edge = next(
                (
                    e
                    for e in edges
                    if e.role
                    not in (
                        EdgeRole.BRANCH,
                        EdgeRole.BACK_EDGE,
                        EdgeRole.TRY,
                        EdgeRole.CATCH,
                        EdgeRole.COMPENSATE,
                        EdgeRole.BODY,
                    )
                ),
                None,
            )

        node_id = next_edge.target if next_edge else None
        steps += 1

    return state, branch_journal, None


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


# ── Main loop
async def run_workflow(
    workflow: DslWorkflow,
    initial_state: dict[str, Any],
    tools: dict[str, Callable],
    *,
    gate_fn: Callable | None = None,
    # Phase 3 — persistence
    store: Any | None = None,  # WorkflowInstanceStore | None
    agent_id: str = "",
    conversation_id: str = "",
    workflow_resolver: Callable | None = None,  # plan_id -> DslWorkflow | None
    resume_from: Any | None = None,  # WorkflowInstance | None (crash recovery)
    replan_fn: Callable | None = None,  # Phase 4: async (context, workflow) -> DslWorkflow | None
    # Cancellation
    cancel_event: asyncio.Event | None = None,  # set() from outside to cancel immediately
) -> ExecutionResult:
    """Run a compiled DslWorkflow deterministically.

    Args:
        workflow:          A validated DslWorkflow.
        initial_state:     Caller-supplied state values.
        tools:             Tool registry: {"agent.method": callable, ...}
        gate_fn:           Optional async (node_id, prompt) -> bool for GateNode approval.
        store:             Optional WorkflowInstanceStore for persistence.
        agent_id:          Owning agent ID (stored in WorkflowInstance).
        conversation_id:   Conversation context (stored in WorkflowInstance).
        workflow_resolver: Callable(plan_id) -> DslWorkflow | None for SubflowNode.
        resume_from:       WorkflowInstance to resume from (crash recovery).

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

    # Determine start state and entry cursor
    if resume_from is not None:
        start_state = (
            dict(resume_from.state_snapshot) if resume_from.state_snapshot else dict(initial_state)
        )
        entry = resume_from.current_node_ids[0] if resume_from.current_node_ids else workflow.entry
    else:
        start_state = dict(initial_state)
        entry = workflow.entry

    # Validate entry
    if not entry or workflow.get_node(entry) is None:
        return ExecutionResult(
            ok=False,
            status=ExecutionStatus.FAILED,
            response=None,
            state=initial_state,
            journal=[],
            error=f"Invalid or missing entry node: '{entry}'",
            duration_ms=0.0,
        )

    ctx = ExecutionContext(
        workflow=workflow,
        state=start_state,
        journal=[],
        current_node_id=entry,
        visited_count={},
        status=ExecutionStatus.RUNNING,
        start_time=start,
    )

    log.info("run_workflow started: %s%s", workflow.summary(), " (resumed)" if resume_from else "")

    # ── Persistence setup (optional) ----------------------------------------
    instance_id: str | None = None
    if store is not None:
        if resume_from is not None:
            instance_id = resume_from.id
            log.info("run_workflow: resuming instance '%s'", instance_id)
        else:
            from datetime import datetime, timezone

            from framework.storage.models import WorkflowInstance

            wi = await store.create(
                WorkflowInstance(
                    agent_id=agent_id,
                    conversation_id=conversation_id,
                    plan_id=workflow.workflow_id,
                    plan_version=workflow.version,
                    status="RUNNING",
                    started_at=datetime.now(timezone.utc),
                    state_snapshot=start_state,
                )
            )
            instance_id = wi.id
            log.info("run_workflow: created instance '%s'", instance_id)

    # ── Build callable helpers passed to dispatch() --------------------------
    def run_branch_fn(wf: DslWorkflow, start_nid: str, st: dict) -> Any:
        return _run_branch(wf, start_nid, st, tools)

    def run_workflow_fn(wf: DslWorkflow, state: dict, t: dict) -> Any:
        # Child workflow inherits no store (persistence of subflow is caller's concern)
        return run_workflow(wf, state, t)

    # ── Replay index: node_id -> node_status_map entry (populated on crash recovery)
    # Source: node_status_map (written atomically per-node via update_node).
    # NOT execution_log — that is only written at workflow end / CheckpointNode.
    # So this index is correct even if the process crashed before _finalize_instance.
    #
    # Recovery logic per node:
    #   status="ok"      → in replay_index: inject stored outputs, skip tool call
    #   status="running" → was in-flight when crash happened: retry (idempotency key guards)
    #   absent           → never started: execute fresh
    #
    # ⚠ TOOL DISCIPLINE (replay contract):
    #   Replay is correct ONLY if tools are pure with respect to state — i.e. their only
    #   observable effect is what they write to state via their output dict.
    #   Tools with implicit side effects (e.g. sending an email AND writing a flag) must
    #   use the _idempotency_key to guard against double-firing on retry; they MUST NOT
    #   rely on the executor detecting or replaying those effects.
    #
    # FUTURE — concurrency limit: single-process async handles current load fine; add a
    #   semaphore around dispatch() (or inside handle_parallel) when you need to cap
    #   max concurrent LLM/tool calls (e.g. asyncio.Semaphore(max_concurrent=10)).
    #
    # FUTURE — journal growth: journal grows in-memory per run; for >500-node workflows
    #   consider streaming persistence (write each JournalEntry to store immediately and
    #   discard from memory). Not urgent at current scale.
    replay_index: dict[str, dict[str, Any]] = {}
    if resume_from is not None:
        for nid, entry in (resume_from.node_status_map or {}).items():
            raw = entry.model_dump() if hasattr(entry, "model_dump") else dict(entry)
            if raw.get("status") == "ok":
                replay_index[nid] = raw
            elif raw.get("status") == "running":
                # Restore retry count so _should_retry counts across restarts.
                # Without this: crash on attempt 2 → recovery resets to 0 → 3 more
                # tries allowed → effectively infinite retries across process restarts.
                stored_attempt = int(raw.get("retry_attempt") or 0)
                if stored_attempt > 0:
                    ctx.retry_counts[nid] = stored_attempt
                    log.debug(
                        "run_workflow: restored retry_counts['%s'] = %d from store",
                        nid,
                        stored_attempt,
                    )
        if replay_index:
            log.info(
                "run_workflow: replay index built — %d node(s) will be skipped (outputs injected)",
                len(replay_index),
            )

    while ctx.status == ExecutionStatus.RUNNING:
        # ── Timeout guard
        if ctx.elapsed_seconds > cfg.max_execution_seconds:
            ctx.status = ExecutionStatus.FAILED
            error_msg = f"Workflow timeout: exceeded {cfg.max_execution_seconds}s"
            log.warning(error_msg)
            return _build_result(ctx, ok=False, error=error_msg, start=start)

        # ── Cancellation guard (check at every iteration boundary)
        if cancel_event is not None and cancel_event.is_set():
            ctx.status = ExecutionStatus.CANCELLED
            log.info("run_workflow: cancelled at node '%s'", ctx.current_node_id)
            if store is not None and instance_id is not None:
                await store.update_status(instance_id, "CANCELLED")
            return _build_result(ctx, ok=False, error="Workflow cancelled", start=start)

        # ── Max total-visits guard (prevents runaway workflows)
        if len(ctx.journal) >= cfg.max_nodes:
            ctx.status = ExecutionStatus.FAILED
            error_msg = (
                f"Max total node visits exceeded ({cfg.max_nodes}). "
                f"Increase WorkflowConfig.max_nodes for large loop workflows."
            )
            log.warning(error_msg)
            return _build_result(ctx, ok=False, error=error_msg, start=start)

        # ── Fetch current node (use ctx.workflow so ReplanNode patches are visible)
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

        # ── Dispatch — or replay stored output if this node already ran -------
        #
        # Node lifecycle:  pending → running (persisted) → ok | error (persisted)
        # Writing "running" + attempt BEFORE dispatch lets crash recovery determine:
        #   • status="ok"      → replay_index: inject stored outputs, skip tool
        #   • status="running" → was in-flight at crash: retry (idempotency key guards)
        #   • absent            → never started: execute fresh
        retry_cfg = node.retry
        attempt = ctx.retry_counts.get(node.id, 0)
        node_started = time.monotonic()

        # Mark node as RUNNING in the store before executing (fire-and-forget)
        if store is not None and instance_id is not None:
            await _mark_node_started(store, instance_id, node, attempt)

        replayed = False
        if node.id in replay_index:
            stored = replay_index[node.id]
            stored_outputs: dict[str, Any] = stored.get("outputs") or {}
            # Re-inject outputs — state_snapshot may already have them, but an
            # explicit write handles edge cases where the snapshot was partial.
            if stored_outputs:
                from framework.code_mode.executor.dispatcher import _write_outputs

                _write_outputs(node, stored_outputs, ctx.state)
            result = NodeResult(status="ok", outputs=stored_outputs)
            replayed = True
            log.info(
                "replay: node '%s' (%s) — skipped, injecting stored outputs",
                node.id,
                node.type.value,
            )
        else:
            result = await dispatch(
                node,
                ctx,
                tools,
                gate_fn=gate_fn,
                run_branch=run_branch_fn,
                store=store,
                instance_id=instance_id,
                workflow_resolver=workflow_resolver,
                run_workflow_fn=run_workflow_fn,
                replan_fn=replan_fn,
                cancel_event=cancel_event,
            )

            while result.status in ("error", "timeout") and _should_retry(retry_cfg, attempt):
                assert retry_cfg is not None
                log.debug(
                    "retrying node %s (attempt %d/%d): %s",
                    node.id,
                    attempt + 1,
                    retry_cfg.max_attempts,
                    result.error,
                )
                await _backoff(retry_cfg, attempt)
                attempt += 1
                ctx.retry_counts[node.id] = attempt
                node_started = time.monotonic()
                # Persist attempt count BEFORE retrying so that:
                # 1. Idempotency key is correct for this attempt
                # 2. Crash inside a retry leaves the right attempt count in store
                if store is not None and instance_id is not None:
                    await _mark_node_started(store, instance_id, node, attempt)
                result = await dispatch(
                    node,
                    ctx,
                    tools,
                    gate_fn=gate_fn,
                    run_branch=run_branch_fn,
                    store=store,
                    instance_id=instance_id,
                    workflow_resolver=workflow_resolver,
                    run_workflow_fn=run_workflow_fn,
                    replan_fn=replan_fn,
                    cancel_event=cancel_event,
                )

        # ── Write journal entry
        journal_entry = _journal(node, result, node_started, inputs_snapshot)
        ctx.journal.append(journal_entry)

        # ── Reset retry budget on success so loop iterations start fresh.
        # Without this, a node inside a loop that exhausted retries on iteration N
        # would have no retries left for iteration N+1.
        if result.status == "ok" and node.id in ctx.retry_counts:
            del ctx.retry_counts[node.id]

        # ── Persist node execution record (skip for replayed nodes — already stored)
        if store is not None and instance_id is not None and not replayed:
            await _persist_node(store, instance_id, node, journal_entry, ctx)

        # ── State size guard (prevents silent memory / storage bloat)
        # json.dumps gives a precise byte count matching how the store sees the data.
        # Warn at 80 %, hard-fail at 100 % of state_size_limit_mb (0 = unlimited).
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
                pass  # serialization errors during size check should never block execution

        # ── Handle error (after retries exhausted)
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
        if result.override_next == "__WAITING__":
            ctx.status = ExecutionStatus.WAITING
            gate_label = node.label or node.id
            return _build_result(
                ctx,
                ok=False,
                error=f"Paused at gate '{gate_label}'. Provide gate_fn to run_workflow to resume.",
                start=start,
            )
        if result.override_next == "__CANCELLED__":
            ctx.status = ExecutionStatus.CANCELLED
            log.info("run_workflow: cancelled by node signal at '%s'", node.id)
            if store is not None and instance_id is not None:
                await store.update_status(instance_id, "CANCELLED")
            return _build_result(ctx, ok=False, error="Workflow cancelled", start=start)

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
        "run_workflow finished: status=%s nodes=%d duration=%.1fms",
        ctx.status.value,
        len(ctx.journal),
        (time.monotonic() - start) * 1000,
    )
    result = _build_result(ctx, ok=(ctx.status == ExecutionStatus.COMPLETED), start=start)
    if store is not None and instance_id is not None:
        await _finalize_instance(store, instance_id, ctx, result)
    return result


async def _mark_node_started(
    store: Any,
    instance_id: str,
    node: Any,
    attempt: int,
) -> None:
    """Write NodeExecution(status='running', attempt=N) BEFORE dispatch.

    Gives us the full lifecycle: pending → running → ok | error.
    On crash recovery, status='running' in node_status_map means:
      - node was in-flight → retry (idempotency key prevents duplicate side-effects).
    Fire-and-forget: failures are logged but never block execution.
    """
    try:
        from datetime import datetime, timezone

        from framework.storage.models import NodeExecution as StorageNodeExecution

        ne = StorageNodeExecution(
            node_id=node.id,
            node_type=node.type.value,
            label=getattr(node, "label", "") or "",
            status="running",
            retry_attempt=attempt,
            started_at=datetime.now(timezone.utc),
        )
        await store.update_node(instance_id, node.id, ne)
    except Exception as exc:
        log.warning("_mark_node_started failed for '%s': %s", node.id, exc)


async def _persist_node(
    store: Any,
    instance_id: str,
    node: Any,
    journal_entry: JournalEntry,
    ctx: ExecutionContext,
) -> None:
    """Write per-node execution record to store. Fire-and-forget safe."""
    try:
        from datetime import datetime, timezone

        from framework.storage.models import NodeExecution as StorageNodeExecution

        ne = StorageNodeExecution(
            node_id=node.id,
            node_type=node.type.value,
            status=journal_entry.status,
            started_at=datetime.fromtimestamp(journal_entry.started_at, tz=timezone.utc),
            duration_ms=int(journal_entry.duration_ms),
            inputs=journal_entry.inputs,
            outputs=journal_entry.outputs,
            error=journal_entry.error,
        )
        await store.update_node(instance_id, node.id, ne)
        # For side-effecting nodes: also flush state_snapshot immediately
        from framework.code_mode.compiler.nodes import NodeType

        if node.type in (NodeType.ACTION, NodeType.SUBFLOW):
            await store.update_status(
                instance_id,
                "RUNNING",
                state_snapshot=ctx.state,
                current_node_ids=[ctx.current_node_id],
            )
    except Exception as exc:
        log.warning("_persist_node failed for '%s': %s", node.id, exc)


async def _finalize_instance(
    store: Any,
    instance_id: str,
    ctx: ExecutionContext,
    result: ExecutionResult,
) -> None:
    """Write final status, response, and journal to store."""
    import dataclasses

    try:
        await store.update_status(
            instance_id,
            ctx.status.value,
            state_snapshot=ctx.state,
            execution_log=[dataclasses.asdict(e) for e in ctx.journal],
            response=result.response,
            error=result.error,
            current_node_ids=[ctx.current_node_id],
        )
    except Exception as exc:
        log.warning("_finalize_instance failed for '%s': %s", instance_id, exc)


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


# ── Crash recovery -----------------------------------------------------------


async def recover_running(
    store: Any,
    workflow_resolver: Callable,  # plan_id -> DslWorkflow | None
    tools: dict[str, Callable],
    *,
    gate_fn: Callable | None = None,
) -> list[ExecutionResult]:
    """Resume all RUNNING workflow instances after a server crash.

    Args:
        store:             WorkflowInstanceStore.
        workflow_resolver: Callable(plan_id) -> DslWorkflow | None.
                           Return None to skip instances whose workflow is unavailable.
        tools:             Tool registry.
        gate_fn:           Optional gate approval function (forwarded to run_workflow).

    Returns:
        List of ExecutionResult, one per resumed instance.
    """
    running = await store.list_by_status("RUNNING")
    if not running:
        log.info("recover_running: no RUNNING instances found")
        return []

    log.info("recover_running: %d RUNNING instance(s) to resume", len(running))
    results: list[ExecutionResult] = []

    for instance in running:
        workflow = workflow_resolver(instance.plan_id)
        if workflow is None:
            log.warning(
                "recover_running: skipping '%s' — workflow '%s' not resolvable",
                instance.id,
                instance.plan_id,
            )
            continue
        if not instance.current_node_ids:
            log.warning("recover_running: skipping '%s' — no current_node_ids stored", instance.id)
            continue

        log.info("recover_running: resuming '%s' at %s", instance.id, instance.current_node_ids)
        try:
            result = await run_workflow(
                workflow=workflow,
                initial_state={},  # ignored — resume_from.state_snapshot is used
                tools=tools,
                gate_fn=gate_fn,
                store=store,
                resume_from=instance,
                workflow_resolver=workflow_resolver,
            )
            results.append(result)
        except Exception as exc:
            log.error("recover_running: instance '%s' raised: %s", instance.id, exc, exc_info=True)

    return results


# ── Deterministic replay
async def replay_workflow(
    workflow: DslWorkflow,
    execution_log: list[dict[str, Any]],
    initial_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay a workflow deterministically from a stored execution_log.

    Injects recorded node outputs directly into state WITHOUT calling any tools.
    Useful for auditing, debugging, and UI preview of past runs.

    Args:
        workflow:       The DslWorkflow that was originally executed.
        execution_log:  List of journal entry dicts (stored via _finalize_instance).
        initial_state:  Optional starting state (merged under recorded outputs).

    Returns:
        Final state dict after replaying all journal entries.
    """
    from framework.code_mode.compiler.nodes import NodeType
    from framework.code_mode.executor.dispatcher import _write_outputs

    state: dict[str, Any] = dict(initial_state or {})

    for entry in execution_log:
        node_id = entry.get("node_id")
        if not node_id:
            continue

        node = workflow.get_node(node_id)
        if node is None:
            log.debug("replay_workflow: node '%s' not found in graph — skipping", node_id)
            continue

        status = entry.get("status", "ok")
        if status in ("error", "timeout"):
            # Stop at the first failed node; state is as-of-last-success
            log.info(
                "replay_workflow: stopping at failed node '%s': %s", node_id, entry.get("error")
            )
            break

        outputs: dict[str, Any] = entry.get("outputs") or {}
        if outputs:
            _write_outputs(node, outputs, state)

        # Restore any sentinel keys the runner uses for routing
        if node.type == NodeType.BRANCH and "__branch_result__" in outputs:
            state["__branch_result__"] = outputs["__branch_result__"]
        if "__response__" in outputs:
            state["__response__"] = outputs["__response__"]

    return state
