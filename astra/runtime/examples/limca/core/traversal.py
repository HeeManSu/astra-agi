# ruff: noqa: TID252
"""Multi-hop code traversal with guards."""

from dataclasses import dataclass, field
from typing import Any

from .call_graph import CallGraph
from .import_graph import ImportGraph
from .parser import Symbol
from .symbols import SymbolTable


@dataclass
class TraversalConfig:
    """Configuration for traversal limits."""

    max_depth: int = 5
    max_nodes: int = 100
    max_files: int = 50
    include_unresolved: bool = False


@dataclass
class TraceResult:
    """Result of a trace operation."""

    entry_fqn: str
    tree: dict[str, Any] = field(default_factory=dict)  # Call tree structure
    symbols: list[Symbol] = field(default_factory=list)  # Collected symbols
    files: set[str] = field(default_factory=set)  # Files touched
    truncated: bool = False  # True if limits were hit
    visited_count: int = 0


class CodeNavigator:
    """Navigate codebase via call and import graphs."""

    def __init__(
        self,
        symbols: SymbolTable,
        calls: CallGraph,
        imports: ImportGraph,
    ):
        """Initialize navigator.

        Args:
            symbols: Symbol table
            calls: Call graph
            imports: Import graph
        """
        self.symbols = symbols
        self.calls = calls
        self.imports = imports

    def trace_flow(
        self,
        entry_fqn: str,
        config: TraversalConfig | None = None,
    ) -> TraceResult:
        """Trace execution flow from entry point.

        Args:
            entry_fqn: Starting symbol FQN
            config: Traversal configuration

        Returns:
            TraceResult with call tree and collected data
        """
        if config is None:
            config = TraversalConfig()

        result = TraceResult(entry_fqn=entry_fqn)
        visited: set[str] = set()

        def build_tree(fqn: str, depth: int) -> dict[str, Any] | None:
            # Guard: depth limit
            if depth <= 0:
                result.truncated = True
                return None

            # Guard: node limit
            if len(visited) >= config.max_nodes:
                result.truncated = True
                return None

            # Guard: cycle detection
            if fqn in visited:
                return {"_cycle": True}

            visited.add(fqn)
            result.visited_count = len(visited)

            # Get symbol info
            symbol = self.symbols.get_by_fqn(fqn)
            if symbol:
                result.symbols.append(symbol)
                result.files.add(symbol.file)

                # Guard: file limit
                if len(result.files) > config.max_files:
                    result.truncated = True
                    return None

            # Get callees
            callees = self.calls.get_callees(fqn)

            node: dict[str, Any] = {
                "fqn": fqn,
                "type": symbol.type if symbol else "unknown",
                "file": symbol.file if symbol else None,
                "line": symbol.line_start if symbol else None,
                "calls": {},
            }

            for callee in callees:
                subtree = build_tree(callee, depth - 1)
                if subtree:
                    node["calls"][callee] = subtree

            return node

        result.tree = build_tree(entry_fqn, config.max_depth) or {}
        return result

    def find_path(
        self,
        from_fqn: str,
        to_fqn: str,
        max_depth: int = 10,
    ) -> list[str] | None:
        """Find call path between two symbols using BFS.

        Args:
            from_fqn: Starting symbol FQN
            to_fqn: Target symbol FQN
            max_depth: Maximum path length

        Returns:
            List of FQNs forming the path, or None if not found
        """
        if from_fqn == to_fqn:
            return [from_fqn]

        visited: set[str] = set()
        queue: list[tuple[str, list[str]]] = [(from_fqn, [from_fqn])]

        while queue:
            current, path = queue.pop(0)

            if len(path) > max_depth:
                continue

            if current in visited:
                continue
            visited.add(current)

            callees = self.calls.get_callees(current)
            for callee in callees:
                if callee == to_fqn:
                    return [*path, callee]
                if callee not in visited:
                    queue.append((callee, [*path, callee]))

        return None

    def get_context(
        self,
        fqn: str,
        include_callers: bool = True,
        include_callees: bool = True,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Get context around a symbol.

        Args:
            fqn: Symbol FQN
            include_callers: Include who calls this
            include_callees: Include what this calls
            depth: Traversal depth

        Returns:
            Context dict with symbol info, callers, callees
        """
        symbol = self.symbols.get_by_fqn(fqn)

        context: dict[str, Any] = {
            "symbol": None,
            "callers": [],
            "callees": [],
        }

        if symbol:
            context["symbol"] = {
                "fqn": symbol.fqn,
                "name": symbol.name,
                "type": symbol.type,
                "file": symbol.file,
                "line_start": symbol.line_start,
                "line_end": symbol.line_end,
            }

        if include_callers:
            callers = self.calls.get_callers_deep(fqn, depth=depth)
            context["callers"] = list(callers.keys())

        if include_callees:
            callees = self.calls.get_callees_deep(fqn, depth=depth)
            context["callees"] = list(callees.keys())

        return context
