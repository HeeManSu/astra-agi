"""
AST parsing and validation for generated code.

This module provides a two-step pipeline for validating LLM-generated Python code:
1. `parse_code()` - Converts raw string to AST, catching syntax errors
2. `validate()` - Validates AST structure and enforces safety rules

Example:
    result = parse_code(code)
    if result.error:
        # Handle syntax error
        return

    errors = validate(result.module)
    if errors:
        # Handle validation errors
        return
"""

import ast
from dataclasses import dataclass
import logging
import traceback


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationError:
    """A single validation violation found in the AST."""

    message: str
    line: int = 0
    col: int = 0
    node_type: str = ""


@dataclass
class ParseResult:
    """Result of parsing code into an AST."""

    module: ast.Module | None
    error: str | None
    ast_dump: str | None


def _strip_fences(code: str) -> str:
    lines = code.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def parse_code(code: str) -> ParseResult:
    """Parse Python code into an AST.

    Automatically strips markdown fences and handles syntax errors gracefully.

    Args:
        code: Python source code string to parse

    Returns:
        ParseResult containing the parsed AST module, error message (if any),
        and AST dump for debugging
    """

    # removes the unwanted markdown fences from the code
    code = _strip_fences(code)

    try:
        module = ast.parse(code)
        return ParseResult(
            module=module,
            error=None,
            ast_dump=ast.dump(module, indent=4),
        )

    except SyntaxError as e:
        return ParseResult(
            module=None,
            error=f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}",
            ast_dump=None,
        )


_BANNED_NODES = (
    # Imports
    ast.Import,
    ast.ImportFrom,
    # Definitions
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
    # Exception handling
    ast.Try,
    ast.Raise,
    # Unsafe loops
    ast.While,
    # Context managers
    ast.With,
    ast.AsyncWith,
    # Async
    ast.Await,
    ast.AsyncFor,
    # Generators
    ast.Yield,
    ast.YieldFrom,
    ast.GeneratorExp,
    ast.ListComp,
    ast.DictComp,
    ast.SetComp,
    # Scope manipulation
    ast.Global,
    ast.Nonlocal,
    # Deletion
    ast.Delete,
    # Flow control statements
    ast.Break,
    ast.Continue,
    # Assertions
    ast.Assert,
    # Walrus operator (:=)
    ast.NamedExpr,
)

if hasattr(ast, "Match"):
    _BANNED_NODES = (*_BANNED_NODES, ast.Match)

if hasattr(ast, "TryStar"):
    _BANNED_NODES = (*_BANNED_NODES, ast.TryStar)

# Friendly names for banned nodes so error messages are readable.
_BANNED_NAMES: dict[type, str] = {
    ast.Import: "import",
    ast.ImportFrom: "from ... import",
    ast.FunctionDef: "function definition (def)",
    ast.AsyncFunctionDef: "async function definition",
    ast.ClassDef: "class definition",
    ast.Lambda: "lambda expression",
    ast.Try: "try/except block",
    ast.Raise: "raise statement",
    ast.While: "while loop",
    ast.With: "with statement",
    ast.AsyncWith: "async with statement",
    ast.Await: "await expression",
    ast.AsyncFor: "async for loop",
    ast.Yield: "yield expression",
    ast.YieldFrom: "yield from expression",
    ast.GeneratorExp: "generator expression",
    ast.ListComp: "list comprehension",
    ast.DictComp: "dict comprehension",
    ast.SetComp: "set comprehension",
    ast.Global: "global statement",
    ast.Nonlocal: "nonlocal statement",
    ast.Delete: "del statement",
    ast.Break: "break statement",
    ast.Continue: "continue statement",
    ast.Assert: "assert statement",
    ast.NamedExpr: "walrus operator (:=)",
}

_ALLOWED_TOP_LEVEL = (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Expr, ast.If, ast.For, ast.Pass)

_BANNED_FUNCTIONS = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "open",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "dir",
        "breakpoint",
        "exit",
        "quit",
        "input",
    }
)


_ALLOWED_BUILTINS = frozenset(
    {
        "len",
        "range",
        "enumerate",
        "zip",
        "map",
        "filter",
        "list",
        "dict",
        "set",
        "tuple",
        "frozenset",
        "str",
        "int",
        "float",
        "bool",
        "sum",
        "min",
        "max",
        "abs",
        "round",
        "sorted",
        "reversed",
        "all",
        "any",
        "isinstance",
        "type",
        "print",
        "synthesize_response",
        "call_tool",
    }
)

_BANNED_MODULES = frozenset(
    {
        # System / process
        "os",
        "sys",
        "subprocess",
        "shutil",
        "pathlib",
        "signal",
        "ctypes",
        # Networking
        "socket",
        "http",
        "urllib",
        "requests",
        "httpx",
        "aiohttp",
        # File / IO
        "io",
        "tempfile",
        "fileinput",
        "mmap",
        # Code execution
        "importlib",
        "runpy",
        "code",
        "codeop",
        "ast",
        # Serialization
        "pickle",
        "shelve",
        "marshal",
    }
)


def validate(module: ast.Module) -> list[ValidationError]:
    """Validate an AST module for safety and structural correctness.

    Performs validation checks:
    - Banned node types (imports, function definitions, etc.)
    - Top-level structure (only assignments, expressions, if/for allowed)
    - Banned function calls
    - Nesting depth limits (max 1 level for if/for)
    - Required synthesize_response() as final statement

    Args:
        module: A parsed ast.Module to validate

    Returns:
        List of ValidationError objects. Empty list means code is valid.
    """
    try:
        checker = _ASTValidator(module)
        return checker.run()
    except Exception as exc:
        return [
            ValidationError(
                message=f"Internal validation error: {exc}\n{traceback.format_exc()}",
            )
        ]


class _ASTValidator:
    """
    Walks the AST and collects validation errors.
    """

    def __init__(self, module: ast.Module) -> None:
        self._module = module
        self._errors: list[ValidationError] = []

    def run(self) -> list[ValidationError]:
        """Run all the validation checks and collect errors."""

        self._check_banned_nodes()
        self._check_top_level()
        self._check_nesting()
        self._check_calls()
        self._check_synthesize()
        return self._errors

    def _check_banned_nodes(self) -> None:
        """Walk the AST and collect validation errors for banned nodes."""

        for node in ast.walk(self._module):
            if isinstance(node, _BANNED_NODES):
                name = _BANNED_NAMES.get(type(node), type(node).__name__)
                self._errors.append(
                    ValidationError(
                        message=f"'{name}' is not allowed in generated code",
                        node_type=name,
                        line=node.lineno,
                        col=node.col_offset,
                    )
                )

    def _check_top_level(self) -> None:
        """Check that the module has only allowed top-level nodes."""

        for statement in self._module.body:
            if not isinstance(statement, _ALLOWED_TOP_LEVEL):
                self._errors.append(
                    ValidationError(
                        message=f"Unsupported top-level statement: {type(statement).__name__}",
                        node_type=type(statement).__name__,
                        line=statement.lineno,
                        col=statement.col_offset,
                    )
                )

    def _check_nesting(self) -> None:
        """Enforce max nesting depth of 2 for if/for blocks.

        Allowed (depth <= 2):
            for item in items:          # depth 1
                if item['active']:      # depth 2 — OK

        Blocked (depth 3+):
            for item in items:          # depth 1
                if item['active']:      # depth 2
                    for sub in item:    # depth 3 — ERROR

        elif chains are NOT counted as nesting. Python represents
        ``elif`` as a single ``ast.If`` inside the parent's ``orelse``
        list, so we skip that case explicitly.
        """

        for node in ast.walk(self._module):
            if not isinstance(node, (ast.If, ast.For)):
                continue

            # Collect depth-1 child statements from body (+ else if not elif).
            depth1_stmts: list[ast.stmt] = []
            if isinstance(node, ast.If):
                depth1_stmts.extend(node.body)
                # Single ast.If in orelse = elif chain, not nesting. Skip it.
                if node.orelse and not (
                    len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If)
                ):
                    depth1_stmts.extend(node.orelse)
            elif isinstance(node, ast.For):
                depth1_stmts.extend(node.body)

            for child in depth1_stmts:
                if not isinstance(child, (ast.If, ast.For)):
                    continue
                # child is at depth 2 — allowed. Check its children for depth 3.
                depth2_stmts: list[ast.stmt] = []
                if isinstance(child, ast.If):
                    depth2_stmts.extend(child.body)
                    if child.orelse and not (
                        len(child.orelse) == 1 and isinstance(child.orelse[0], ast.If)
                    ):
                        depth2_stmts.extend(child.orelse)
                elif isinstance(child, ast.For):
                    depth2_stmts.extend(child.body)

                for grandchild in depth2_stmts:
                    if isinstance(grandchild, (ast.If, ast.For)):
                        self._errors.append(
                            ValidationError(
                                message=(
                                    f"Control flow nested too deep: "
                                    f"{type(grandchild).__name__} at line {getattr(grandchild, 'lineno', '?')} "
                                    f"is at depth 3+ (max allowed: 2)"
                                ),
                                node_type=type(grandchild).__name__,
                                line=getattr(grandchild, "lineno", 0),
                                col=getattr(grandchild, "col_offset", 0),
                            )
                        )

    def _check_calls(self) -> None:
        """Check that the AST has no dangerous function or method calls.

        Three checks on every ast.Call node:
          1. Bare name calls against _BANNED_FUNCTIONS   → eval(), exec(), open(), ...
          2. Attribute calls against _BANNED_MODULES      → os.system(), subprocess.run(), ...
          3. Bare name calls NOT in _ALLOWED_BUILTINS
             and NOT a dotted method call (agent.tool)    → unknown global function
        """
        for node in ast.walk(self._module):
            if not isinstance(node, ast.Call):
                continue

            func = node.func
            line = getattr(node, "lineno", 0)
            col = getattr(node, "col_offset", 0)

            # 1. Bare function call against _BANNED_FUNCTIONS
            if isinstance(func, ast.Name):
                if func.id in _BANNED_FUNCTIONS:
                    self._errors.append(
                        ValidationError(
                            message=f"Banned function call: {func.id}()",
                            line=line,
                            col=col,
                            node_type="Call",
                        )
                    )
                elif func.id not in _ALLOWED_BUILTINS:
                    self._errors.append(
                        ValidationError(
                            message=f"Unknown function call: {func.id}() is not in the allowed builtins",
                            line=line,
                            col=col,
                            node_type="Call",
                        )
                    )

            # 2. Method call: os.system(), subprocess.run(), ...
            elif isinstance(func, ast.Attribute):
                # Check the root object (leftmost name) against banned modules
                root = func.value
                while isinstance(root, ast.Attribute):
                    root = root.value
                if isinstance(root, ast.Name) and root.id in _BANNED_MODULES:
                    self._errors.append(
                        ValidationError(
                            message=f"Banned module access: {root.id}.{func.attr}()",
                            line=line,
                            col=col,
                            node_type="Call",
                        )
                    )

    def _check_synthesize(self) -> None:
        """Check that the last top-level statement is synthesize_response(...)."""
        if not self._module.body:
            self._errors.append(ValidationError(message="Empty module — no statements found"))
            return

        last = self._module.body[-1]

        if (
            isinstance(last, ast.Expr)
            and isinstance(last.value, ast.Call)
            and isinstance(last.value.func, ast.Name)
            and last.value.func.id == "synthesize_response"
        ):
            return

        self._errors.append(
            ValidationError(
                message="Last statement must be synthesize_response(...)",
                line=getattr(last, "lineno", 0),
                col=getattr(last, "col_offset", 0),
                node_type=type(last).__name__,
            )
        )
