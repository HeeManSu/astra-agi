"""Project Engine - astra.json management and project discovery."""

import json
from pathlib import Path
from typing import Any


ASTRA_CONFIG_FILE = "astra.json"
SCHEMA_VERSION = "1.0"


def discover_project() -> Path | None:
    """
    Find project root by walking up directory tree looking for astra.json.

    Returns:
        Path to project root, or None if not found.
    """
    current = Path.cwd()

    while current != current.parent:
        config_path = current / ASTRA_CONFIG_FILE
        if config_path.exists():
            return current
        current = current.parent

    # Check root
    if (current / ASTRA_CONFIG_FILE).exists():
        return current

    return None


def load_project_config(project_path: Path) -> dict[str, Any]:
    """
    Load and validate astra.json from project path.

    Args:
        project_path: Path to project root

    Returns:
        Parsed config dict

    Raises:
        ValueError: If config is invalid
    """
    config_path = project_path / ASTRA_CONFIG_FILE

    if not config_path.exists():
        raise ValueError(f"No {ASTRA_CONFIG_FILE} found in {project_path}")

    with open(config_path) as f:
        config = json.load(f)

    # Validate schema version
    schema_version = config.get("schema_version", "0.0")
    if schema_version != SCHEMA_VERSION:
        # Future: handle migrations
        pass

    return config


def save_project_config(project_path: Path, config: dict[str, Any]) -> None:
    """
    Save config to astra.json.

    Args:
        project_path: Path to project root
        config: Config dict to save
    """
    config_path = project_path / ASTRA_CONFIG_FILE

    # Ensure schema version
    config["schema_version"] = SCHEMA_VERSION

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def create_project_config(
    name: str,
    project_type: str = "server",
    features: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a new project config.

    Args:
        name: Project name
        project_type: Type of project (server)
        features: Initial features dict

    Returns:
        New config dict
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "project": {
            "name": name,
            "type": project_type,
        },
        "features": features or {"core": True},
        "runtime": {
            "entrypoint": "app.main:app",
        },
    }
