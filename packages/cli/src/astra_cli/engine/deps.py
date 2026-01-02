"""Dependency Engine - Merge dependencies into pyproject.toml."""

from pathlib import Path
from typing import Any

import tomlkit


def update_dependencies(project_path: Path, deps_to_add: list[str]) -> None:
    """
    Add dependencies to pyproject.toml.

    Args:
        project_path: Path to project root
        deps_to_add: List of dependencies to add
    """
    pyproject_path = project_path / "pyproject.toml"

    if not pyproject_path.exists():
        return

    with open(pyproject_path) as f:
        doc = tomlkit.load(f)

    # Get or create dependencies list
    project_table: dict[str, Any] = doc.get("project", {})  # type: ignore[assignment]
    if not project_table:
        doc["project"] = {}
        project_table = doc["project"]  # type: ignore[assignment]

    deps_list: list[str] = project_table.get("dependencies", [])  # type: ignore[assignment]
    if not deps_list:
        project_table["dependencies"] = []
        deps_list = project_table["dependencies"]  # type: ignore[assignment]

    current_deps = set(deps_list)

    # Add new deps (avoid duplicates)
    for dep in deps_to_add:
        dep_name = dep.split("[")[0].split(">=")[0].split("==")[0]
        already_present = any(
            d.split("[")[0].split(">=")[0].split("==")[0] == dep_name for d in current_deps
        )
        if not already_present:
            deps_list.append(dep)

    with open(pyproject_path, "w") as f:
        tomlkit.dump(doc, f)


def remove_dependencies(project_path: Path, deps_to_remove: list[str]) -> None:
    """
    Remove dependencies from pyproject.toml.

    Args:
        project_path: Path to project root
        deps_to_remove: List of dependencies to remove
    """
    pyproject_path = project_path / "pyproject.toml"

    if not pyproject_path.exists():
        return

    with open(pyproject_path) as f:
        doc = tomlkit.load(f)

    project_table: dict[str, Any] = doc.get("project", {})  # type: ignore[assignment]
    if not project_table:
        return

    deps_list: list[str] = project_table.get("dependencies", [])  # type: ignore[assignment]
    if not deps_list:
        return

    remove_names = {dep.split("[")[0].split(">=")[0].split("==")[0] for dep in deps_to_remove}

    # Filter and replace
    project_table["dependencies"] = [
        dep
        for dep in deps_list
        if dep.split("[")[0].split(">=")[0].split("==")[0] not in remove_names
    ]

    with open(pyproject_path, "w") as f:
        tomlkit.dump(doc, f)
