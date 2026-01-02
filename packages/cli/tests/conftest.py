"""Pytest configuration and fixtures for Astra CLI tests."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Typer CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_config():
    """Sample astra.json configuration."""
    return {
        "schema_version": "1.0",
        "project": {
            "name": "test-project",
            "type": "server",
        },
        "features": {
            "core": True,
        },
        "runtime": {
            "entrypoint": "app.main:app",
        },
    }


@pytest.fixture
def temp_project(tmp_path, sample_config):
    """Create a temporary project with astra.json."""
    project_path = tmp_path / "test-project"
    project_path.mkdir()

    config_path = project_path / "astra.json"
    config_path.write_text(json.dumps(sample_config, indent=2))

    return project_path


@pytest.fixture
def temp_project_with_auth(tmp_path):
    """Create a temporary project with JWT auth."""
    project_path = tmp_path / "auth-project"
    project_path.mkdir()

    config = {
        "schema_version": "1.0",
        "project": {
            "name": "auth-project",
            "type": "server",
        },
        "features": {
            "core": True,
            "auth": "jwt",
        },
        "runtime": {
            "entrypoint": "app.main:app",
        },
    }

    config_path = project_path / "astra.json"
    config_path.write_text(json.dumps(config, indent=2))

    return project_path


def get_file_tree(path: Path, relative_to: Path | None = None) -> dict:
    """
    Get file tree structure for snapshot testing.

    Args:
        path: Root path to traverse
        relative_to: Make paths relative to this

    Returns:
        Dict mapping relative paths to file contents or 'DIR'
    """
    if relative_to is None:
        relative_to = path

    tree = {}
    for item in sorted(path.rglob("*")):
        rel_path = str(item.relative_to(relative_to))

        if item.is_file():
            # Store file content
            try:
                tree[rel_path] = item.read_text()
            except Exception:
                tree[rel_path] = "<binary>"
        else:
            tree[rel_path] = "<DIR>"

    return tree
