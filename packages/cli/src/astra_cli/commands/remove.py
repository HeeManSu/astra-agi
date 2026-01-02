"""astra remove <feature> - Remove a feature from project."""

from rich.console import Console
from rich.prompt import Confirm
import typer

from astra_cli.engine.deps import remove_dependencies
from astra_cli.engine.features import PROTECTED_FEATURES, get_remove_feature_plan
from astra_cli.engine.project import discover_project, load_project_config, save_project_config
from astra_cli.engine.templates import remove_feature_files


console = Console()


def remove_feature(
    feature: str = typer.Argument(..., help="Feature to remove"),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be removed without removing",
    ),
):
    """Remove a feature from the current Astra project."""
    # Discover project
    project_path = discover_project()
    if not project_path:
        console.print("[red]Error: No Astra project found in this directory or parents.[/red]")
        console.print("[dim]Tip: Run `astra init server` to create one.[/dim]")
        raise typer.Exit(1)

    # Load config
    config = load_project_config(project_path)

    # Check protected features
    feature_key = feature.replace(" ", "-")
    if feature_key in PROTECTED_FEATURES:
        console.print(f"[red]Error: Cannot remove protected feature '{feature}'[/red]")
        raise typer.Exit(1)

    # Check if feature exists
    if feature_key not in config.get("features", {}):
        console.print(f"[yellow]Feature '{feature}' is not enabled.[/yellow]")
        return

    # Get remove plan
    plan = get_remove_feature_plan(config, feature_key)

    if dry_run:
        console.print(f"\n[bold yellow][DRY RUN][/bold yellow] Would remove '{feature}':\n")
        if plan.files_to_remove:
            console.print("[bold]📁 Files to delete:[/bold]")
            for f in plan.files_to_remove:
                console.print(f"   ✗ {f}")
        if plan.deps_to_remove:
            console.print("\n[bold]📦 Dependencies to remove:[/bold]")
            for dep in plan.deps_to_remove:
                console.print(f"   ✗ {dep}")
        console.print("\n[dim]No changes made. Remove --dry-run to apply.[/dim]")
        return

    # Confirm removal
    if not force:
        confirmed = Confirm.ask(
            f"Remove feature '{feature}'? This will delete files.",
            default=False,
        )
        if not confirmed:
            console.print("[dim]Cancelled.[/dim]")
            return

    # Remove files
    removed_files = remove_feature_files(project_path, plan)

    # Remove dependencies
    if plan.deps_to_remove:
        remove_dependencies(project_path, plan.deps_to_remove)

    # Update config
    del config["features"][feature_key]
    save_project_config(project_path, config)

    # Success output
    console.print(f"\n[bold green]✅ Removed {feature}[/bold green]\n")
    for f in removed_files:
        console.print(f"   ✗ {f}")
