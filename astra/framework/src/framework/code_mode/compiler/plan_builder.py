"""Plan builder — lowers a validated Python AST into a ExecutionPlan graph.

Pipeline:  ast.Module  →  build()  →  PlanBuildResult(.ok, .workflow, .errors)

Four internal components:
    PlanBuildContext  — accumulates nodes, edges, state fields
    PlanNodeFactory   — creates typed PlanNode subclasses
    PlanEdgeBuilder   — emits edges with correct types and roles
    CodeToPlanCompiler     — walks the AST, dispatches to handlers, chains flow
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from framework.code_mode.compiler.edges import PlanEdge, EdgeRole, EdgeType
from framework.code_mode.compiler.nodes import (
    ActionNode,
    BranchNode,
    PlanNode,
    LoopNode,
    NodeType,
    RespondNode,
    TransformNode,
)
from framework.code_mode.compiler.schema import ExecutionPlan, StateField


# ── Build Context ────────────────────────────────────────────────────────────


@dataclass
class PlanBuildContext:
    """Mutable accumulator for the graph being built.

    Every component writes into this; at the end the ``build()`` function
    reads it off to assemble a ``ExecutionPlan``.
    """

    nodes: list[PlanNode] = field(default_factory=list)
    edges: list[PlanEdge] = field(default_factory=list)
    state_fields: list[StateField] = field(default_factory=list)
    entry_id: str | None = None
    errors: list[str] = field(default_factory=list)

    # ── names we've already registered (fast dedup) ──
    _state_names: set[str] = field(default_factory=set, repr=False)

    def add_node(self, node: PlanNode) -> str:
        """Append *node* and return its id.

        The first node added automatically becomes the entry point.
        """
        self.nodes.append(node)
        if self.entry_id is None:
            self.entry_id = node.id
        return node.id

    def add_edge(self, edge: PlanEdge) -> None:
        """Append *edge* to the edge list."""
        self.edges.append(edge)

    def add_state(self, name: str, type_: str = "any") -> None:
        """Register a state field, deduplicating by name.

        If the same variable is assigned more than once (common in branches)
        we keep a single ``StateField`` entry.
        """
        if not name or name in self._state_names:
            return
        self._state_names.add(name)
        self.state_fields.append(StateField(name=name, type=type_))


# ── Node Factory
class PlanNodeFactory:
    """Creates typed PlanNode subclasses with sensible defaults.

    Pure factory — returns a node, does NOT mutate any context.
    The caller is responsible for adding it to a ``PlanBuildContext``.
    """

    def __init__(self) -> None:
        self._branch_counter = 0
        self._loop_counter = 0

    def action(
        self,
        tool: str,
        label: str,
        inputs: dict[str, str] | None = None,
        outputs: dict[str, str] | None = None,
    ) -> ActionNode:
        """Create an external tool-call node."""
        return ActionNode(
            label=label,
            tool=tool,
            inputs=inputs or {},
            outputs=outputs or {},
        )

    def transform(
        self,
        expression: str,
        assign_to: str,
        label: str,
    ) -> TransformNode:
        """Create a pure-computation node."""
        return TransformNode(
            label=label,
            expression=expression,
            assign_to=assign_to,
        )

    def respond(self, message: str) -> RespondNode:
        """Create a final-response node."""
        return RespondNode(label="respond", message=message)

    def branch(self, condition: str) -> BranchNode:
        """Create a conditional-routing node with an auto-incrementing label."""
        self._branch_counter += 1
        return BranchNode(
            label=f"branch_{self._branch_counter}",
            condition=condition,
        )

    def loop(
        self,
        over: str,
        as_var: str = "item",
    ) -> LoopNode:
        """Create an iteration node with an auto-incrementing label."""
        self._loop_counter += 1
        return LoopNode(
            label=f"loop_{self._loop_counter}",
            over=over,
            as_var=as_var,
        )


# ── Edge Builder
class PlanEdgeBuilder:
    """Emits edges into a ``PlanBuildContext`` with correct types and roles.

    Named methods prevent role/type misuse — callers never construct
    ``PlanEdge`` directly.
    """

    def __init__(self, ctx: PlanBuildContext) -> None:
        self._ctx = ctx

    def _emit(
        self,
        src: str,
        tgt: str,
        etype: EdgeType,
        role: EdgeRole,
        condition: str | None = None,
        label: str = "",
    ) -> None:
        self._ctx.add_edge(
            PlanEdge(
                source=src,
                target=tgt,
                type=etype,
                role=role,
                condition=condition,
                label=label,
            )
        )

    def sequential(self, src: str, tgt: str) -> None:
        """Plain A → B flow."""
        self._emit(src, tgt, EdgeType.SEQUENTIAL, EdgeRole.NONE)

    def branch_then(self, src: str, tgt: str, condition: str) -> None:
        """BranchNode true-path."""
        self._emit(src, tgt, EdgeType.CONDITIONAL, EdgeRole.THEN, condition=condition, label="then")

    def branch_else(self, src: str, tgt: str, condition: str) -> None:
        """BranchNode false-path (explicit else block)."""
        self._emit(
            src,
            tgt,
            EdgeType.CONDITIONAL,
            EdgeRole.ELSE,
            condition=f"not ({condition})",
            label="else",
        )

    def branch_fallthrough(self, src: str, tgt: str, condition: str) -> None:
        """BranchNode false-path (no else block — skip to next statement)."""
        self._emit(src, tgt, EdgeType.SEQUENTIAL, EdgeRole.ELSE_FALLTHROUGH)

    def loop_body(self, loop_id: str, body_entry: str) -> None:
        """LoopNode → first node inside the loop body."""
        self._emit(loop_id, body_entry, EdgeType.SEQUENTIAL, EdgeRole.BODY)

    def loop_back(self, body_tail: str, loop_id: str) -> None:
        """Last node in loop body → back to loop (next iteration)."""
        self._emit(body_tail, loop_id, EdgeType.SEQUENTIAL, EdgeRole.BACK_EDGE)


# ── AST Walker
class CodeToPlanCompiler:
    """Walks a list of AST statements and builds the DSL graph.

    Dispatches each statement to the right handler, chains tails
    with sequential edges.
    """

    def __init__(
        self,
        ctx: PlanBuildContext,
        factory: PlanNodeFactory,
        edges: PlanEdgeBuilder,
        allowed_tools: set[str],
    ) -> None:
        self._ctx = ctx
        self._factory = factory
        self._edges = edges
        self._allowed_tools = allowed_tools
        self._tool_alias_to_canonical: dict[str, str] = {}
        for tool in allowed_tools:
            # Keep exact key.
            self._tool_alias_to_canonical[tool] = tool
            # Normalize generated stub identifiers (underscores) to canonical DSL slugs (hyphens).
            self._tool_alias_to_canonical[tool.replace("-", "_")] = tool

    # ── public ─────────────────────────────────────────────────────────

    def walk(self, stmts: list[ast.stmt]) -> str | list[str] | None:
        """Process a block of statements and return the tail node id(s).

        Returns:
            A single id, a list of ids (from branching), or None if empty.
        """
        tail: str | list[str] | None = None

        for stmt in stmts:
            # reject unsupported AST node types
            if not isinstance(stmt, self._SUPPORTED_STMTS):
                self._ctx.errors.append(
                    f"Unsupported statement: {type(stmt).__name__}"
                    f" at line {getattr(stmt, 'lineno', '?')}"
                )
                continue

            # dispatch — returns (entry_id, tail_id(s))
            if isinstance(stmt, ast.Assign):
                nid = self._handle_assign(stmt)
                entry_id, new_tail = nid, nid
            elif isinstance(stmt, ast.Expr):
                nid = self._handle_expr(stmt)
                entry_id, new_tail = nid, nid
            elif isinstance(stmt, ast.If):
                entry_id, new_tail = self._handle_if(stmt)
            elif isinstance(stmt, ast.For):
                nid = self._handle_for(stmt)
                entry_id, new_tail = nid, nid
            else:
                continue

            # chain previous tail → this statement's entry node
            if tail is not None:
                self._chain(tail, entry_id)

            tail = new_tail

        return tail

    # ── chaining helper ──────────────────────────────────────────────────

    _SUPPORTED_STMTS = (ast.Assign, ast.Expr, ast.If, ast.For)

    def _chain(self, tail: str | list[str], target: str) -> None:
        """Emit sequential edge(s) from *tail* to *target*.

        Terminal nodes (``RespondNode``) are silently skipped — they
        are dead-ends and must never chain forward.

        BranchNode tails (if-without-else fallthrough) emit an
        ``ELSE_FALLTHROUGH`` edge instead of plain SEQUENTIAL.
        """
        if isinstance(tail, list):
            for t in tail:
                if not self._is_terminal(t):
                    self._emit_chain_edge(t, target)
        else:
            if not self._is_terminal(tail):
                self._emit_chain_edge(tail, target)

    def _emit_chain_edge(self, source: str, target: str) -> None:
        """Emit the right edge type based on the source node."""
        node = self._find_node(source)
        if node is not None and node.type == NodeType.BRANCH:
            condition = getattr(node, "condition", "")
            self._edges.branch_fallthrough(source, target, condition)
        else:
            self._edges.sequential(source, target)

    # ── statement handlers ───────────────────────────────────────────────

    def _handle_assign(self, stmt: ast.Assign) -> str:
        """Handle ``x = call()`` or ``x = expr``."""
        target_name = self._target_name(stmt.targets[0])
        value = stmt.value

        if isinstance(value, ast.Call):
            tool_name = self._dotted_name(value.func)
            canonical_tool_name = self._canonical_tool_name(tool_name) if tool_name else None
            if canonical_tool_name and self._classify(canonical_tool_name) == "action":
                inputs = self._extract_args(value)
                outputs = {"result": f"$.{target_name}"} if target_name else {}
                node = self._factory.action(
                    canonical_tool_name, target_name or canonical_tool_name, inputs, outputs
                )
            else:
                expr_str = self._unparse(value)
                assign_to = f"$.{target_name}" if target_name else ""
                node = self._factory.transform(expr_str, assign_to, target_name or "transform")
        else:
            # plain expression: x = some_expr
            expr_str = self._unparse(value)
            assign_to = f"$.{target_name}" if target_name else ""
            node = self._factory.transform(expr_str, assign_to, target_name or "transform")

        nid = self._ctx.add_node(node)
        if target_name:
            self._ctx.add_state(target_name)
        return nid

    def _handle_expr(self, stmt: ast.Expr) -> str:
        """Handle bare calls: ``synthesize_response(msg)`` or ``agent.tool(...)``."""
        value = stmt.value

        if not isinstance(value, ast.Call):
            # bare expression that isn't a call — treat as transform
            node = self._factory.transform(self._unparse(value), "", "expr")
            return self._ctx.add_node(node)

        func_name = self._dotted_name(value.func)

        # synthesize_response(…) → RespondNode
        if func_name == "synthesize_response":
            msg = self._unparse(value.args[0]) if value.args else ""
            node = self._factory.respond(msg)
            return self._ctx.add_node(node)

        # other bare tool call (no assignment)
        canonical_tool_name = self._canonical_tool_name(func_name) if func_name else None
        if canonical_tool_name and self._classify(canonical_tool_name) == "action":
            inputs = self._extract_args(value)
            node = self._factory.action(canonical_tool_name, canonical_tool_name, inputs)
        else:
            node = self._factory.transform(self._unparse(value), "", func_name or "expr")

        return self._ctx.add_node(node)

    def _handle_if(self, stmt: ast.If) -> tuple[str, str | list[str]]:
        """Handle ``if cond: body [else: orelse]``.

        Returns:
            ``(entry_id, tails)`` where entry_id is the BranchNode and
            tails are the exit points from both branches.
        """
        condition = self._unparse(stmt.test)
        branch = self._factory.branch(condition)
        branch_id = self._ctx.add_node(branch)

        tails: list[str] = []

        # ── then branch ──
        body_start_idx = len(self._ctx.nodes)
        body_tail = self.walk(stmt.body)

        if body_start_idx < len(self._ctx.nodes):
            body_entry_id = self._ctx.nodes[body_start_idx].id
            self._edges.branch_then(branch_id, body_entry_id, condition)

        if body_tail is not None:
            if isinstance(body_tail, list):
                tails.extend(body_tail)
            else:
                tails.append(body_tail)

        # ── else branch ──
        if stmt.orelse:
            else_start_idx = len(self._ctx.nodes)
            else_tail = self.walk(stmt.orelse)

            if else_start_idx < len(self._ctx.nodes):
                else_entry_id = self._ctx.nodes[else_start_idx].id
                self._edges.branch_else(branch_id, else_entry_id, condition)

            if else_tail is not None:
                if isinstance(else_tail, list):
                    tails.extend(else_tail)
                else:
                    tails.append(else_tail)
        else:
            # no else block — branch itself is a fallthrough tail
            tails.append(branch_id)

        # Filter out terminal nodes — they are dead-ends, not real exits
        tails = [t for t in tails if not self._is_terminal(t)]

        # If ALL branches are terminal, this if-block itself is terminal.
        # Return empty list so walk() knows nothing chains forward.
        if not tails:
            return branch_id, []

        return branch_id, tails if len(tails) != 1 else tails[0]

    def _handle_for(self, stmt: ast.For) -> str:
        """Handle ``for var in iterable: body``.

        Returns the loop node id (entry == tail for loops — the next
        statement connects after the loop exits).
        """
        # Reject for...else — DSL doesn't support Python's for-else semantics
        if stmt.orelse:
            self._ctx.errors.append(
                f"'for...else' is not supported at line {stmt.lineno}; "
                f"use a plain 'for' loop instead"
            )

        as_var = self._target_name(stmt.target)
        over = self._normalize_iterable(stmt.iter)

        loop = self._factory.loop(over, as_var)
        loop_id = self._ctx.add_node(loop)

        # walk the body
        body_start_idx = len(self._ctx.nodes)
        body_tail = self.walk(stmt.body)

        # BODY edge: loop → first body node
        if body_start_idx < len(self._ctx.nodes):
            body_entry_id = self._ctx.nodes[body_start_idx].id
            self._edges.loop_body(loop_id, body_entry_id)

        # BACK_EDGE: last body node → loop (next iteration)
        # Skip terminal nodes — RespondNode inside a loop body should NOT
        # create a back-edge (it exits the workflow, not the loop).
        if body_tail is not None:
            if isinstance(body_tail, list):
                for t in body_tail:
                    if not self._is_terminal(t):
                        self._edges.loop_back(t, loop_id)
            else:
                if not self._is_terminal(body_tail):
                    self._edges.loop_back(body_tail, loop_id)

        return loop_id

    # ── helpers ──────────────────────────────────────────────────────────

    def _find_node(self, node_id: str) -> PlanNode | None:
        """Look up a node by ID."""
        for n in self._ctx.nodes:
            if n.id == node_id:
                return n
        return None

    def _is_terminal(self, node_id: str) -> bool:
        """Check if *node_id* refers to a terminal node (``RespondNode``).

        Terminal nodes are dead-ends — they must never chain forward
        or create back-edges.
        """
        node = self._find_node(node_id)
        return node is not None and node.type == NodeType.RESPOND

    def _classify(self, dotted_name: str) -> str:
        """Return ``'action'`` if *dotted_name* is in allowed_tools, else ``'transform'``."""
        return "action" if dotted_name in self._allowed_tools else "transform"

    def _canonical_tool_name(self, dotted_name: str) -> str | None:
        """Resolve generated call names to canonical ``domain.tool-slug`` names."""
        if not dotted_name:
            return None
        return self._tool_alias_to_canonical.get(dotted_name)

    def _extract_args(self, call: ast.Call) -> dict[str, str]:
        """Extract call arguments as ``{name: unparsed_value}``."""
        args: dict[str, str] = {}
        for i, arg in enumerate(call.args):
            args[f"arg_{i}"] = self._unparse(arg)
        for kw in call.keywords:
            key = kw.arg if kw.arg else f"kwarg_{id(kw)}"
            args[key] = self._unparse(kw.value)
        return args

    @staticmethod
    def _unparse(node: ast.expr) -> str:
        """Convert an AST expression back to source code."""
        try:
            return ast.unparse(node)
        except Exception:
            return repr(node)

    @staticmethod
    def _dotted_name(func: ast.expr) -> str | None:
        """Extract the dotted name from a call target.

        ``ast.Name('foo')`` → ``'foo'``
        ``ast.Attribute(Name('a'), 'b')`` → ``'a.b'``
        """
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"
        return None

    @staticmethod
    def _target_name(target: ast.expr) -> str:
        """Extract the variable name from an assignment target."""
        if isinstance(target, ast.Name):
            return target.id
        return ""

    @staticmethod
    def _normalize_iterable(node: ast.expr) -> str:
        """Convert an iterable AST node to a state-path string.

        ``Name('items')``            → ``'$.items'``
        ``Attribute(Name('a'), 'b')`` → ``'$.a.b'``
        Anything else                → ``ast.unparse(node)``
        """
        if isinstance(node, ast.Name):
            return f"$.{node.id}"
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            return f"$.{node.value.id}.{node.attr}"
        return ast.unparse(node)


# ── Build Result
@dataclass
class PlanBuildResult:
    """Outcome of ``build()`` — consumed by the sandbox and validator."""

    ok: bool
    workflow: ExecutionPlan | None = None
    errors: list[str] = field(default_factory=list)


# ── Public API ───────────────────────────────────────────────────────────────


def build(
    module: ast.Module,
    *,
    name: str = "",
    allowed_tools: set[str] | None = None,
) -> PlanBuildResult:
    """Lower a validated ``ast.Module`` into a ``ExecutionPlan``.

    Args:
        module:        Parsed AST (must pass ``ast_parser.validate`` first).
        name:          Human-readable workflow name.
        allowed_tools: Set of ``domain.tool_slug`` strings that count as
                       external tool calls (everything else → TransformNode).

    Returns:
        ``PlanBuildResult`` with ``.ok``, ``.workflow``, and ``.errors``.
    """
    if not module.body:
        return PlanBuildResult(ok=False, errors=["Empty module — nothing to build"])

    ctx = PlanBuildContext()
    factory = PlanNodeFactory()
    edge_builder = PlanEdgeBuilder(ctx)
    walker = CodeToPlanCompiler(ctx, factory, edge_builder, allowed_tools or set())

    walker.walk(module.body)

    # ── Assemble workflow ────────────────────────────────────────────────
    workflow = ExecutionPlan(
        name=name or "workflow",
        description=f"Auto-generated from AST ({len(ctx.nodes)} nodes)",
        state=ctx.state_fields,
        nodes=ctx.nodes,
        edges=ctx.edges,
        entry=ctx.entry_id or "",
    )

    # ── Collect build-time errors + structural sanity checks ─────────────
    errors = list(ctx.errors)
    errors.extend(workflow.validate_structure())
    if errors:
        return PlanBuildResult(ok=False, workflow=workflow, errors=errors)

    return PlanBuildResult(ok=True, workflow=workflow)
