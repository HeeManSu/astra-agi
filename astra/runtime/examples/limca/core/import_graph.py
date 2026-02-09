"""Import graph for file dependencies."""

from dataclasses import dataclass, field


@dataclass
class ImportGraph:
    """Track import/dependency relationships between files."""

    _imports: dict[str, set[str]] = field(default_factory=dict)  # file → imported modules
    _aliases: dict[str, dict[str, str]] = field(default_factory=dict)  # file → {alias: fqn}
    _reverse: dict[str, set[str]] = field(default_factory=dict)  # module → importing files

    def add_import(self, file: str, module: str, alias: str | None = None) -> None:
        """Add an import.

        Args:
            file: File that contains the import
            module: Module being imported (fully qualified)
            alias: Optional alias used for the import
        """
        if file not in self._imports:
            self._imports[file] = set()
        self._imports[file].add(module)

        if alias:
            if file not in self._aliases:
                self._aliases[file] = {}
            self._aliases[file][alias] = module

        if module not in self._reverse:
            self._reverse[module] = set()
        self._reverse[module].add(file)

    def get_imports(self, file: str) -> set[str]:
        """Get all modules imported by a file."""
        return self._imports.get(file, set())

    def get_importers(self, module: str) -> set[str]:
        """Get all files that import a module."""
        return self._reverse.get(module, set())

    def resolve_alias(self, file: str, alias: str) -> str | None:
        """Resolve an alias to its full module name."""
        aliases = self._aliases.get(file, {})
        return aliases.get(alias)

    def get_dependencies(
        self,
        file: str,
        depth: int = 3,
        visited: set[str] | None = None,
        max_files: int = 50,
    ) -> set[str]:
        """Get all dependencies of a file up to specified depth."""
        if visited is None:
            visited = set()

        if depth <= 0 or file in visited or len(visited) >= max_files:
            return set()

        visited.add(file)
        deps = self.get_imports(file)
        result = set(deps)

        for dep in deps:
            if len(visited) >= max_files:
                break
            sub_deps = self.get_dependencies(dep, depth - 1, visited, max_files)
            result.update(sub_deps)

        return result

    def get_dependents(self, file: str) -> set[str]:
        """Get files that depend on (import) this file."""
        return self.get_importers(file)

    def __len__(self) -> int:
        return sum(len(imports) for imports in self._imports.values())
