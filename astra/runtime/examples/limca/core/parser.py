"""Tree-sitter based AST parser for multiple languages."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


@dataclass
class Symbol:
    """A code symbol (class, function, method, variable)."""

    fqn: str  # Fully qualified: auth.views.LoginView.post
    name: str  # Short name: post
    type: str  # class, function, method, variable
    file: str  # Relative file path
    line_start: int
    line_end: int
    parent_fqn: str | None = None  # For methods: auth.views.LoginView
    signature: str | None = None  # Function signature
    docstring: str | None = None


@dataclass
class Call:
    """A function/method call site."""

    caller_fqn: str  # auth.views.LoginView.post
    callee_raw: str  # self.validate (unresolved)
    callee_fqn: str | None = None  # auth.views.LoginView.validate (resolved)
    file: str = ""
    line: int = 0


@dataclass
class ParseResult:
    """Result of parsing a file."""

    file: str
    language: str
    symbols: list[Symbol] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)
    imports: list[tuple[str, str | None]] = field(default_factory=list)  # (module, alias)
    errors: list[str] = field(default_factory=list)


class LanguageDetector:
    """Detect language from file extension."""

    EXTENSION_MAP: ClassVar[dict[str, str]] = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
    }

    @classmethod
    def detect(cls, path: Path | str) -> str | None:
        """Detect language from file path."""
        if isinstance(path, str):
            path = Path(path)
        return cls.EXTENSION_MAP.get(path.suffix.lower())


class TreeSitterParser:
    """Parse source code using tree-sitter."""

    def __init__(self):
        """Initialize parser with language support."""
        self._parsers: dict[str, Any] = {}
        self._languages: dict[str, Any] = {}

    def _get_parser(self, language: str) -> Any:
        """Get or create parser for language."""
        if language in self._parsers:
            return self._parsers[language]

        try:
            import tree_sitter

            if language == "python":
                import tree_sitter_python as ts_python

                lang = tree_sitter.Language(ts_python.language())
            elif language == "javascript":
                import tree_sitter_javascript as ts_js

                lang = tree_sitter.Language(ts_js.language())
            elif language == "typescript":
                import tree_sitter_typescript as ts_ts

                lang = tree_sitter.Language(ts_ts.language_typescript())
            else:
                return None

            parser = tree_sitter.Parser(lang)
            self._parsers[language] = parser
            self._languages[language] = lang
            return parser

        except ImportError:
            return None

    def parse_file(self, code: str, file_path: str, language: str | None = None) -> ParseResult:
        """Parse a source file.

        Args:
            code: Source code content
            file_path: Relative file path (used for FQN generation)
            language: Language override (auto-detected if None)

        Returns:
            ParseResult with symbols, calls, imports
        """
        if language is None:
            language = LanguageDetector.detect(file_path)

        if language is None:
            return ParseResult(file=file_path, language="unknown", errors=["Unknown language"])

        parser = self._get_parser(language)
        if parser is None:
            return ParseResult(
                file=file_path, language=language, errors=[f"No parser for {language}"]
            )

        try:
            tree = parser.parse(bytes(code, "utf8"))
            if language == "python":
                return self._parse_python(tree.root_node, code, file_path)
            elif language in ("javascript", "typescript"):
                return self._parse_javascript(tree.root_node, code, file_path, language)
            else:
                return ParseResult(
                    file=file_path,
                    language=language,
                    errors=[f"Parser not implemented for {language}"],
                )
        except Exception as e:
            return ParseResult(file=file_path, language=language, errors=[str(e)])

    def _get_module_name(self, file_path: str) -> str:
        """Convert file path to module name."""
        # Remove extension and convert slashes to dots
        path = Path(file_path)
        parts = list(path.parts)
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        elif parts[-1].endswith((".js", ".ts")):
            parts[-1] = parts[-1].rsplit(".", 1)[0]

        # Remove __init__ from module name
        if parts[-1] == "__init__":
            parts = parts[:-1]

        return ".".join(parts)

    def _parse_python(self, root_node: Any, code: str, file_path: str) -> ParseResult:
        """Parse Python code."""
        result = ParseResult(file=file_path, language="python")
        module_name = self._get_module_name(file_path)

        # Track current scope for FQN building
        scope_stack: list[str] = [module_name]

        def get_text(node: Any) -> str:
            return code[node.start_byte : node.end_byte]

        def visit(node: Any, parent_type: str = "") -> None:
            if node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    fqn = f"{scope_stack[-1]}.{name}" if scope_stack else name
                    result.symbols.append(
                        Symbol(
                            fqn=fqn,
                            name=name,
                            type="class",
                            file=file_path,
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            parent_fqn=scope_stack[-1] if scope_stack else None,
                        )
                    )
                    scope_stack.append(fqn)
                    for child in node.children:
                        visit(child, "class")
                    scope_stack.pop()
                    return

            elif node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    fqn = f"{scope_stack[-1]}.{name}" if scope_stack else name
                    sym_type = "method" if parent_type == "class" else "function"
                    result.symbols.append(
                        Symbol(
                            fqn=fqn,
                            name=name,
                            type=sym_type,
                            file=file_path,
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            parent_fqn=scope_stack[-1] if scope_stack else None,
                        )
                    )
                    scope_stack.append(fqn)
                    for child in node.children:
                        visit(child, "function")
                    scope_stack.pop()
                    return

            elif node.type == "call":
                func_node = node.child_by_field_name("function")
                if func_node:
                    callee_raw = get_text(func_node)
                    caller_fqn = scope_stack[-1] if scope_stack else module_name
                    result.calls.append(
                        Call(
                            caller_fqn=caller_fqn,
                            callee_raw=callee_raw,
                            file=file_path,
                            line=node.start_point[0] + 1,
                        )
                    )

            elif node.type == "import_statement":
                # import foo, bar
                for child in node.children:
                    if child.type == "dotted_name":
                        result.imports.append((get_text(child), None))

            elif node.type == "import_from_statement":
                # from foo import bar
                module_node = node.child_by_field_name("module_name")
                if module_node:
                    module = get_text(module_node)
                    for child in node.children:
                        if child.type == "dotted_name" and child != module_node:
                            result.imports.append((f"{module}.{get_text(child)}", get_text(child)))
                        elif child.type == "aliased_import":
                            name_node = child.child_by_field_name("name")
                            alias_node = child.child_by_field_name("alias")
                            if name_node:
                                name = get_text(name_node)
                                alias = get_text(alias_node) if alias_node else name
                                result.imports.append((f"{module}.{name}", alias))

            # Recurse
            for child in node.children:
                visit(child, parent_type)

        visit(root_node)
        return result

    def _parse_javascript(
        self, root_node: Any, code: str, file_path: str, language: str
    ) -> ParseResult:
        """Parse JavaScript/TypeScript code."""
        result = ParseResult(file=file_path, language=language)
        module_name = self._get_module_name(file_path)

        scope_stack: list[str] = [module_name]

        def get_text(node: Any) -> str:
            return code[node.start_byte : node.end_byte]

        def visit(node: Any) -> None:
            if node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    fqn = f"{scope_stack[-1]}.{name}"
                    result.symbols.append(
                        Symbol(
                            fqn=fqn,
                            name=name,
                            type="class",
                            file=file_path,
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            parent_fqn=scope_stack[-1],
                        )
                    )
                    scope_stack.append(fqn)
                    for child in node.children:
                        visit(child)
                    scope_stack.pop()
                    return

            elif node.type in ("function_declaration", "method_definition", "arrow_function"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    fqn = f"{scope_stack[-1]}.{name}"
                    result.symbols.append(
                        Symbol(
                            fqn=fqn,
                            name=name,
                            type="function",
                            file=file_path,
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            parent_fqn=scope_stack[-1],
                        )
                    )
                    scope_stack.append(fqn)
                    for child in node.children:
                        visit(child)
                    scope_stack.pop()
                    return

            elif node.type == "call_expression":
                func_node = node.child_by_field_name("function")
                if func_node:
                    callee_raw = get_text(func_node)
                    result.calls.append(
                        Call(
                            caller_fqn=scope_stack[-1],
                            callee_raw=callee_raw,
                            file=file_path,
                            line=node.start_point[0] + 1,
                        )
                    )

            elif node.type == "import_statement":
                source_node = node.child_by_field_name("source")
                if source_node:
                    module = get_text(source_node).strip("'\"")
                    result.imports.append((module, None))

            for child in node.children:
                visit(child)

        visit(root_node)
        return result
