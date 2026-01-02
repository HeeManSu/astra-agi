"""astra sync - Reconcile state with code."""

from rich.console import Console
import typer

from astra_cli.engine.features import get_sync_plan, validate_features_in_config
from astra_cli.engine.project import (
    SCHEMA_VERSION,
    discover_project,
    load_project_config,
    save_project_config,
)
from astra_cli.engine.templates import apply_feature_plan


console = Console()


def sync(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be synced without applying",
    ),
):
    """
    Reconcile project state with code.

    This command:
    - Validates astra.json schema and features
    - Adds missing template files
    - Never deletes or overwrites user code
    """
    # Discover project
    project_path = discover_project()
    if not project_path:
        console.print("[red]Error: No Astra project found in this directory or parents.[/red]")
        console.print("[dim]Tip: Run `astra init server` to create one.[/dim]")
        raise typer.Exit(1)

    # Load config
    config = load_project_config(project_path)

    # Check schema version
    schema_version = config.get("schema_version", "0.0")
    if schema_version != SCHEMA_VERSION:
        console.print(
            f"[yellow]WARN: astra.json schema v{schema_version} (CLI supports v{SCHEMA_VERSION})[/yellow]"
        )
        config["schema_version"] = SCHEMA_VERSION

    # Validate features
    errors = validate_features_in_config(config)
    if errors:
        console.print("\n[red]Validation errors:[/red]")
        for error in errors:
            console.print(f"  • {error}")
        console.print("\n[dim]Fix the errors in astra.json and run `astra sync` again.[/dim]")
        raise typer.Exit(1)

    # Get sync plan (add missing files only)
    plan = get_sync_plan(config, project_path)

    if not plan.files_to_add:
        console.print("[green]✅ Project is in sync. No changes needed.[/green]")
        return

    if dry_run:
        console.print("\n[bold yellow][DRY RUN][/bold yellow] Would add missing files:\n")
        for f in plan.files_to_add:
            console.print(f"   → {f.replace('.j2', '')}")
        console.print("\n[dim]No changes made. Remove --dry-run to apply.[/dim]")
        return

    # Apply missing files
    context = {
        "project_name": config["project"]["name"],
        "features": config.get("features", {}),
        "auth_type": config.get("features", {}).get("auth", "none"),
        "has_auth": config.get("features", {}).get("auth", "none") != "none",
    }

    created_files = apply_feature_plan(
        project_path=project_path,
        plan=plan,
        context=context,
        force=False,  # Never overwrite in sync
    )

    # Save updated config (schema version update)
    save_project_config(project_path, config)

    # Success output
    if created_files:
        console.print("\n[bold green]✅ Synced project[/bold green]\n")
        console.print("[bold]Added missing files:[/bold]")
        for f in created_files:
            console.print(f"   → {f}")
    else:
        console.print("[green]✅ Project is in sync. No changes needed.[/green]")
