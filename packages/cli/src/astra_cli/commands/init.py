"""astra init server - Scaffold a new Astra server project."""

from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt
import typer

from astra_cli.engine.features import get_feature_plan
from astra_cli.engine.project import create_project_config, save_project_config
from astra_cli.engine.templates import render_project


app = typer.Typer(help="Initialize a new project")
console = Console()


@app.command("server")
def init_server(
    name: str = typer.Argument(None, help="Project name"),
    auth: str = typer.Option(
        None,
        "--auth",
        "-a",
        help="Authentication type: none, api-key, jwt",
    ),
    no_interactive: bool = typer.Option(
        False,
        "--no-interactive",
        "-y",
        help="Skip interactive prompts",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be created without creating",
    ),
):
    """Scaffold a new Astra server project."""
    # Interactive prompts if not provided
    if not no_interactive:
        if not name:
            name = Prompt.ask(
                "[bold cyan]Project name[/bold cyan]",
                default="astra-server",
            )
        if not auth:
            auth = Prompt.ask(
                "[bold cyan]Authentication[/bold cyan]",
                choices=["none", "api-key", "jwt"],
                default="none",
            )

    # Validate required fields
    if not name:
        console.print("[red]Error: Project name is required[/red]")
        raise typer.Exit(1)

    auth = auth or "none"

    # Check if directory exists
    project_path = Path.cwd() / name
    if project_path.exists() and not dry_run:
        console.print(f"[red]Error: Directory '{name}' already exists[/red]")
        raise typer.Exit(1)

    # Determine features
    features: dict[str, bool | str] = {"core": True}
    if auth != "none":
        features["auth"] = auth

    # Create project config
    config = create_project_config(
        name=name,
        project_type="server",
        features=features,
    )

    # Get feature plan
    plan = get_feature_plan(config)

    if dry_run:
        console.print("\n[bold yellow][DRY RUN][/bold yellow] Would create:\n")
        console.print(f"[bold]📁 {name}/[/bold]")
        for f in plan.files_to_add:
            console.print(f"   → {f.replace('.j2', '')}")
        if plan.deps_to_add:
            console.print("\n[bold]📦 Dependencies:[/bold]")
            for dep in plan.deps_to_add:
                console.print(f"   → {dep}")
        console.print("\n[dim]No changes made. Remove --dry-run to apply.[/dim]")
        return

    # Render project
    created_files = render_project(
        project_path=project_path,
        plan=plan,
        context={
            "project_name": name,
            "auth_type": auth,
            "features": features,
            "has_auth": auth != "none",
        },
    )

    # Save astra.json
    save_project_config(project_path, config)

    # Success output
    console.print(f"\n[bold green]✅ Created {name}/[/bold green]\n")
    for f in created_files:
        console.print(f"   → {f}")

    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  [cyan]cd {name}[/cyan]")
    console.print("  [cyan]pip install -e .[/cyan]")
    console.print("  [cyan]astra dev[/cyan]")
