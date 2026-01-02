"""astra dev - Run development server."""

import subprocess
import sys

from rich.console import Console
import typer

from astra_cli.engine.project import discover_project, load_project_config


console = Console()


def run_dev(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind"),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Enable auto-reload"),
):
    """Run the development server."""
    # Discover project
    project_path = discover_project()
    if not project_path:
        console.print("[red]Error: No Astra project found in this directory or parents.[/red]")
        console.print("[dim]Tip: Run `astra init server` to create one.[/dim]")
        raise typer.Exit(1)

    # Load config for entrypoint
    config = load_project_config(project_path)
    entrypoint = config.get("runtime", {}).get("entrypoint", "app.main:app")

    # Banner
    console.print("\n[bold blue]🚀 Starting Astra development server[/bold blue]\n")
    console.print(f"   [dim]Project:[/dim]  {config['project']['name']}")
    console.print(f"   [dim]Server:[/dim]   http://{host}:{port}")
    console.print(f"   [dim]Docs:[/dim]     http://{host}:{port}/docs")
    console.print(f"   [dim]Reload:[/dim]   {'enabled' if reload else 'disabled'}")
    console.print()

    # Build command
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        entrypoint,
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")

    # Run
    try:
        subprocess.run(cmd, cwd=project_path, check=True)
    except FileNotFoundError:
        console.print("[red]Error: uvicorn not found. Install with: pip install uvicorn[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Server stopped.[/dim]")
