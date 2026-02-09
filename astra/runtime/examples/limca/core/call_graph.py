# ruff: noqa: TID252
"""Call graph with FQN support."""

from dataclasses import dataclass, field

from .parser import Call


@dataclass
class CallGraph:
    """Call graph tracking caller → callee relationships."""

    _edges: dict[str, set[str]] = field(default_factory=dict)  # caller → callees
    _reverse: dict[str, set[str]] = field(default_factory=dict)  # callee → callers
    _calls: list[Call] = field(default_factory=list)  # All call objects
    _unresolved: list[Call] = field(default_factory=list)  # Unresolved calls

    def add_call(self, call: Call) -> None:
        """Add a call to the graph."""
        self._calls.append(call)

        if call.callee_fqn is None:
            self._unresolved.append(call)
            return

        caller = call.caller_fqn
        callee = call.callee_fqn

        if caller not in self._edges:
            self._edges[caller] = set()
        self._edges[caller].add(callee)

        if callee not in self._reverse:
            self._reverse[callee] = set()
        self._reverse[callee].add(caller)

    def get_callees(self, fqn: str) -> set[str]:
        """Get direct callees of a symbol."""
        return self._edges.get(fqn, set())

    def get_callers(self, fqn: str) -> set[str]:
        """Get direct callers of a symbol."""
        return self._reverse.get(fqn, set())

    def get_callees_deep(
        self,
        fqn: str,
        depth: int = 3,
        visited: set[str] | None = None,
        max_nodes: int = 100,
    ) -> dict[str, set[str]]:
        """Get callees up to specified depth.

        Returns dict mapping FQN → set of callees at that level.
        """
        if visited is None:
            visited = set()

        result: dict[str, set[str]] = {}
        if depth <= 0 or fqn in visited or len(visited) >= max_nodes:
            return result

        visited.add(fqn)
        callees = self.get_callees(fqn)
        result[fqn] = callees

        for callee in callees:
            if len(visited) >= max_nodes:
                break
            sub = self.get_callees_deep(callee, depth - 1, visited, max_nodes)
            result.update(sub)

        return result

    def get_callers_deep(
        self,
        fqn: str,
        depth: int = 3,
        visited: set[str] | None = None,
        max_nodes: int = 100,
    ) -> dict[str, set[str]]:
        """Get callers up to specified depth."""
        if visited is None:
            visited = set()

        result: dict[str, set[str]] = {}
        if depth <= 0 or fqn in visited or len(visited) >= max_nodes:
            return result

        visited.add(fqn)
        callers = self.get_callers(fqn)
        result[fqn] = callers

        for caller in callers:
            if len(visited) >= max_nodes:
                break
            sub = self.get_callers_deep(caller, depth - 1, visited, max_nodes)
            result.update(sub)

        return result

    @property
    def unresolved_count(self) -> int:
        """Number of unresolved calls."""
        return len(self._unresolved)

    def __len__(self) -> int:
        return len(self._calls)
