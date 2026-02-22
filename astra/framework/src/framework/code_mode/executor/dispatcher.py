"""
Node dispatcher — one async function per node type (Phase 1).

Handles: ActionNode, TransformNode, RespondNode, BranchNode, LoopNode, TerminateNode

State resolution:
  - Input expressions like "$.state.field" or "state.field" are resolved from
    ctx.state before the node runs.
  - Outputs written into ctx.state after the node returns.

Tool calling (ActionNode):
  - tools: dict[str, Callable] passed in from the runner.
  - Key format: "agent.method" → looks up tools["agent.method"].
  - Returns tool output dict or raises on failure.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import Any

from framework.code_mode.compiler.edges import EdgeRole
from framework.code_mode.compiler.nodes import (
    ActionNode,
    BranchNode,
    CheckpointNode,
    DslNode,
    FallbackNode,
    GateNode,
    GateTimeoutAction,
    JoinStrategy,
    LoopNode,
    NodeType,
    ParallelNode,
    ReplanNode,
    RespondNode,
    SubflowNode,
    TerminateNode,
    TerminateStatus,
    TransformNode,
)
from framework.code_mode.executor.models import ExecutionContext, NodeResult


log = logging.getLogger(__name__)


# ── State resolution --
def _resolve(expr: str, state: dict[str, Any]) -> Any:
    """Resolve a state reference expression to a value.

    Supported formats:
      - "$.field"           → state["field"]
      - "$.nested.key"      → state["nested"]["key"]
      - "field"             → state["field"]  (shorthand)
      - Any other string    → returned as a literal string
    """
    if not expr:
        return None

    # Explicit JSONPath-like state reference.
    if expr.startswith("$."):
        path = expr[2:]
        if not path:
            return expr
        parts = path.split(".")
        value: Any = state
        for part in parts:
            if not isinstance(value, dict):
                return None
            value = value.get(part)
            if value is None:
                return None
        return value

    # Bare state reference: "field" or "nested.field"
    import re

    # Python literal keywords must not be treated as state identifiers.
    if expr in {"True", "False", "None"}:
        import ast

        return ast.literal_eval(expr)

    if re.fullmatch(r"[A-Za-z_]\w*(\.[A-Za-z_]\w*)*", expr):
        parts = expr.split(".")
        value: Any = state
        for part in parts:
            if not isinstance(value, dict):
                return None
            value = value.get(part)
            if value is None:
                return None
        return value

    # Literal expression: number/list/dict/string/bool/null-ish
    import ast

    try:
        return ast.literal_eval(expr)
    except Exception:
        # Fall back to raw string for unparseable literals.
        return expr


def _resolve_inputs(node: DslNode, state: dict[str, Any]) -> dict[str, Any]:
    """Resolve all node input bindings against current state."""
    return {k: _resolve(expr, state) for k, expr in node.inputs.items()}


def _write_outputs(node: DslNode, raw_outputs: dict[str, Any], state: dict[str, Any]) -> None:
    """Write handler output values into state using node output bindings.

    If node.outputs is defined, each output key maps to a state path.
    If node.outputs is empty, the entire raw_outputs dict is merged into state.
    """
    if not node.outputs:
        # No explicit output bindings — merge everything into state directly
        state.update(raw_outputs)
        return

    for out_key, state_path in node.outputs.items():
        value = raw_outputs.get(out_key)
        path = state_path.lstrip("$").lstrip(".")
        if not path:
            continue

        parts = path.split(".")
        target = state
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value


# ── Template resolution (for RespondNode.message)
def _render_template(template: str, state: dict[str, Any]) -> str:
    """Render {{state.field}} placeholders in a string template.

    Also supports bare "$.path" expressions (resolves to str(value)).
    """
    import re  # local import — only needed for RespondNode

    # {{state.field}} or {{field}}
    def _replace(m: re.Match) -> str:
        expr = m.group(1).strip()
        val = _resolve(expr, state)
        return str(val) if val is not None else m.group(0)

    result = re.sub(r"\{\{(.+?)\}\}", _replace, template)

    # If the entire message is a plain state reference, resolve it
    if result.startswith("$.") or (not result.startswith("{") and "." in result):
        resolved = _resolve(result, state)
        if resolved is not None:
            return str(resolved)

    return result


# ── Node handlers
async def handle_action(
    node: ActionNode,
    ctx: ExecutionContext,
    tools: dict[str, Callable],
) -> NodeResult:
    """Call the tool referenced by node.tool and write results to state.

    Idempotency: if the tool's signature declares `_idempotency_key`, we inject
    a deterministic key `{workflow_id}:{node_id}:{attempt}`.
    - Same attempt → same key  (safe to replay within a retry window)
    - New attempt  → new key   (tool can detect and skip duplicate work)
    Tools that do NOT declare the param are unaffected.
    """
    inputs = _resolve_inputs(node, ctx.state)

    tool_fn = tools.get(node.tool)
    if tool_fn is None:
        return NodeResult(
            status="error",
            error=f"Tool '{node.tool}' not found. Available: {list(tools.keys())}",
        )

    # ── Inject idempotency key if the tool opts in ----------------------
    import inspect

    try:
        if "_idempotency_key" in inspect.signature(tool_fn).parameters:
            attempt = ctx.retry_counts.get(node.id, 0)
            inputs["_idempotency_key"] = f"{ctx.workflow.workflow_id}:{node.id}:{attempt}"
    except (ValueError, TypeError):
        pass  # uninspectable callables (C extensions etc.) — skip gracefully

    try:
        # Support both sync and async tool functions
        if asyncio.iscoroutinefunction(tool_fn):
            raw = await tool_fn(**inputs)
        else:
            raw = tool_fn(**inputs)

        # Normalize: tool must return dict. Wrap scalars for clean state merging.
        if not isinstance(raw, dict):
            raw = {"result": raw}

        _write_outputs(node, raw, ctx.state)
        return NodeResult(status="ok", outputs=raw)

    except asyncio.TimeoutError:
        return NodeResult(status="timeout", error=f"Tool '{node.tool}' timed out")
    except Exception as exc:
        return NodeResult(status="error", error=str(exc))


async def handle_transform(node: TransformNode, ctx: ExecutionContext) -> NodeResult:
    """Evaluate expression and write result to state[assign_to]."""
    if not node.expression:
        return NodeResult(status="ok")

    # Resolve the expression — try as a state reference first, then as a literal
    value = _resolve(node.expression, ctx.state)

    # Write into assign_to path
    if node.assign_to:
        _write_outputs(node, {"__result__": value}, ctx.state)
        # assign_to may differ from outputs — write directly if no outputs binding
        if not node.outputs:
            assign_path = node.assign_to.lstrip("$").lstrip(".")
            parts = assign_path.split(".")
            target = ctx.state
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = value

    return NodeResult(status="ok", outputs={"__result__": value})


async def handle_respond(node: RespondNode, ctx: ExecutionContext) -> NodeResult:
    """Resolve message template, store as __response__, signal COMPLETED."""
    message = _render_template(node.message, ctx.state)
    ctx.state["__response__"] = message
    # Signal the runner to stop — no next node needed
    return NodeResult(status="ok", outputs={"__response__": message}, override_next="__COMPLETED__")


async def handle_branch(node: BranchNode, ctx: ExecutionContext) -> NodeResult:
    """Evaluate the condition and store result for _resolve_next to use.

    BranchNode itself is a no-op — routing is done by the runner via edges.
    We evaluate the condition here and stash it in ctx.state["__branch_result__"]
    so _resolve_next can read it without re-evaluating.
    """
    if not node.condition:
        ctx.state["__branch_result__"] = False
        return NodeResult(status="ok")

    # Evaluate: supports "$.field", "field", or simple Python-like truthy check
    value = _resolve(node.condition, ctx.state)
    ctx.state["__branch_result__"] = bool(value) if value is not None else False
    return NodeResult(status="ok")


async def handle_loop(node: LoopNode, ctx: ExecutionContext) -> NodeResult:
    """Initialize or advance the loop iterator.

    State keys managed:
      __loop_{node.id}_items   - the resolved collection
      __loop_{node.id}_idx     - current index (0-based)
      {node.as_var}            - the current iteration value
    """
    items_key = f"__loop_{node.id}_items"
    idx_key = f"__loop_{node.id}_idx"

    # First time we hit this node — initialize
    if items_key not in ctx.state:
        collection = _resolve(node.over, ctx.state)
        if collection is None:
            collection = []
        if not isinstance(collection, (list, tuple)):
            # Try to make it iterable (e.g. wrap a single value)
            collection = list(collection) if hasattr(collection, "__iter__") else [collection]
        ctx.state[items_key] = list(collection)
        ctx.state[idx_key] = 0
    else:
        # Advance index on subsequent visits
        ctx.state[idx_key] = ctx.state.get(idx_key, 0) + 1

    idx = ctx.state[idx_key]
    items = ctx.state[items_key]

    # Check max_iterations guard
    if idx > 0 and idx >= node.max_iterations:
        # Exceeded safety cap — exit the loop
        ctx.state[idx_key] = len(items)  # force exit condition
        return NodeResult(status="ok")

    if idx < len(items):
        # There's a next item — expose it via as_var
        ctx.state[node.as_var] = items[idx]
        return NodeResult(status="ok")
    else:
        # Loop exhausted — clean up and signal exit
        ctx.state.pop(node.as_var, None)
        return NodeResult(status="ok")


async def handle_terminate(node: TerminateNode, ctx: ExecutionContext) -> NodeResult:
    """Force stop the workflow with given status."""
    if node.output:
        value = _resolve(node.output, ctx.state)
        ctx.state["__response__"] = str(value) if value is not None else ""

    # Signal based on TerminateStatus
    override = "__COMPLETED__" if node.status == TerminateStatus.SUCCESS else "__FAILED__"
    return NodeResult(
        status="ok" if node.status == TerminateStatus.SUCCESS else "error",
        error=node.reason or None,
        override_next=override,
    )


def _merge_branch_state(ctx: ExecutionContext, branch_state: dict[str, Any], merge_to: str) -> None:
    """Write branch final state back into parent ctx.state."""
    if merge_to:
        path = merge_to.lstrip("$").lstrip(".")
        ctx.state[path] = branch_state
    else:
        for k, v in branch_state.items():
            if not k.startswith("__"):  # skip runner-internal sentinel keys
                ctx.state[k] = v


async def handle_gate(
    node: DslNode,
    ctx: ExecutionContext,
    gate_fn: Callable | None,
    cancel_event: asyncio.Event | None = None,
) -> NodeResult:
    """Pause for external approval.

    gate_fn=None          → returns WAITING (caller must provide gate_fn to resume).
    cancel_event fires    → returns __CANCELLED__ immediately.
    gate_fn(id, prompt)   → approved=True continues; denied=False routes to deny edge.
    Timeout: GateTimeoutAction.APPROVE / DENY / FAIL.
    """
    assert isinstance(node, GateNode)  # guaranteed by dispatch routing
    if gate_fn is None:
        return NodeResult(status="waiting", override_next="__WAITING__")

    timeout = node.timeout_seconds or 300

    async def _call_gate() -> bool:
        if asyncio.iscoroutinefunction(gate_fn):
            return await gate_fn(node.id, node.prompt)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, gate_fn, node.id, node.prompt)

    gate_task = asyncio.ensure_future(asyncio.wait_for(_call_gate(), timeout=timeout))

    # Race gate approval against cancellation
    if cancel_event is not None:
        cancel_waiter = asyncio.ensure_future(cancel_event.wait())
        done, pending = await asyncio.wait(
            {gate_task, cancel_waiter}, return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        if cancel_waiter in done:
            return NodeResult(status="error", override_next="__CANCELLED__")
        # Gate task completed — extract result
        try:
            approved = gate_task.result()
        except asyncio.TimeoutError:
            approved = None  # handled below
        except Exception as exc:
            return NodeResult(status="error", error=str(exc))
    else:
        try:
            approved = await gate_task
        except asyncio.TimeoutError:
            approved = None

    if approved is None:  # timeout reached
        if node.on_timeout == GateTimeoutAction.APPROVE:
            approved = True
        elif node.on_timeout == GateTimeoutAction.FAIL:
            return NodeResult(status="error", error=f"Gate '{node.label or node.id}' timed out")
        else:  # DENY (default)
            approved = False

    ctx.state[f"__gate_{node.id}_approved__"] = approved
    return NodeResult(status="ok", outputs={"approved": approved})


async def handle_parallel(
    node: DslNode,
    ctx: ExecutionContext,
    run_branch: Callable | None,
    cancel_event: asyncio.Event | None = None,
) -> NodeResult:
    """Fan out to BRANCH edges concurrently, merge results per join strategy.

    cancel_event fires → all in-flight branch tasks are cancelled immediately.
    """
    assert isinstance(node, ParallelNode)  # guaranteed by dispatch routing
    if run_branch is None:
        return NodeResult(
            status="error",
            error="ParallelNode requires run_branch (nested parallel not supported in sub-branches)",
        )

    branch_edges = [e for e in ctx.workflow.outgoing_edges(node.id) if e.role == EdgeRole.BRANCH]
    if not branch_edges:
        return NodeResult(status="ok")

    tasks = [
        asyncio.create_task(run_branch(ctx.workflow, e.target, dict(ctx.state)))
        for e in branch_edges
    ]

    async def _cancel_all_on_event() -> None:
        """Background watcher: cancel all branch tasks if cancel_event fires."""
        if cancel_event is not None:
            await cancel_event.wait()
            for t in tasks:
                t.cancel()

    watcher = asyncio.create_task(_cancel_all_on_event()) if cancel_event is not None else None

    if node.join == JoinStrategy.ALL:
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        if watcher is not None:
            watcher.cancel()
        # Check for cancellation
        if cancel_event is not None and cancel_event.is_set():
            return NodeResult(status="error", override_next="__CANCELLED__")
        errors: list[str] = []
        for r in raw:
            if isinstance(r, (BaseException, asyncio.CancelledError)):
                errors.append(str(r))
                continue
            b_state, b_journal, b_error = r
            ctx.journal.extend(b_journal)
            if b_error:
                errors.append(b_error)
            else:
                _merge_branch_state(ctx, b_state, node.merge_to)
        if errors:
            return NodeResult(
                status="error", error=f"Parallel branches failed: {'; '.join(errors)}"
            )

    else:  # ANY or RACE — first completed wins, cancel the rest
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        if watcher is not None:
            watcher.cancel()
        first_task = next(iter(done))
        try:
            b_state, b_journal, b_error = first_task.result()
        except asyncio.CancelledError:
            return NodeResult(status="error", override_next="__CANCELLED__")
        except Exception as exc:
            return NodeResult(status="error", error=str(exc))
        ctx.journal.extend(b_journal)
        if b_error:
            return NodeResult(status="error", error=b_error)
        _merge_branch_state(ctx, b_state, node.merge_to)

    return NodeResult(status="ok")


async def handle_fallback(
    node: FallbackNode,
    ctx: ExecutionContext,
    run_branch: Callable | None,
) -> NodeResult:
    """TRY primary path; on error run CATCH; optionally run COMPENSATE."""
    if run_branch is None:
        return NodeResult(status="error", error="FallbackNode requires run_branch")

    workflow = ctx.workflow
    try_edge = workflow.edge_by_role(node.id, EdgeRole.TRY)
    if try_edge is None:
        return NodeResult(status="error", error=f"FallbackNode '{node.id}' missing TRY edge")

    try_state, try_journal, try_error = await run_branch(workflow, try_edge.target, dict(ctx.state))
    ctx.journal.extend(try_journal)
    if try_error is None:
        _merge_branch_state(ctx, try_state, "")
        return NodeResult(status="ok")

    # TRY failed — look for CATCH
    catch_edge = workflow.edge_by_role(node.id, EdgeRole.CATCH)
    if catch_edge is None:
        return NodeResult(status="error", error=try_error)

    ctx.state["__fallback_error__"] = try_error
    catch_state, catch_journal, catch_error = await run_branch(
        workflow, catch_edge.target, dict(ctx.state)
    )
    ctx.journal.extend(catch_journal)
    if catch_error:
        return NodeResult(
            status="error",
            error=f"CATCH failed: {catch_error} (original: {try_error})",
        )
    _merge_branch_state(ctx, catch_state, "")

    # Optional COMPENSATE path (cleanup/rollback — runs after CATCH)
    comp_edge = workflow.edge_by_role(node.id, EdgeRole.COMPENSATE)
    if comp_edge is not None:
        comp_state, comp_journal, comp_error = await run_branch(
            workflow, comp_edge.target, dict(ctx.state)
        )
        ctx.journal.extend(comp_journal)
        if not comp_error:
            _merge_branch_state(ctx, comp_state, "")
        else:
            log.warning("COMPENSATE path failed in '%s': %s", node.id, comp_error)

    return NodeResult(status="ok")


async def handle_checkpoint(
    node: DslNode,
    ctx: ExecutionContext,
    store: Any | None,
    instance_id: str | None,
) -> NodeResult:
    """Flush full state + journal to WorkflowInstanceStore.

    No-op if store is not configured (persistence disabled).
    """
    assert isinstance(node, CheckpointNode)  # guaranteed by dispatch routing
    if store is None or instance_id is None:
        log.debug("CheckpointNode '%s': no store configured, skipping flush", node.id)
        return NodeResult(status="ok")

    import dataclasses

    journal_dicts = [{k: v for k, v in dataclasses.asdict(e).items()} for e in ctx.journal]
    await store.update_status(
        instance_id,
        "RUNNING",
        state_snapshot=ctx.state,
        execution_log=journal_dicts,
        current_node_ids=[ctx.current_node_id],
    )
    log.info(
        "CheckpointNode '%s' (%s): flushed %d journal entries",
        node.id,
        node.checkpoint_label,
        len(journal_dicts),
    )
    return NodeResult(status="ok")


async def handle_subflow(
    node: DslNode,
    ctx: ExecutionContext,
    tools: dict[str, Callable],
    workflow_resolver: Callable | None,
    run_workflow_fn: Callable | None,
) -> NodeResult:
    """Delegate execution to a child workflow and map I/O.

    input_map:  {child_state_key: parent_expr}  — what the child receives
    output_map: {parent_state_key: child_expr}  — what the parent gets back
    """
    assert isinstance(node, SubflowNode)  # guaranteed by dispatch routing
    if workflow_resolver is None:
        return NodeResult(status="error", error="SubflowNode requires workflow_resolver")
    if run_workflow_fn is None:
        return NodeResult(status="error", error="SubflowNode requires run_workflow_fn")

    child_workflow = workflow_resolver(node.workflow_id)
    if child_workflow is None:
        return NodeResult(
            status="error",
            error=f"SubflowNode: workflow '{node.workflow_id}' not found",
        )

    # Build child initial state from parent via input_map
    child_state: dict[str, Any] = {}
    for child_key, parent_expr in node.input_map.items():
        child_state[child_key] = _resolve(parent_expr, ctx.state)

    child_result = await run_workflow_fn(child_workflow, child_state, tools)

    if not child_result.ok:
        return NodeResult(
            status="error",
            error=f"Subflow '{node.workflow_id}' failed: {child_result.error}",
        )

    # Map child outputs back to parent state via output_map
    for parent_key, child_expr in node.output_map.items():
        ctx.state[parent_key] = _resolve(child_expr, child_result.state)

    return NodeResult(status="ok", outputs=child_result.state)


async def handle_replan(
    node: DslNode,
    ctx: ExecutionContext,
    replan_fn: Callable | None,
) -> NodeResult:
    """Pause and call the planner to patch the live workflow graph.

    replan_fn signature:  async (context: Any, workflow: DslWorkflow) -> DslWorkflow | None
      - context: the value of node.context resolved from state (or full state if empty)
      - workflow: current DslWorkflow (REMAINING scope) or full workflow (FULL scope)
      - return None to skip replanning (treat as no-op)
      - return a new DslWorkflow to replace the running graph in place

    The returned workflow must include a sequential edge from the ReplanNode
    to the next node the runner should execute.

    Guard rails:
      - per-node max_replans cap (node.max_replans)
      - global max_replans cap (workflow.config.max_replans)
      - structural validation of the patched workflow before applying
    """
    assert isinstance(node, ReplanNode)  # guaranteed by dispatch routing

    if not ctx.workflow.config.allow_replan:
        log.warning("ReplanNode '%s': replanning disabled in workflow config", node.id)
        return NodeResult(status="ok")

    if replan_fn is None:
        log.warning("ReplanNode '%s': no replan_fn provided, skipping", node.id)
        return NodeResult(status="ok")

    # ── Guard: per-node replan count
    replan_key = f"__replan_{node.id}_count__"
    replan_count = ctx.state.get(replan_key, 0)
    if replan_count >= node.max_replans:
        return NodeResult(
            status="error",
            error=f"ReplanNode '{node.id}' exceeded max_replans ({node.max_replans})",
        )

    # ── Guard: global replan count
    global_count = ctx.state.get("__total_replan_count__", 0)
    if global_count >= ctx.workflow.config.max_replans:
        return NodeResult(
            status="error",
            error=f"Global max_replans ({ctx.workflow.config.max_replans}) exceeded",
        )

    # ── Build context payload for the planner
    context_data = _resolve(node.context, ctx.state) if node.context else ctx.state
    planner_workflow = ctx.workflow  # FULL or REMAINING — caller's responsibility to scope

    # ── Call the planner
    try:
        if asyncio.iscoroutinefunction(replan_fn):
            patched = await replan_fn(context_data, planner_workflow)
        else:
            patched = replan_fn(context_data, planner_workflow)
    except Exception as exc:
        return NodeResult(status="error", error=f"replan_fn raised: {exc}")

    if patched is None:
        log.info("ReplanNode '%s': planner returned None — no change", node.id)
        return NodeResult(status="ok")

    # ── Validate patched workflow before applying
    errors = patched.validate_structure()
    if errors:
        return NodeResult(
            status="error",
            error=f"Patched workflow failed validation: {errors[0]}",
        )

    # ── Compatibility: the active ReplanNode must survive the patch.
    # If the patch removes node.id, _resolve_next finds no outgoing edges and
    # treats the workflow as complete (silently wrong).  Fail loudly instead.
    if patched.get_node(node.id) is None:
        return NodeResult(
            status="error",
            error=(
                f"Replan patch removed active ReplanNode '{node.id}'. "
                "The patched workflow must retain the current node."
            ),
        )

    # ── Apply: replace the live workflow in ctx
    ctx.workflow = patched
    ctx.state[replan_key] = replan_count + 1
    ctx.state["__total_replan_count__"] = global_count + 1
    log.info("ReplanNode '%s': applied patched workflow (replan #%d)", node.id, replan_count + 1)
    return NodeResult(status="ok")


async def dispatch(
    node: DslNode,
    ctx: ExecutionContext,
    tools: dict[str, Callable],
    *,
    gate_fn: Callable | None = None,
    run_branch: Callable | None = None,
    store: Any | None = None,
    instance_id: str | None = None,
    workflow_resolver: Callable | None = None,
    run_workflow_fn: Callable | None = None,
    replan_fn: Callable | None = None,  # Phase 4
    cancel_event: asyncio.Event | None = None,  # Cancellation token
) -> NodeResult:
    """Route a node to its handler. Applies per-node timeout if set."""
    handler_map = {
        # Phase 1
        NodeType.ACTION: lambda: handle_action(node, ctx, tools),  # type: ignore[arg-type]
        NodeType.TRANSFORM: lambda: handle_transform(node, ctx),  # type: ignore[arg-type]
        NodeType.RESPOND: lambda: handle_respond(node, ctx),  # type: ignore[arg-type]
        NodeType.BRANCH: lambda: handle_branch(node, ctx),  # type: ignore[arg-type]
        NodeType.LOOP: lambda: handle_loop(node, ctx),  # type: ignore[arg-type]
        NodeType.TERMINATE: lambda: handle_terminate(node, ctx),  # type: ignore[arg-type]
        # Phase 2
        NodeType.GATE: lambda: handle_gate(node, ctx, gate_fn, cancel_event),  # type: ignore[arg-type]
        NodeType.PARALLEL: lambda: handle_parallel(node, ctx, run_branch, cancel_event),  # type: ignore[arg-type]
        NodeType.FALLBACK: lambda: handle_fallback(node, ctx, run_branch),  # type: ignore[arg-type]
        # Phase 3
        NodeType.CHECKPOINT: lambda: handle_checkpoint(node, ctx, store, instance_id),  # type: ignore[arg-type]
        NodeType.SUBFLOW: lambda: handle_subflow(
            node, ctx, tools, workflow_resolver, run_workflow_fn
        ),  # type: ignore[arg-type]
        # Phase 4
        NodeType.REPLAN: lambda: handle_replan(node, ctx, replan_fn),  # type: ignore[arg-type]
    }

    handler_factory = handler_map.get(node.type)
    if handler_factory is None:
        return NodeResult(
            status="error",
            error=f"No handler for node type '{node.type}'.",
        )

    coro = handler_factory()

    if node.timeout_seconds:
        try:
            return await asyncio.wait_for(coro, timeout=node.timeout_seconds)
        except asyncio.TimeoutError:
            return NodeResult(
                status="timeout",
                error=f"Node '{node.id}' ({node.label}) timed out after {node.timeout_seconds}s",
            )

    return await coro
