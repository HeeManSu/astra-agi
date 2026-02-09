"""Wiki page planner for Limca.

Clusters files and generates page structure for wiki generation.
"""

from typing import Any

from ..config import WikiConfig


class PagePlan:
    """A planned wiki page with content sources."""

    def __init__(
        self,
        title: str,
        purpose: str,
        parent: str | None = None,
        files: list[str] | None = None,
        symbols: list[str] | None = None,
    ) -> None:
        self.title = title
        self.purpose = purpose
        self.parent = parent
        self.files = files or []
        self.symbols = symbols or []

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "purpose": self.purpose,
            "parent": self.parent,
            "files": self.files,
            "symbols": self.symbols,
        }


class WikiPlanner:
    """Plans wiki structure from code analysis or config."""

    def __init__(self, config: WikiConfig | None = None) -> None:
        self.config = config

    def plan_from_config(self) -> list[PagePlan]:
        """Generate page plans from explicit config.

        Returns:
            List of PagePlan objects based on wiki.json configuration
        """
        if not self.config or not self.config.pages:
            return []

        plans = []
        for page in self.config.pages:
            plans.append(
                PagePlan(
                    title=page.title,
                    purpose=page.purpose,
                    parent=page.parent,
                    files=page.files or [],
                )
            )
        return plans

    def plan_from_index(self, index: Any) -> list[PagePlan]:
        """Generate page plans automatically from code index.

        Clusters files by import relationships and generates pages.

        Args:
            index: CodeIndex from limca.core.indexer

        Returns:
            List of PagePlan objects
        """
        if not index:
            return []

        plans = []

        # 1. Overview page (always)
        plans.append(
            PagePlan(
                title="Overview",
                purpose="High-level system architecture and entry points",
                parent=None,
            )
        )

        # 2. Group files by top-level directories
        file_groups = self._group_by_directory(index)

        for group_name, files in file_groups.items():
            # Get symbols in these files
            symbols = self._get_symbols_for_files(index, files)

            plans.append(
                PagePlan(
                    title=group_name.title().replace("_", " "),
                    purpose=f"Components and functionality in {group_name}/",
                    parent="Overview",
                    files=files,
                    symbols=symbols,
                )
            )

        return plans

    def _group_by_directory(self, index: Any) -> dict[str, list[str]]:
        """Group files by their top-level directory."""
        groups: dict[str, list[str]] = {}

        # Get all indexed files
        if not hasattr(index, "symbols") or not hasattr(index.symbols, "symbols"):
            return groups

        seen_files = set()
        for sym in index.symbols.symbols.values():
            file_path = sym.file
            if file_path in seen_files:
                continue
            seen_files.add(file_path)

            # Get top-level directory
            parts = file_path.split("/")
            if len(parts) > 1:
                group = parts[0]
            else:
                group = "root"

            if group not in groups:
                groups[group] = []
            groups[group].append(file_path)

        return groups

    def _get_symbols_for_files(self, index: Any, files: list[str]) -> list[str]:
        """Get symbol FQNs for a list of files."""
        symbols = []

        if not hasattr(index, "symbols") or not hasattr(index.symbols, "symbols"):
            return symbols

        files_set = set(files)
        for fqn, sym in index.symbols.symbols.items():
            if sym.file in files_set:
                symbols.append(fqn)

        return symbols[:20]  # Limit to avoid overwhelming

    def merge_plans(
        self,
        config_plans: list[PagePlan],
        auto_plans: list[PagePlan],
    ) -> list[PagePlan]:
        """Merge config-based and auto-generated plans.

        Config pages take precedence.
        """
        # Use config pages as base
        config_titles = {p.title for p in config_plans}

        merged = list(config_plans)

        # Add auto plans that don't conflict
        for auto_plan in auto_plans:
            if auto_plan.title not in config_titles:
                merged.append(auto_plan)

        return merged
