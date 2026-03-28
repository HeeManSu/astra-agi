"""Workflow builder — lowers a validated Python AST into an ExecutionWorkflow graph.

Pipeline:  ast.Module  →  build_workflow()  →  WorkflowBuildResult(.success, .workflow, .errors)

The WorkflowBuilder walks the AST top-down, converting each statement into
typed graph nodes connected by edges. It tracks ``_open_tails`` — nodes whose
outgoing edge hasn't been wired yet — so that control flow (if/for) composes
naturally by saving and restoring tails.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import ClassVar

from framework.code_mode.compiler.edges import (
    Edge,
    branch_default,
    branch_else,
    branch_if,
    loop_back,
    loop_body,
    sequential,
)
from framework.code_mode.compiler.nodes import (
    Node,
    action_node,
    branch_node,
    loop_node,
    respond_node,
    transform_node,
)


_AUGMENTED_OPS: dict[type, str] = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "//",
    ast.Mod: "%",
    ast.Pow: "**",
    ast.BitOr: "|",
    ast.BitAnd: "&",
    ast.BitXor: "^",
    ast.LShift: "<<",
    ast.RShift: ">>",
}


@dataclass
class WorkFlowConfig:
    """Runtime Configuration for a workflow."""

    max_execution_seconds: int = 300
    max_nodes: int = 10_000
    max_visits_per_node: int = 5_000
    state_size_limit_mb: int = 50


@dataclass
class ExecutionWorkflow:
    """A graph of nodes and edges that represent the execution of a workflow."""

    name: str = ""
    description: str = ""
    entry: str = ""
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    state_variables: list[str] = field(default_factory=list)
    config: WorkFlowConfig = field(default_factory=WorkFlowConfig)


@dataclass
class WorkflowBuildResult:
    """Outcome of ``build()`` — consumed by the sandbox and validator."""

    success: bool
    workflow: ExecutionWorkflow | None = None
    errors: list[str] = field(default_factory=list)


def _extract_inputs(call: ast.Call) -> dict[str, str]:
    """Unparse call arguments into a {name: expression_string} dict."""
    inputs: dict[str, str] = {}
    for i, arg in enumerate(call.args):
        inputs[f"_arg{i}"] = ast.unparse(arg)
    for kw in call.keywords:
        key = kw.arg if kw.arg else f"**{ast.unparse(kw.value)}"
        inputs[key] = ast.unparse(kw.value)
    return inputs


class WorkflowBuilder:
    """
    AST to Workflow Builder.

    Args:
        workflow: The workflow to build.

    Returns:
        A  WorkflowBuildResult containing the success status and the workflow graph.
    """

    def __init__(self, workflow: ExecutionWorkflow):
        self.workflow = workflow
        self._open_tails: list[
            tuple[str, Callable]
        ] = []  # tuple of (source_id, function to make the edge)
        self._errors: list[str] = []

    def _register_state_variable(self, name: str) -> None:
        """Register a variable name in state_variables if not already present."""
        if name not in self.workflow.state_variables:
            self.workflow.state_variables.append(name)

    def _chain_next_node(self, node: Node) -> None:
        """Chain the next node to the current node."""
        for source_id, make_edge in self._open_tails:
            edge = make_edge(source_id, node.id)
            self.workflow.edges.append(edge)
        self._open_tails.clear()
        if not self.workflow.entry:
            self.workflow.entry = node.id
        self.workflow.nodes.append(node)
        self._open_tails.append((node.id, sequential))

    def _handle_for(self, statement: ast.For) -> None:
        """
        Lower for loop into LoopNode with LOOP_BODY / LOOP_BACK edges.

        For(
            target: Name(id='', ctx=Store())
            iter: Call(
                func= Attribute(
                    value= Name(id='', ctx=Load()),
                    attr='',
                    ctx=Load()
                ),
                args=[],
                keywords=[]
            )
        )
        """

        collection = ast.unparse(statement.iter)

        if isinstance(statement.target, ast.Name):
            var = statement.target.id
            self._register_state_variable(var)
        elif isinstance(statement.target, ast.Tuple):
            var = ast.unparse(statement.target)
            for element in statement.target.elts:
                if isinstance(element, ast.Name):
                    self._register_state_variable(element.id)
        else:
            var = ast.unparse(statement.target)

        loop = loop_node(over=collection, as_var=var, label=f"for {var} in {collection}")

        for source_id, make_edge in self._open_tails:
            self.workflow.edges.append(make_edge(source_id, loop.id))
        self._open_tails.clear()

        if not self.workflow.entry:
            self.workflow.entry = loop.id
        self.workflow.nodes.append(loop)

        # Walk loop body: first body node gets a LOOP_BODY edge from the loop
        self._open_tails = [(loop.id, loop_body)]
        self.walk(statement.body)

        # Wire every body tail back to the loop node via LOOP_BACK
        for source_id, _ in self._open_tails:
            self.workflow.edges.append(loop_back(source_id, loop.id))
        self._open_tails.clear()

        self._open_tails = [(loop.id, sequential)]

    def _handle_if(self, statement: ast.If) -> None:
        """
        Lower if/elif/else into BranchNode with BRANCH_IF / BRANCH_ELSE / BRANCH_DEFAULT edges.

        If(
            test: Call(
                func= Attribute(
                    value= Name(id='', ctx=Load()),
                    attr='',
                    ctx=Load()
                ),
                args=[],
                keywords=[]
            )
        )
        """

        condition = ast.unparse(statement.test)
        node = branch_node(condition=condition, label=f"if {condition}")

        for source_id, make_edge in self._open_tails:
            edge = make_edge(source_id, node.id)
            self.workflow.edges.append(edge)
        self._open_tails.clear()

        if not self.workflow.entry:
            self.workflow.entry = node.id
        self.workflow.nodes.append(node)

        self._open_tails = [
            (
                node.id,
                lambda source, target, condition=condition: branch_if(source, target, condition),
            ),
        ]

        self.walk(statement.body)

        if_tails = self._open_tails[:]

        if statement.orelse:
            self._open_tails = [
                (node.id, branch_else),
            ]
            self.walk(statement.orelse)

            else_tails = self._open_tails[:]
            self._open_tails = if_tails + else_tails
        else:
            self._open_tails = [
                *if_tails,
                (node.id, branch_default),
            ]

    def _handle_expr(self, statement: ast.Expr) -> None:
        """
        Handle an expression statement.

        Expr(
            value: Call(
                func= Attribute(
                    value= Name(id='', ctx=Load()),
                    attr='',
                    ctx=Load()
                ),
                args=[],
                keywords=[]
            )
        )
        """
        value = statement.value

        # pure expression like `some_var` or `a + b`
        if not isinstance(value, ast.Call):
            expr = ast.unparse(value)
            node = transform_node(expression=expr, assign_to="", label=expr)
            self._chain_next_node(node)
            return

        # synthesize_response(...) → RespondNode
        if isinstance(value.func, ast.Name) and value.func.id == "synthesize_response":
            message = ast.unparse(value.args[0]) if value.args else "''"
            node = respond_node(message=message)
            self._chain_next_node(node)
            return

        # agent.tool(...) → ActionNode (dotted name)
        if isinstance(value.func, ast.Attribute):
            tool = ast.unparse(value.func)
            node = action_node(
                tool=tool,
                label=f"{tool}(...)",
                inputs=_extract_inputs(value),
            )
            self._chain_next_node(node)
            return

        # bare built-in function like len(items) → TransformNode
        expr = ast.unparse(value)
        node = transform_node(expression=expr, assign_to="", label=expr)
        self._chain_next_node(node)

    def _handle_annotated_assign(self, statement: ast.AnnAssign) -> None:
        """
        Handle an annotated assignment statement like x: int = 1.

        Args:
            statement: The annotated assignment statement to handle.

        AnnAssign(
            target: Name(id='', ctx=Store())
            annotation: Type(id='', ctx=Load())
            value: Call(
                func= Attribute(
                    value= Name(id='', ctx=Load()),
                    attr='',
                    ctx=Load()
                ),
                args=[],
                keywords=[]
            )
        )
        """

        if statement.value is None:
            return

        if not isinstance(statement.target, ast.Name):
            self._errors.append(f"Line {statement.lineno}: only simple name targets supported")
            return

        name = statement.target.id
        self._register_state_variable(name)
        value = statement.value

        if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute):
            tool = ast.unparse(value.func)
            node = action_node(
                tool=tool,
                label=f"{name} = {tool}(...)",
                inputs=_extract_inputs(value),
                outputs={"result": name},
            )
        else:
            expr = ast.unparse(value)
            node = transform_node(
                expression=expr,
                assign_to=name,
                label=f"{name} = {expr}",
            )

        self._chain_next_node(node)

    def _handle_augmented_assign(self, statement: ast.AugAssign) -> None:
        """
        Handle an augmented assignment statement like x += 1.

        Args:
            statement: The augmented assignment statement to handle.

        AugAssign(
            target: Name(id='', ctx=Store())
            op: AugAssignOp
            value: Call(
                func= Attribute(
                    value= Name(id='', ctx=Load()),
                    attr='',
                    ctx=Load()
                ),
                args=[],
                keywords=[]
            )
        )
        """

        if not isinstance(statement.target, ast.Name):
            self._errors.append(f"Line {statement.lineno}: only simple name targets supported")
            return

        name = statement.target.id
        self._register_state_variable(name)

        operation = _AUGMENTED_OPS.get(type(statement.op), "+")

        rhs = ast.unparse(statement.value)

        expr = f"{name} {operation} ({rhs})"  # x -= a - b lowers to x - (a - b)

        node = transform_node(expression=expr, assign_to=name, label=f"{name} {operation}= {rhs}")

        self._chain_next_node(node)

    def _handle_assign(self, statement: ast.Assign) -> None:
        """
        Handle an assignment statement.

        Assign(
            targets: [
                Name(id='', ctx=Store())
            ])
            value: Call(
                func= Attribute(
                    value= Name(id='', ctx=Load()),
                    attr='',
                    ctx=Load()
                ),
                args=[],
                keywords=[]
            )
        )

        Args:
            statement: The assignment statement to handle.
        """
        target = statement.targets[0]
        if not isinstance(target, ast.Name):
            self._errors.append(f"Line {statement.lineno}: only simple name targets supported")
            return

        name = target.id
        self._register_state_variable(name)
        value = statement.value

        if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute):
            tool = ast.unparse(value.func)
            node = action_node(
                tool=tool,
                label=f"{name} = {tool}(...)",
                inputs=_extract_inputs(value),
                outputs={"result": name},
            )
        else:
            expr = ast.unparse(value)
            node = transform_node(
                expression=expr,
                assign_to=name,
                label=f"{name} = {expr}",
            )

        self._chain_next_node(node)

    _HANDLERS: ClassVar[dict[type, str]] = {
        ast.Assign: "_handle_assign",
        ast.AugAssign: "_handle_augmented_assign",
        ast.AnnAssign: "_handle_annotated_assign",
        ast.Expr: "_handle_expr",
        ast.If: "_handle_if",
        ast.For: "_handle_for",
    }

    def walk(self, statements: list[ast.stmt]) -> None:
        """Walk the AST and build the workflow."""
        for statement in statements:
            if isinstance(statement, ast.Pass):
                continue
            handler_name = self._HANDLERS.get(type(statement))
            if handler_name:
                getattr(self, handler_name)(statement)
            else:
                self._errors.append(
                    f"Unsupported: {type(statement).__name__} at line {getattr(statement, 'lineno', '?')}"
                )


def build_workflow(
    module: ast.Module,
    *,
    name: str = "",
) -> WorkflowBuildResult:
    """
    Build a workflow from an AST module.

    Args:
        module: The AST module to build the workflow from.
        name: The name of the workflow.

    Returns:
        A WorkflowBuildResult containing the success status and the workflow.
    """

    if not module.body:
        return WorkflowBuildResult(success=False, errors=["Empty module — nothing to build"])

    workflow = ExecutionWorkflow(
        name=name or "workflow",
        description=f"Auto-generated from AST ({len(module.body)} nodes)",
    )

    builder = WorkflowBuilder(workflow)
    builder.walk(module.body)

    if builder._errors:
        return WorkflowBuildResult(success=False, workflow=workflow, errors=builder._errors)

    return WorkflowBuildResult(success=True, workflow=workflow)
