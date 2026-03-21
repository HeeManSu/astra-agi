"""
AST parsing and validation for generated code.

Two-step pipeline:
    1. parse_code()  — raw string → AST (catches syntax errors)
    2. validate()    — AST → list of validation errors

Usage:
    result = parse_code(code)
    if result.error:
        handle syntax error ...

    errors = validate(result.module)
    if errors:
        handle validation errors ...
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
    """Strip markdown code fences if present.

    Handles:  ```python ... ```  and  ``` ... ```
    """
    lines = code.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]  # drop opening fence
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]  # drop closing fence
    return "\n".join(lines).strip()


def parse_code(code: str) -> ParseResult:
    """Parse Python code into an AST.

    Strips markdown fences before parsing if present.

    Args:
        code: Python source code string to parse.

    Returns:
        ParseResult with module on success, error message on failure.
    """
    code = _strip_fences(code)

    try:
        module = ast.parse(code)
        return ParseResult(
            module=module,
            error=None,
            ast_dump=ast.dump(module, indent=4),
        )

    except SyntaxError as e:
        log.warning(
            "parse_code: SyntaxError in generated code at line %s, col %s: %s",
            e.lineno,
            e.offset,
            e.msg,
            exc_info=True,
        )
        return ParseResult(
            module=None,
            error=f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}",
            ast_dump=None,
        )

    except Exception as e:
        log.exception("parse_code: unexpected parse error")
        return ParseResult(
            module=None,
            error=f"Parse error: {e}\n{traceback.format_exc()}",
            ast_dump=None,
        )


# Nodes that are NEVER allowed in generated code.
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
    # Generators / comprehensions
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
    # Flow control statements not supported by DSL lowerer
    ast.Pass,
    ast.Break,
    ast.Continue,
    # Assertions
    ast.Assert,
    # Augmented assignment (x += 1)
    ast.AugAssign,
    # Walrus operator (:=)
    ast.NamedExpr,
    # Annotated assignment (x: int = 5)
    ast.AnnAssign,
)

# Also ban Match if available (Python 3.10+)
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
    ast.Pass: "pass statement",
    ast.Break: "break statement",
    ast.Continue: "continue statement",
    ast.Assert: "assert statement",
    ast.AugAssign: "augmented assignment (+=, -=, etc.)",
    ast.NamedExpr: "walrus operator (:=)",
    ast.AnnAssign: "type annotation assignment",
}

# Only these are allowed at the top level of the module.
_ALLOWED_TOP_LEVEL = (ast.Assign, ast.Expr, ast.If, ast.For)

# Dangerous builtins that must NEVER be called.
_DANGEROUS_CALLS = frozenset(
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

# Safe builtins that ARE allowed as bare Name calls.
_SAFE_BUILTINS = frozenset(
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

# Known dangerous module/object names that must NEVER be used as call targets.
# Blocks os.system(), subprocess.run(), socket.connect(), etc.
_DANGEROUS_MODULES = frozenset(
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
        # Serialization (pickle is code exec)
        "pickle",
        "shelve",
        "marshal",
    }
)


def validate(
    module: ast.Module,
    *,
    allowed_tools: set[str] | None = None,
) -> list[ValidationError]:
    """Validate an AST module against the restricted code-mode subset.

    Checks:
        1. No banned node types anywhere in the tree
        2. Only Assign/Expr/If/For at top level
        3. Dangerous / unknown call enforcement
        4. Max 1 level of if nesting, max 1 level of for nesting
        5. Exactly one synthesize_response() as the last statement
        6. Tool whitelist enforcement (when allowed_tools is provided)

    Args:
        module:        A parsed ast.Module to validate.
        allowed_tools: Optional set of known tool names (e.g. {"inventory.check_stock"}).
                       When provided, attribute calls that don't match the whitelist
                       are flagged as unknown.

    Returns:
        List of ValidationError (empty means code is valid).
    """
    try:
        checker = _ASTValidator(module, allowed_tools=allowed_tools)
        return checker.run()
    except Exception as exc:
        log.exception("validate: unexpected internal error during AST validation")
        return [
            ValidationError(
                message=f"Internal validation error: {exc}\n{traceback.format_exc()}",
            )
        ]


class _ASTValidator:
    """Internal validator that walks the AST and collects errors."""

    def __init__(
        self,
        module: ast.Module,
        *,
        allowed_tools: set[str] | None = None,
    ) -> None:
        self._module = module
        self._allowed_tools = allowed_tools
        self._errors: list[ValidationError] = []

    def run(self) -> list[ValidationError]:
        self._check_banned_nodes()
        self._check_top_level()
        self._check_nesting(self._module.body, if_depth=0, for_depth=0)
        self._check_calls()
        self._check_synthesize()
        if self._allowed_tools is not None:
            self._check_tool_whitelist()
        return self._errors

    # -- Check 1: Banned nodes --

    def _check_banned_nodes(self) -> None:
        """Walk entire tree and flag any banned node type."""
        for node in ast.walk(self._module):
            if isinstance(node, _BANNED_NODES):
                name = _BANNED_NAMES.get(type(node), type(node).__name__)
                self._emit(
                    f"'{name}' is not allowed in generated code",
                    node,
                )

    # -- Check 2: Top-level structure --

    def _check_top_level(self) -> None:
        """Ensure only Assign, Expr, If, For appear at module level."""
        for stmt in self._module.body:
            if not isinstance(stmt, _ALLOWED_TOP_LEVEL):
                self._emit(
                    f"Unsupported top-level statement: {type(stmt).__name__}",
                    stmt,
                )

    # -- Check 3: Dangerous / unknown calls --

    def _check_calls(self) -> None:
        """Walk all Call nodes and enforce call safety rules.

        Rules:
          - Name calls must be in _SAFE_BUILTINS (blocks eval, exec, open, etc.)
          - Attribute calls must be single-level: var.method() only
            (blocks chained calls like a.b.c())
          - Attribute call target must NOT be a known dangerous module
            (blocks os.system(), subprocess.run(), etc.)
        """
        for node in ast.walk(self._module):
            if not isinstance(node, ast.Call):
                continue

            func = node.func

            # Case 1: bare name call — e.g. len(), eval()
            if isinstance(func, ast.Name):
                name = func.id
                if name in _DANGEROUS_CALLS:
                    self._emit(
                        f"'{name}()' is a dangerous builtin and is not allowed",
                        node,
                    )
                elif name not in _SAFE_BUILTINS:
                    self._emit(
                        f"Unknown function '{name}()' — only safe builtins and tool calls (var.method()) are allowed",
                        node,
                    )

            # Case 2: attribute call — e.g. agent.tool()
            elif isinstance(func, ast.Attribute):
                # Allow single-level: Name.attr()  (e.g. agent.tool())
                # Allow subscript:    Name[i].attr() (e.g. results[0].get())
                # Block chained:      Name.attr.attr() or Call().attr()
                if isinstance(func.value, ast.Name):
                    # Block known dangerous modules: os.system(), subprocess.run(), etc.
                    target_name = func.value.id
                    if target_name in _DANGEROUS_MODULES:
                        self._emit(
                            f"'{target_name}.{func.attr}()' is not allowed — '{target_name}' is a blocked module/object",
                            node,
                        )
                elif isinstance(func.value, ast.Subscript):
                    # results[0].get() — safe pattern (indexing then method call)
                    # Check if the base of the subscript is a dangerous module
                    if isinstance(func.value.value, ast.Name):
                        target_name = func.value.value.id
                        if target_name in _DANGEROUS_MODULES:
                            self._emit(
                                f"'{target_name}[...].{func.attr}()' is not allowed — '{target_name}' is a blocked module/object",
                                node,
                            )
                elif isinstance(func.value, ast.Call) and func.attr == "get":
                    # Allow chained .get().get() — safe dict access, no side effects
                    # e.g. step_result.get("result", {}).get("price")
                    pass
                else:
                    self._emit(
                        "Chained calls like 'a.b.c()' are not allowed — use single-level 'var.method()'",
                        node,
                    )

    # -- Check 6: Tool whitelist --

    def _check_tool_whitelist(self) -> None:
        """Validate that attribute calls match the allowed_tools whitelist.

        Only runs when allowed_tools is provided.  Flags Name.attr() calls
        where 'name.attr' is not in the whitelist.
        """
        assert self._allowed_tools is not None

        # Extract known agent/domain names from the whitelist
        known_domains = {t.split(".")[0] for t in self._allowed_tools if "." in t}

        for node in ast.walk(self._module):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                target_name = func.value.id
                # Skip if not a known domain — it's a local variable method
                # call like results.append() which _check_calls already handles
                if target_name not in known_domains:
                    continue
                full_name = f"{target_name}.{func.attr}"
                if full_name not in self._allowed_tools:
                    self._emit(
                        f"Unknown tool '{full_name}()' — not in the allowed tools whitelist",
                        node,
                    )

    # -- Check 3: Nesting depth --

    def _check_nesting(
        self,
        stmts: list[ast.stmt],
        *,
        if_depth: int,
        for_depth: int,
    ) -> None:
        """Recursively check that if/for nesting doesn't exceed 1 level."""
        for stmt in stmts:
            if isinstance(stmt, ast.If):
                if if_depth >= 1:
                    self._emit(
                        "Nested if-statements are not allowed (max depth: 1)",
                        stmt,
                    )
                else:
                    self._check_nesting(
                        stmt.body,
                        if_depth=if_depth + 1,
                        for_depth=for_depth,
                    )
                    if stmt.orelse:
                        self._check_nesting(
                            stmt.orelse,
                            if_depth=if_depth + 1,
                            for_depth=for_depth,
                        )

            elif isinstance(stmt, ast.For):
                if for_depth >= 1:
                    self._emit(
                        "Nested for-loops are not allowed (max depth: 1)",
                        stmt,
                    )
                else:
                    self._check_nesting(
                        stmt.body,
                        if_depth=if_depth,
                        for_depth=for_depth + 1,
                    )
                    if stmt.orelse:
                        self._check_nesting(
                            stmt.orelse,
                            if_depth=if_depth,
                            for_depth=for_depth + 1,
                        )

    # -- Check 4: synthesize_response --

    def _check_synthesize(self) -> None:
        """Ensure exactly one synthesize_response() call as the last statement."""
        synth_count = 0
        for node in ast.walk(self._module):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "synthesize_response"
            ):
                synth_count += 1

        if synth_count == 0:
            self._errors.append(
                ValidationError(
                    message="Missing synthesize_response() — exactly one is required as the last statement",
                )
            )
            return

        if synth_count > 1:
            self._errors.append(
                ValidationError(
                    message=f"Found {synth_count} synthesize_response() calls — exactly 1 is required",
                )
            )

        # Check that the last top-level statement IS synthesize_response
        if self._module.body:
            last = self._module.body[-1]
            is_synth = (
                isinstance(last, ast.Expr)
                and isinstance(last.value, ast.Call)
                and isinstance(last.value.func, ast.Name)
                and last.value.func.id == "synthesize_response"
            )
            if not is_synth:
                self._emit(
                    "synthesize_response() must be the last statement",
                    last,
                )

    # -- Helper --

    def _emit(self, message: str, node: ast.AST) -> None:
        self._errors.append(
            ValidationError(
                message=message,
                line=getattr(node, "lineno", 0),
                col=getattr(node, "col_offset", 0),
                node_type=type(node).__name__,
            )
        )
