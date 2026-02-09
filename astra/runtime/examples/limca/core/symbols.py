# ruff: noqa: TID252
"""Symbol table with fully qualified name support."""

from collections.abc import Iterator
from dataclasses import dataclass, field

from .parser import Symbol


@dataclass
class SymbolTable:
    """Symbol table with FQN indexing."""

    _by_fqn: dict[str, Symbol] = field(default_factory=dict)
    _by_name: dict[str, list[Symbol]] = field(default_factory=dict)
    _by_file: dict[str, list[Symbol]] = field(default_factory=dict)
    _by_type: dict[str, list[Symbol]] = field(default_factory=dict)

    def add(self, symbol: Symbol) -> None:
        """Add a symbol to the table."""
        self._by_fqn[symbol.fqn] = symbol

        if symbol.name not in self._by_name:
            self._by_name[symbol.name] = []
        self._by_name[symbol.name].append(symbol)

        if symbol.file not in self._by_file:
            self._by_file[symbol.file] = []
        self._by_file[symbol.file].append(symbol)

        if symbol.type not in self._by_type:
            self._by_type[symbol.type] = []
        self._by_type[symbol.type].append(symbol)

    def get_by_fqn(self, fqn: str) -> Symbol | None:
        """Get symbol by fully qualified name."""
        return self._by_fqn.get(fqn)

    def find_by_name(self, name: str) -> list[Symbol]:
        """Find all symbols with given short name."""
        return self._by_name.get(name, [])

    def find_by_prefix(self, prefix: str) -> list[Symbol]:
        """Find all symbols whose FQN starts with prefix."""
        return [s for fqn, s in self._by_fqn.items() if fqn.startswith(prefix)]

    def find_by_file(self, file: str) -> list[Symbol]:
        """Get all symbols in a file."""
        return self._by_file.get(file, [])

    def find_by_type(self, sym_type: str) -> list[Symbol]:
        """Get all symbols of a type (class, function, method)."""
        return self._by_type.get(sym_type, [])

    def search(self, query: str) -> list[Symbol]:
        """Search symbols by name or FQN substring."""
        query_lower = query.lower()
        results = []
        for fqn, symbol in self._by_fqn.items():
            if query_lower in fqn.lower() or query_lower in symbol.name.lower():
                results.append(symbol)
        return results

    def __len__(self) -> int:
        return len(self._by_fqn)

    def __iter__(self) -> Iterator[Symbol]:
        return iter(self._by_fqn.values())

    def __contains__(self, fqn: str) -> bool:
        return fqn in self._by_fqn
