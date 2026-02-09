# ruff: noqa: TID252
"""Symbol resolver for mapping unqualified names to FQNs."""

from .import_graph import ImportGraph
from .parser import Call
from .symbols import SymbolTable


class SymbolResolver:
    """Resolves unqualified names to fully qualified names."""

    def __init__(self, symbols: SymbolTable, imports: ImportGraph):
        """Initialize resolver.

        Args:
            symbols: Symbol table with all known symbols
            imports: Import graph for resolving imported names
        """
        self.symbols = symbols
        self.imports = imports

    def resolve(self, call: Call) -> str | None:
        """Resolve a call target to FQN.

        Handles:
        - self.method → lookup in caller's class
        - ClassName.method → lookup by class name
        - module.func → lookup by module
        - func() → lookup in same module or imports

        Args:
            call: Call object with caller_fqn and callee_raw

        Returns:
            Resolved FQN or None if unresolvable
        """
        callee = call.callee_raw
        caller = call.caller_fqn

        # Handle self.method
        if callee.startswith("self."):
            method_name = callee[5:]  # Remove "self."
            return self._resolve_self_method(caller, method_name)

        # Handle this.method (JavaScript)
        if callee.startswith("this."):
            method_name = callee[5:]
            return self._resolve_self_method(caller, method_name)

        # Handle qualified calls: ClassName.method or module.func
        if "." in callee:
            return self._resolve_qualified(callee, call.file)

        # Handle simple function calls
        return self._resolve_simple(callee, caller, call.file)

    def _resolve_self_method(self, caller_fqn: str, method_name: str) -> str | None:
        """Resolve self.method to Class.method."""
        # Find the class containing this method
        # caller_fqn might be: module.Class.method
        parts = caller_fqn.split(".")

        # Try each parent level until we find a class
        for i in range(len(parts) - 1, 0, -1):
            parent_fqn = ".".join(parts[:i])
            parent = self.symbols.get_by_fqn(parent_fqn)
            if parent and parent.type == "class":
                # Look for method in this class
                method_fqn = f"{parent_fqn}.{method_name}"
                if self.symbols.get_by_fqn(method_fqn):
                    return method_fqn
                # Might be inherited - return best guess
                return method_fqn

        return None

    def _resolve_qualified(self, callee: str, file: str) -> str | None:
        """Resolve qualified name like ClassName.method."""
        # First check if it's a direct FQN match
        if self.symbols.get_by_fqn(callee):
            return callee

        # Try to resolve the first part via imports
        parts = callee.split(".")
        first_part = parts[0]

        # Check if first part is an import alias
        resolved = self.imports.resolve_alias(file, first_part)
        if resolved:
            # Replace alias with resolved module
            full_fqn = ".".join([resolved, *parts[1:]])
            if self.symbols.get_by_fqn(full_fqn):
                return full_fqn

        # Try to find symbol by name
        candidates = self.symbols.find_by_name(first_part)
        for candidate in candidates:
            potential_fqn = f"{candidate.fqn}.{'.'.join(parts[1:])}"
            if self.symbols.get_by_fqn(potential_fqn):
                return potential_fqn

        return None

    def _resolve_simple(self, callee: str, caller_fqn: str, file: str) -> str | None:
        """Resolve simple function call."""
        # Get module from caller_fqn
        parts = caller_fqn.split(".")

        # Try same module first
        for i in range(len(parts), 0, -1):
            module_prefix = ".".join(parts[:i])
            potential_fqn = f"{module_prefix}.{callee}"
            if self.symbols.get_by_fqn(potential_fqn):
                return potential_fqn

        # Check imports
        resolved = self.imports.resolve_alias(file, callee)
        if resolved and self.symbols.get_by_fqn(resolved):
            return resolved

        # Try to find by name (might have multiple matches)
        candidates = self.symbols.find_by_name(callee)
        if len(candidates) == 1:
            return candidates[0].fqn

        return None

    def resolve_all(self, calls: list[Call]) -> list[Call]:
        """Resolve all calls in a list.

        Args:
            calls: List of Call objects with unresolved callee_raw

        Returns:
            List of Call objects with callee_fqn populated where possible
        """
        for call in calls:
            call.callee_fqn = self.resolve(call)
        return calls
