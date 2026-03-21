"""
Node dispatcher — one async function per node type.

Handles: ActionNode, TransformNode, RespondNode, BranchNode, LoopNode

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
import traceback
from typing import Any

from framework.code_mode.compiler.nodes import (
    ActionNode,
    BranchNode,
    LoopNode,
    NodeType,
    PlanNode,
    RespondNode,
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
        log.debug("_resolve: literal_eval failed for expr=%r", expr, exc_info=True)

    # Safe eval: handle expressions with state variable references
    # e.g. str({'step_1': step_1, 'step_2': step_2})
    _SAFE_BUILTINS = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "len": len,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
        "sorted": sorted,
        "any": any,
        "all": all,
        "isinstance": isinstance,
        "type": type,
        "range": range,
        "True": True,
        "False": False,
        "None": None,
    }
    try:
        safe_ns = {k: v for k, v in state.items() if not k.startswith("__")}
        safe_ns.update(_SAFE_BUILTINS)
        return eval(expr, {"__builtins__": {}}, safe_ns)
    except Exception:
        log.debug(
            "_resolve: safe eval failed for expr=%r, returning raw string", expr, exc_info=True
        )
        return expr


def _resolve_inputs(node: PlanNode, state: dict[str, Any]) -> dict[str, Any]:
    """Resolve all node input bindings against current state."""
    return {k: _resolve(expr, state) for k, expr in node.inputs.items()}


def _write_outputs(node: PlanNode, raw_outputs: dict[str, Any], state: dict[str, Any]) -> None:
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
    """Call the tool referenced by node.tool and write results to state."""
    inputs = _resolve_inputs(node, ctx.state)

    tool_fn = tools.get(node.tool)
    if tool_fn is None:
        return NodeResult(
            status="error",
            error=f"Tool '{node.tool}' not found. Available: {list(tools.keys())}",
        )

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
        log.error("handle_action: tool '%s' timed out", node.tool, exc_info=True)
        return NodeResult(status="timeout", error=f"Tool '{node.tool}' timed out")
    except Exception as exc:
        log.exception("handle_action: tool '%s' raised an exception", node.tool)
        return NodeResult(
            status="error",
            error=f"Tool '{node.tool}' failed: {exc}\n{traceback.format_exc()}",
        )


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
    """Resolve message expression/template, store as __response__, signal COMPLETED.

    The RespondNode.message may be:
      1. A Python expression (from ast.unparse) containing state variable references,
         e.g. ``{'step_1': step_1_result, 'step_2': step_2_result}``
      2. A template with ``{{field}}`` placeholders
      3. A plain string

    We first try to eval() the message as a Python expression using the execution
    state as the namespace. This resolves variable references like ``step_1_result``
    to their actual values from tool outputs. If eval fails (e.g. the message is
    a plain string or template), we fall back to _render_template().
    """
    raw_message = node.message

    # ── Strategy 1: Evaluate as Python expression with state as namespace
    # This handles messages like: {'status': 'success', 'results': {'step_1': step_1_result}}
    # where step_1_result etc. are keys in ctx.state with actual tool output values.
    resolved = None
    try:
        # Build a safe namespace from the execution state (only state variables)
        eval_ns: dict[str, Any] = dict(ctx.state)
        result = eval(raw_message, {"__builtins__": {}}, eval_ns)
        if isinstance(result, (dict, list)):
            import json as _json

            resolved = _json.dumps(result, default=str, ensure_ascii=False)
        elif result is not None:
            resolved = str(result)
    except Exception:
        # eval failed — message is not a valid Python expression, fall through
        log.debug(
            "handle_respond: eval failed for message, falling back to template rendering",
            exc_info=True,
        )

    # ── Strategy 2: Fall back to template rendering ({{field}} placeholders)
    if resolved is None:
        resolved = _render_template(raw_message, ctx.state)

    ctx.state["__response__"] = resolved
    # Signal the runner to stop — no next node needed
    return NodeResult(
        status="ok", outputs={"__response__": resolved}, override_next="__COMPLETED__"
    )


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


# ── Dispatch router ---------------------------------------------------------


async def dispatch(
    node: PlanNode,
    ctx: ExecutionContext,
    tools: dict[str, Callable],
) -> NodeResult:
    """Route a node to its type-specific handler."""
    handler_map = {
        NodeType.ACTION: lambda: handle_action(node, ctx, tools),  # type: ignore[arg-type]
        NodeType.TRANSFORM: lambda: handle_transform(node, ctx),  # type: ignore[arg-type]
        NodeType.RESPOND: lambda: handle_respond(node, ctx),  # type: ignore[arg-type]
        NodeType.BRANCH: lambda: handle_branch(node, ctx),  # type: ignore[arg-type]
        NodeType.LOOP: lambda: handle_loop(node, ctx),  # type: ignore[arg-type]
    }

    handler_factory = handler_map.get(node.type)
    if handler_factory is None:
        return NodeResult(
            status="error",
            error=f"No handler for node type '{node.type}'.",
        )

    coro = handler_factory()
    return await coro
