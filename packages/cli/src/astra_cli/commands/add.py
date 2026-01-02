"""astra add <feature> - Add a feature to existing project."""

from rich.console import Console
import typer

from astra_cli.engine.deps import update_dependencies
from astra_cli.engine.features import get_add_feature_plan, validate_feature
from astra_cli.engine.project import discover_project, load_project_config, save_project_config
from astra_cli.engine.templates import apply_feature_plan


console = Console()


def add_feature(
    feature: str = typer.Argument(
        ..., help="Feature to add (e.g., rate-limit, ui, observability-otel)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing files",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be added without adding",
    ),
):
    """Add a feature to the current Astra project."""
    # Discover project
    project_path = discover_project()
    if not project_path:
        console.print("[red]Error: No Astra project found in this directory or parents.[/red]")
        console.print("[dim]Tip: Run `astra init server` to create one.[/dim]")
        raise typer.Exit(1)

    # Load config
    config = load_project_config(project_path)

    # Validate feature
    error = validate_feature(feature)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(1)

    # Check if already enabled
    feature_key = feature.replace(" ", "-")
    if feature_key in config.get("features", {}):
        console.print(f"[yellow]Feature '{feature}' is already enabled.[/yellow]")
        return

    # Get add plan
    plan = get_add_feature_plan(config, feature_key)

    # Check conflicts
    if plan.conflicts:
        console.print(
            f"[red]Error: Feature '{feature}' conflicts with: {', '.join(plan.conflicts)}[/red]"
        )
        console.print(f"[dim]Tip: Run `astra remove {plan.conflicts[0]}` first.[/dim]")
        raise typer.Exit(1)

    if dry_run:
        console.print(f"\n[bold yellow][DRY RUN][/bold yellow] Would add '{feature}':\n")
        if plan.files_to_add:
            console.print("[bold]📁 Files to create:[/bold]")
            for f in plan.files_to_add:
                console.print(f"   → {f}")
        if plan.deps_to_add:
            console.print("\n[bold]📦 Dependencies to add:[/bold]")
            for dep in plan.deps_to_add:
                console.print(f"   → {dep}")
        console.print("\n[dim]No changes made. Remove --dry-run to apply.[/dim]")
        return

    # Apply feature
    context = {
        "project_name": config["project"]["name"],
        "features": config.get("features", {}),
        **config.get("features", {}),
    }

    created_files = apply_feature_plan(
        project_path=project_path,
        plan=plan,
        context=context,
        force=force,
    )

    # Update dependencies
    if plan.deps_to_add:
        update_dependencies(project_path, plan.deps_to_add)

    # Update config
    config.setdefault("features", {})[feature_key] = True
    save_project_config(project_path, config)

    # Success output
    console.print(f"\n[bold green]✅ Added {feature}[/bold green]\n")
    for f in created_files:
        console.print(f"   → {f}")
    if plan.deps_to_add:
        console.print(f"\n[dim]Updated dependencies: {', '.join(plan.deps_to_add)}[/dim]")
