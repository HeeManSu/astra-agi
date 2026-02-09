# ruff: noqa: TID252
"""Wiki page generator for Limca.

Generates markdown wiki pages with Mermaid diagrams and source citations.
"""

import os
from typing import Any

from .planner import PagePlan


class WikiGenerator:
    """Generates wiki markdown pages from page plans."""

    def __init__(
        self,
        output_dir: str,
        index: Any = None,
        repo_notes: list[dict] | None = None,
    ) -> None:
        """Initialize wiki generator.

        Args:
            output_dir: Directory to write wiki pages
            index: CodeIndex for fetching content
            repo_notes: Optional context notes about the repo
        """
        self.output_dir = output_dir
        self.index = index
        self.repo_notes = repo_notes or []
        os.makedirs(output_dir, exist_ok=True)

    def generate_all(self, plans: list[PagePlan]) -> list[str]:
        """Generate all wiki pages from plans.

        Args:
            plans: List of PagePlan objects

        Returns:
            List of generated file paths
        """
        generated = []

        # Generate index page
        index_path = self._generate_index(plans)
        generated.append(index_path)

        # Generate each page
        for plan in plans:
            path = self.generate_page(plan)
            generated.append(path)

        return generated

    def _generate_index(self, plans: list[PagePlan]) -> str:
        """Generate index.md with table of contents."""
        lines = ["# Wiki Index", ""]

        # Add repo notes if present
        if self.repo_notes:
            lines.append("## About This Repository")
            lines.append("")
            for note in self.repo_notes:
                content = note.get("content", "")
                lines.append(f"> {content}")
                lines.append("")

        # Build hierarchy
        hierarchy = self._build_hierarchy(plans)

        lines.append("## Pages")
        lines.append("")

        # Render top-level pages
        for title in hierarchy.get("__root__", []):
            slug = self._title_to_slug(title)
            lines.append(f"- [{title}]({slug}.md)")

            # Render children
            for child in hierarchy.get(title, []):
                child_slug = self._title_to_slug(child)
                lines.append(f"  - [{child}]({child_slug}.md)")

        content = "\n".join(lines)
        path = os.path.join(self.output_dir, "index.md")

        with open(path, "w") as f:
            f.write(content)

        return path

    def generate_page(self, plan: PagePlan) -> str:
        """Generate a single wiki page.

        Args:
            plan: PagePlan with page details

        Returns:
            Path to generated file
        """
        lines = [f"# {plan.title}", ""]

        # Purpose
        lines.append(f"_{plan.purpose}_")
        lines.append("")

        # Summary section
        lines.append("## Summary")
        lines.append("")
        lines.append(self._generate_summary(plan))
        lines.append("")

        # Diagram
        if plan.symbols:
            lines.append("## Architecture")
            lines.append("")
            lines.append(self._generate_diagram(plan))
            lines.append("")

        # Key components
        if plan.symbols:
            lines.append("## Key Components")
            lines.append("")
            lines.extend(self._generate_components(plan))
            lines.append("")

        # Source files
        if plan.files:
            lines.append("## Source Files")
            lines.append("")
            for file in plan.files[:10]:  # Limit
                lines.append(f"- [{file}](file://{file})")
            lines.append("")

        content = "\n".join(lines)
        slug = self._title_to_slug(plan.title)
        path = os.path.join(self.output_dir, f"{slug}.md")

        with open(path, "w") as f:
            f.write(content)

        return path

    def _generate_summary(self, plan: PagePlan) -> str:
        """Generate summary paragraph for a page."""
        if not self.index:
            return f"This page covers {plan.purpose.lower()}."

        # Count files and symbols
        num_files = len(plan.files) if plan.files else 0
        num_symbols = len(plan.symbols) if plan.symbols else 0

        return f"This section contains {num_files} files with {num_symbols} symbols. {plan.purpose}"

    def _generate_diagram(self, plan: PagePlan) -> str:
        """Generate Mermaid diagram for the page."""
        if not plan.symbols:
            return ""

        lines = ["```mermaid", "flowchart TD"]

        # Simple diagram showing symbols
        seen = set()
        for i, sym in enumerate(plan.symbols[:10]):
            name = sym.split(".")[-1]  # Get short name
            if name in seen:
                continue
            seen.add(name)

            node_id = f"n{i}"
            lines.append(f"    {node_id}[{name}]")

        lines.append("```")
        return "\n".join(lines)

    def _generate_components(self, plan: PagePlan) -> list[str]:
        """Generate key components table."""
        lines = ["| Component | Type | File |", "|-----------|------|------|"]

        for sym in plan.symbols[:10]:
            parts = sym.split(".")
            name = parts[-1]
            sym_type = "function" if name[0].islower() else "class"
            file = plan.files[0] if plan.files else "unknown"

            lines.append(f"| {name} | {sym_type} | {file} |")

        return lines

    def _build_hierarchy(self, plans: list[PagePlan]) -> dict[str, list[str]]:
        """Build parent -> children mapping."""
        hierarchy: dict[str, list[str]] = {"__root__": []}

        for plan in plans:
            if plan.parent is None:
                hierarchy["__root__"].append(plan.title)
            else:
                if plan.parent not in hierarchy:
                    hierarchy[plan.parent] = []
                hierarchy[plan.parent].append(plan.title)

        return hierarchy

    def _title_to_slug(self, title: str) -> str:
        """Convert title to URL-safe slug."""
        return title.lower().replace(" ", "-").replace("_", "-")
