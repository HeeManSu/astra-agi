"""Astra CLI main entry point."""

from rich.console import Console
import typer

from astra_cli.commands import add, dev, init, remove, sync


app = typer.Typer(
    name="astra",
    help="Astra CLI - Scaffold and manage Astra server projects",
    no_args_is_help=True,
)

console = Console()

# Register command groups
app.add_typer(init.app, name="init", help="Initialize a new project")
app.command(name="add")(add.add_feature)
app.command(name="remove")(remove.remove_feature)
app.command(name="dev")(dev.run_dev)
app.command(name="sync")(sync.sync)


@app.callback()
def main():
    """Astra CLI - Code generation and project management for Astra servers."""


if __name__ == "__main__":
    app()
