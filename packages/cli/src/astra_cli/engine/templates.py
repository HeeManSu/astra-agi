"""Template Engine - Jinja rendering and safe file I/O."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from astra_cli.engine.features import FeaturePlan


# Setup Jinja environment
env = Environment(
    loader=PackageLoader("astra_cli", "templates/server"),
    autoescape=select_autoescape(),
    keep_trailing_newline=True,
)


def render_template(template_name: str, context: dict[str, Any]) -> str:
    """
    Render a single template with context.

    Args:
        template_name: Template filename (e.g., "main.py.j2")
        context: Template context dict

    Returns:
        Rendered template content
    """
    template = env.get_template(template_name)
    return template.render(**context)


def render_project(
    project_path: Path,
    plan: FeaturePlan,
    context: dict[str, Any],
) -> list[str]:
    """
    Render all templates for a new project.

    Args:
        project_path: Path where project will be created
        plan: Feature plan with files to create
        context: Template context

    Returns:
        List of created file paths (relative)
    """
    created_files = []

    for template_file in plan.files_to_add:
        # Determine output path (strip .j2)
        output_name = template_file.replace(".j2", "")
        output_path = project_path / output_name

        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Render and write
        try:
            content = render_template(template_file, context)
            output_path.write_text(content)
            created_files.append(output_name)
        except Exception as e:
            # Log but continue
            print(f"Warning: Failed to render {template_file}: {e}")

    return created_files


def apply_feature_plan(
    project_path: Path,
    plan: FeaturePlan,
    context: dict[str, Any],
    force: bool = False,
) -> list[str]:
    """
    Apply a feature plan to an existing project.

    Args:
        project_path: Path to project root
        plan: Feature plan with files to create
        context: Template context
        force: If True, overwrite existing files

    Returns:
        List of created/updated file paths
    """
    created_files = []

    for template_file in plan.files_to_add:
        output_name = template_file.replace(".j2", "")
        output_path = project_path / output_name

        # Skip existing files unless force
        if output_path.exists() and not force:
            continue

        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Render and write
        try:
            content = render_template(template_file, context)
            output_path.write_text(content)
            created_files.append(output_name)
        except Exception as e:
            print(f"Warning: Failed to render {template_file}: {e}")

    return created_files


def remove_feature_files(
    project_path: Path,
    plan: FeaturePlan,
) -> list[str]:
    """
    Remove files for a feature.

    Args:
        project_path: Path to project root
        plan: Feature plan with files to remove

    Returns:
        List of removed file paths
    """
    removed_files = []

    for file_path in plan.files_to_remove:
        full_path = project_path / file_path

        if full_path.exists():
            full_path.unlink()
            removed_files.append(file_path)

            # Remove empty parent directories
            parent = full_path.parent
            while parent != project_path:
                try:
                    parent.rmdir()  # Only removes if empty
                    parent = parent.parent
                except OSError:
                    break

    return removed_files
