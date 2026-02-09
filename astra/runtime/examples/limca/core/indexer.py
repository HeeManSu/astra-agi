# ruff: noqa: TID252
"""Indexer - builds symbol table and graphs from source."""

from pathlib import Path

from .call_graph import CallGraph
from .import_graph import ImportGraph
from .parser import ParseResult, TreeSitterParser
from .resolver import SymbolResolver
from .symbols import SymbolTable
from .traversal import CodeNavigator


class CodeIndex:
    """Complete index of a codebase."""

    def __init__(self):
        self.symbols = SymbolTable()
        self.calls = CallGraph()
        self.imports = ImportGraph()
        self.navigator: CodeNavigator | None = None
        self.source_root: str = ""
        self.files_indexed: int = 0
        self.parse_errors: list[str] = []

    def get_navigator(self) -> CodeNavigator:
        """Get the code navigator."""
        if self.navigator is None:
            self.navigator = CodeNavigator(self.symbols, self.calls, self.imports)
        return self.navigator


# Global index instance
_index: CodeIndex | None = None


def get_index() -> CodeIndex:
    """Get the global index."""
    global _index
    if _index is None:
        _index = CodeIndex()
    return _index


def reset_index() -> None:
    """Reset the global index."""
    global _index
    _index = None


def _parse_file_safe(
    parser: TreeSitterParser, code: str, relative_path: str
) -> tuple[ParseResult | None, str | None]:
    """Parse a file safely, returning (result, error)."""
    try:
        return parser.parse_file(code, relative_path), None
    except Exception as e:
        return None, str(e)


def index_codebase(path: str) -> dict:
    """Index a codebase from a local path.

    Args:
        path: Path to the codebase root

    Returns:
        Summary of indexing results
    """
    # Import here to avoid circular imports at module level
    from ..sources.github import GitHubSource
    from ..sources.local import LocalSource

    reset_index()
    index = get_index()

    # Handle GitHub URLs
    if path.startswith(("http://", "https://")):
        gh_source = GitHubSource(path)
        try:
            local_path = gh_source.clone()
            index.source_root = local_path
            # Store source for cleanup later if needed?
            # For now, we just index it.
        except Exception as e:
            return {
                "error": f"Failed to clone repository: {e!s}",
                "path": path,
                "files_indexed": 0,
                "symbols_count": 0,
                "calls_count": 0,
                "unresolved_calls": 0,
                "parse_errors": 0,
            }
    else:
        index.source_root = path

    # Load source files
    source = LocalSource(index.source_root)

    files = source.get_files()

    # Parse all files
    parser = TreeSitterParser()
    all_results: list[ParseResult] = []

    for file_path in files:
        code = source.read_file(file_path)
        relative_path = source.get_relative_path(file_path)
        result, error = _parse_file_safe(parser, code, relative_path)

        if error:
            index.parse_errors.append(f"{file_path}: {error}")
            continue

        if result is None:
            continue

        all_results.append(result)

        # Add symbols
        for symbol in result.symbols:
            index.symbols.add(symbol)

        # Add imports
        for module, alias in result.imports:
            index.imports.add_import(relative_path, module, alias)

        # Track errors
        index.parse_errors.extend(result.errors)

    # Resolve calls
    resolver = SymbolResolver(index.symbols, index.imports)
    for result in all_results:
        resolved_calls = resolver.resolve_all(result.calls)
        for call in resolved_calls:
            index.calls.add_call(call)

    index.files_indexed = len(files)
    index.navigator = CodeNavigator(index.symbols, index.calls, index.imports)

    return {
        "path": path,
        "files_indexed": index.files_indexed,
        "symbols_count": len(index.symbols),
        "calls_count": len(index.calls),
        "unresolved_calls": index.calls.unresolved_count,
        "parse_errors": len(index.parse_errors),
    }


def find_symbol(query: str) -> list[dict]:
    """Find symbols matching a query.

    Args:
        query: Symbol name or FQN substring to search for

    Returns:
        List of matching symbols with their details
    """
    index = get_index()

    # First try exact FQN match
    exact = index.symbols.get_by_fqn(query)
    if exact:
        return [_symbol_to_dict(exact)]

    # Search by name or substring
    results = index.symbols.search(query)

    return [_symbol_to_dict(s) for s in results[:20]]  # Limit results


def trace_calls(symbol: str, depth: int = 3) -> dict:
    """Trace call graph from a symbol.

    Args:
        symbol: Symbol name or FQN
        depth: How many levels to traverse (max 5)

    Returns:
        Call tree with file:line references
    """
    from .traversal import TraversalConfig

    index = get_index()
    navigator = index.get_navigator()

    # Resolve symbol if not FQN
    fqn = symbol
    if symbol not in index.symbols:
        matches = index.symbols.search(symbol)
        if matches:
            fqn = matches[0].fqn
        else:
            return {"error": f"Symbol not found: {symbol}"}

    config = TraversalConfig(max_depth=min(depth, 5), max_nodes=100, max_files=50)
    result = navigator.trace_flow(fqn, config)

    return {
        "entry": fqn,
        "tree": result.tree,
        "files": list(result.files),
        "symbols_visited": result.visited_count,
        "truncated": result.truncated,
    }


def find_references(symbol: str) -> dict:
    """Find all usages of a symbol.

    Args:
        symbol: Symbol name or FQN

    Returns:
        List of callers with file:line info
    """
    index = get_index()

    # Resolve symbol if not FQN
    fqn = symbol
    if symbol not in index.symbols:
        matches = index.symbols.search(symbol)
        if matches:
            fqn = matches[0].fqn
        else:
            return {"error": f"Symbol not found: {symbol}"}

    callers = index.calls.get_callers(fqn)

    references = []
    for caller_fqn in callers:
        caller_sym = index.symbols.get_by_fqn(caller_fqn)
        if caller_sym:
            references.append(
                {
                    "caller": caller_fqn,
                    "file": caller_sym.file,
                    "line": caller_sym.line_start,
                }
            )

    return {
        "symbol": fqn,
        "references": references,
        "count": len(references),
    }


def get_file_snippet(file: str, start_line: int, end_line: int | None = None) -> dict:
    """Get a code snippet from a file.

    Args:
        file: Relative file path
        start_line: Starting line (1-indexed)
        end_line: Ending line (default: start_line + 20)

    Returns:
        Code snippet with line numbers
    """
    index = get_index()

    if end_line is None:
        end_line = start_line + 20

    try:
        full_path = Path(index.source_root) / file
        content = full_path.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")

        # Adjust to 0-indexed
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)

        snippet_lines = [f"{i + 1:4d} | {lines[i]}" for i in range(start_idx, end_idx)]

        return {
            "file": file,
            "start_line": start_line,
            "end_line": end_line,
            "content": "\n".join(snippet_lines),
        }

    except Exception as e:
        return {"error": str(e)}


def _symbol_to_dict(symbol) -> dict:
    """Convert Symbol to dict."""
    return {
        "fqn": symbol.fqn,
        "name": symbol.name,
        "type": symbol.type,
        "file": symbol.file,
        "line_start": symbol.line_start,
        "line_end": symbol.line_end,
        "parent_fqn": getattr(symbol, "parent_fqn", None),
    }


def get_class_hierarchy(class_name: str) -> dict:
    """Get inheritance hierarchy for a class.

    Args:
        class_name: Class name or FQN

    Returns:
        Hierarchy with parents and children
    """
    index = get_index()

    # Find the class
    fqn = class_name
    if class_name not in index.symbols:
        matches = [s for s in index.symbols.search(class_name) if s.type == "class"]
        if matches:
            fqn = matches[0].fqn
        else:
            return {"error": f"Class not found: {class_name}"}

    symbol = index.symbols.get_by_fqn(fqn)
    if not symbol or symbol.type != "class":
        return {"error": f"Not a class: {fqn}"}

    # Find children (classes that have this as parent)
    children = []
    for sym in index.symbols:
        if sym.type == "class" and getattr(sym, "parent_fqn", None) == fqn:
            children.append(_symbol_to_dict(sym))

    # Find methods in this class
    methods = []
    for sym in index.symbols:
        if sym.type == "method" and getattr(sym, "parent_fqn", None) == fqn:
            methods.append(_symbol_to_dict(sym))

    return {
        "class": _symbol_to_dict(symbol),
        "parent": getattr(symbol, "parent_fqn", None),
        "children": children,
        "methods": methods,
    }


def find_imports(target: str) -> dict:
    """Find imports for a file or symbol.

    Args:
        target: File path or symbol name

    Returns:
        Import dependencies
    """
    index = get_index()

    # Check if it's a file
    file_imports = index.imports.get_imports(target)
    if file_imports:
        deps = index.imports.get_dependencies(target, depth=2)
        return {
            "target": target,
            "type": "file",
            "direct_imports": list(file_imports),
            "all_dependencies": list(deps),
        }

    # Check if it's a symbol
    if target not in index.symbols:
        matches = index.symbols.search(target)
        if matches:
            symbol = matches[0]
            file_imports = index.imports.get_imports(symbol.file)
            return {
                "target": symbol.fqn,
                "type": "symbol",
                "file": symbol.file,
                "imports": list(file_imports) if file_imports else [],
            }

    return {"error": f"Not found: {target}"}


def generate_diagram(diagram_type: str, target: str | None = None) -> dict:
    """Generate a Mermaid diagram.

    Args:
        diagram_type: "class", "call", "imports", or "overview"
        target: Optional target symbol/file for focused diagrams

    Returns:
        Mermaid diagram code
    """
    index = get_index()

    if diagram_type == "class":
        return _generate_class_diagram(index, target)
    elif diagram_type == "call":
        return _generate_call_diagram(index, target)
    elif diagram_type == "imports":
        return _generate_import_diagram(index, target)
    elif diagram_type == "overview":
        return _generate_overview_diagram(index)
    else:
        return {"error": f"Unknown diagram type: {diagram_type}"}


def _generate_class_diagram(index: CodeIndex, target: str | None) -> dict:
    """Generate Mermaid class diagram."""
    lines = ["classDiagram"]

    classes = index.symbols.find_by_type("class")
    if target:
        # Filter to target and related classes
        matches = [c for c in classes if target.lower() in c.fqn.lower()]
        classes = matches[:10]  # Limit
    else:
        classes = classes[:15]  # Limit for overview

    for cls in classes:
        class_name = cls.name
        # Add class
        lines.append(f"    class {class_name}")

        # Add methods
        methods = [
            s
            for s in index.symbols
            if s.type == "method" and getattr(s, "parent_fqn", None) == cls.fqn
        ]
        for method in methods[:5]:
            lines.append(f"    {class_name} : +{method.name}()")

        # Add inheritance
        parent = getattr(cls, "parent_fqn", None)
        if parent:
            parent_name = parent.split(".")[-1]
            lines.append(f"    {parent_name} <|-- {class_name}")

    return {"diagram_type": "class", "mermaid": "\n".join(lines)}


def _generate_call_diagram(index: CodeIndex, target: str | None) -> dict:
    """Generate Mermaid flowchart for call graph."""
    lines = ["flowchart TD"]

    if not target:
        # Get top-level functions
        funcs = index.symbols.find_by_type("function")[:10]
        for func in funcs:
            callees = index.calls.get_callees(func.fqn)
            for callee in list(callees)[:3]:
                callee_name = callee.split(".")[-1]
                lines.append(f"    {func.name} --> {callee_name}")
    else:
        # Trace from target
        fqn = target
        if target not in index.symbols:
            matches = index.symbols.search(target)
            if matches:
                fqn = matches[0].fqn

        visited = set()

        def add_calls(current_fqn: str, depth: int):
            if depth <= 0 or current_fqn in visited:
                return
            visited.add(current_fqn)
            callees = index.calls.get_callees(current_fqn)
            current_name = current_fqn.split(".")[-1]
            for callee in list(callees)[:5]:
                callee_name = callee.split(".")[-1]
                lines.append(f"    {current_name} --> {callee_name}")
                add_calls(callee, depth - 1)

        add_calls(fqn, 3)

    return {"diagram_type": "call", "mermaid": "\n".join(lines)}


def _generate_import_diagram(index: CodeIndex, target: str | None) -> dict:
    """Generate Mermaid flowchart for imports."""
    lines = ["flowchart LR"]

    if target:
        deps = index.imports.get_dependencies(target, depth=2)
        target_name = Path(target).stem if "/" in target else target
        for dep in list(deps)[:10]:
            dep_name = dep.split(".")[-1]
            lines.append(f"    {target_name} --> {dep_name}")
    else:
        # Overview of imports
        for file, imports in list(index.imports._imports.items())[:10]:
            file_name = Path(file).stem
            for imp in list(imports)[:3]:
                imp_name = imp.split(".")[-1]
                lines.append(f"    {file_name} --> {imp_name}")

    return {"diagram_type": "imports", "mermaid": "\n".join(lines)}


def _generate_overview_diagram(index: CodeIndex) -> dict:
    """Generate overview architecture diagram."""
    lines = ["flowchart TB"]

    # Group by file/module
    files = set()
    for sym in index.symbols:
        if "/" in sym.file:
            module = sym.file.split("/")[0]
            files.add(module)

    # Add modules
    lines.append("    subgraph Modules")
    for f in list(files)[:10]:
        lines.append(f"        {f}")
    lines.append("    end")

    # Add key classes
    classes = index.symbols.find_by_type("class")[:8]
    lines.append("    subgraph Classes")
    for cls in classes:
        lines.append(f"        {cls.name}")
    lines.append("    end")

    return {"diagram_type": "overview", "mermaid": "\n".join(lines)}
