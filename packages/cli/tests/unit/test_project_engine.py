"""Unit tests for Project Engine."""

import json
from pathlib import Path

from astra_cli.engine.project import (
    SCHEMA_VERSION,
    create_project_config,
    discover_project,
    load_project_config,
    save_project_config,
)
import pytest


@pytest.mark.unit
class TestProjectDiscovery:
    """Test project discovery logic."""

    def test_discover_project_in_root(self, temp_project):
        """Should find astra.json in project root."""
        # Change to project directory
        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(temp_project)
            result = discover_project()
            assert result == temp_project
        finally:
            os.chdir(original_cwd)

    def test_discover_project_nested(self, temp_project):
        """Should walk up and find astra.json."""
        # Create nested directory
        nested = temp_project / "app" / "api"
        nested.mkdir(parents=True)

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(nested)
            result = discover_project()
            assert result == temp_project
        finally:
            os.chdir(original_cwd)

    def test_discover_project_not_found(self, tmp_path):
        """Should return None when no project found."""
        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = discover_project()
            assert result is None
        finally:
            os.chdir(original_cwd)


@pytest.mark.unit
class TestConfigLoading:
    """Test config loading and validation."""

    def test_load_valid_config(self, temp_project, sample_config):
        """Should load valid astra.json."""
        config = load_project_config(temp_project)
        assert config == sample_config

    def test_load_missing_config(self, tmp_path):
        """Should raise error for missing config."""
        with pytest.raises(ValueError, match=r"No astra\.json found"):
            load_project_config(tmp_path)

    def test_load_invalid_json(self, tmp_path):
        """Should raise error for invalid JSON."""
        project = tmp_path / "bad-project"
        project.mkdir()
        (project / "astra.json").write_text("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            load_project_config(project)

    def test_save_config(self, tmp_path, sample_config):
        """Should save config to astra.json."""
        project = tmp_path / "save-test"
        project.mkdir()

        save_project_config(project, sample_config)

        saved = json.loads((project / "astra.json").read_text())
        assert saved == sample_config

    def test_save_adds_schema_version(self, tmp_path):
        """Should ensure schema_version is set."""
        project = tmp_path / "schema-test"
        project.mkdir()

        config = {"project": {"name": "test"}}
        save_project_config(project, config)

        saved = json.loads((project / "astra.json").read_text())
        assert saved["schema_version"] == SCHEMA_VERSION


@pytest.mark.unit
class TestConfigCreation:
    """Test config creation."""

    def test_create_minimal_config(self):
        """Should create minimal config."""
        config = create_project_config(name="my-project")

        assert config["schema_version"] == SCHEMA_VERSION
        assert config["project"]["name"] == "my-project"
        assert config["project"]["type"] == "server"
        assert config["features"]["core"] is True

    def test_create_with_features(self):
        """Should include custom features."""
        features = {"core": True, "auth": "jwt"}
        config = create_project_config(name="my-project", features=features)

        assert config["features"] == features
