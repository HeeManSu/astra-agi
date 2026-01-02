"""Unit tests for astra.json corruption handling."""

import json

from astra_cli.engine.project import load_project_config, save_project_config
import pytest


@pytest.mark.unit
class TestConfigCorruption:
    """Test handling of corrupted or malformed astra.json."""

    def test_features_is_list_instead_of_dict(self, tmp_path):
        """Should error clearly when features is a list."""
        project = tmp_path / "bad-project"
        project.mkdir()

        bad_config = {
            "schema_version": "1.0",
            "project": {"name": "test", "type": "server"},
            "features": ["core", "auth-jwt"],  # Should be dict!
        }
        (project / "astra.json").write_text(json.dumps(bad_config))

        # Should handle gracefully or error clearly
        # This will likely fail during feature validation
        from astra_cli.engine.features import validate_features_in_config

        config = load_project_config(project)
        # Features being a list will cause issues - test that we handle it
        try:
            validate_features_in_config(config)
            pytest.fail("Should have raised an exception for list features")
        except (TypeError, AttributeError, KeyError):
            # Expected - features as list causes type error
            pass

    def test_features_is_null(self, tmp_path):
        """Should handle when features is null/None."""
        project = tmp_path / "null-project"
        project.mkdir()

        bad_config = {
            "schema_version": "1.0",
            "project": {"name": "test", "type": "server"},
            "features": None,
        }
        (project / "astra.json").write_text(json.dumps(bad_config))

        from astra_cli.engine.features import validate_features_in_config

        config = load_project_config(project)
        # Should handle None gracefully
        errors = validate_features_in_config(config)
        # May or may not error, but shouldn't crash
        assert isinstance(errors, list)

    def test_auth_wrong_type_bool_instead_of_string(self, tmp_path):
        """Should error when auth is bool instead of string."""
        project = tmp_path / "auth-bool"
        project.mkdir()

        bad_config = {
            "schema_version": "1.0",
            "project": {"name": "test", "type": "server"},
            "features": {
                "core": True,
                "auth": True,  # Should be "jwt" or "api-key"
            },
        }
        (project / "astra.json").write_text(json.dumps(bad_config))

        from astra_cli.engine.features import get_feature_plan

        config = load_project_config(project)
        # Should handle gracefully - bool auth type won't match registry
        plan = get_feature_plan(config)
        # Plan should complete but not add auth files
        assert "app/auth/jwt.py.j2" not in plan.files_to_add

    def test_project_type_not_server(self, tmp_path):
        """Should validate project.type is 'server'."""
        project = tmp_path / "wrong-type"
        project.mkdir()

        bad_config = {
            "schema_version": "1.0",
            "project": {"name": "test", "type": "client"},
            "features": {"core": True},
        }
        (project / "astra.json").write_text(json.dumps(bad_config))

        # Currently we don't validate project.type, but we should
        config = load_project_config(project)
        assert config["project"]["type"] == "client"
        # This test documents current behavior - could add validation

    def test_missing_runtime_entrypoint(self, tmp_path):
        """Should handle missing runtime.entrypoint."""
        project = tmp_path / "no-runtime"
        project.mkdir()

        bad_config = {
            "schema_version": "1.0",
            "project": {"name": "test", "type": "server"},
            "features": {"core": True},
            # Missing runtime section
        }
        (project / "astra.json").write_text(json.dumps(bad_config))

        config = load_project_config(project)
        # Should load fine - runtime is optional in config
        assert "runtime" not in config or config.get("runtime") is None

    def test_missing_project_name(self, tmp_path):
        """Should handle missing project.name."""
        project = tmp_path / "no-name"
        project.mkdir()

        bad_config = {
            "schema_version": "1.0",
            "project": {"type": "server"},  # Missing name
            "features": {"core": True},
        }
        (project / "astra.json").write_text(json.dumps(bad_config))

        config = load_project_config(project)
        # Should load - name is in project dict
        assert "name" not in config["project"]

    def test_completely_empty_config(self, tmp_path):
        """Should handle empty JSON object."""
        project = tmp_path / "empty"
        project.mkdir()

        (project / "astra.json").write_text("{}")

        config = load_project_config(project)
        assert config == {}

        # Validation should catch this
        from astra_cli.engine.features import validate_features_in_config

        # Empty config will fail validation
        errors = validate_features_in_config(config)
        # Should not crash, may return errors
        assert isinstance(errors, list)

    def test_extra_unknown_top_level_keys(self, tmp_path):
        """Should ignore unknown top-level keys (forward compatibility)."""
        project = tmp_path / "extra-keys"
        project.mkdir()

        config_with_extras = {
            "schema_version": "1.0",
            "project": {"name": "test", "type": "server"},
            "features": {"core": True},
            "future_key": "future_value",
            "another_unknown": {"nested": "data"},
        }
        (project / "astra.json").write_text(json.dumps(config_with_extras))

        config = load_project_config(project)
        # Should load fine - we ignore unknown keys
        assert config["future_key"] == "future_value"
        assert config["another_unknown"]["nested"] == "data"


@pytest.mark.unit
class TestConfigSaving:
    """Test config saving handles edge cases."""

    def test_save_preserves_unknown_keys(self, tmp_path):
        """Should preserve unknown keys when saving."""
        project = tmp_path / "preserve"
        project.mkdir()

        original = {
            "schema_version": "1.0",
            "project": {"name": "test", "type": "server"},
            "features": {"core": True},
            "custom_field": "my_data",
        }
        (project / "astra.json").write_text(json.dumps(original))

        # Load and save
        config = load_project_config(project)
        save_project_config(project, config)

        # Reload and check
        saved = json.loads((project / "astra.json").read_text())
        assert saved["custom_field"] == "my_data"

    def test_save_ensures_schema_version(self, tmp_path):
        """Should ensure schema_version is always set."""
        project = tmp_path / "ensure-version"
        project.mkdir()

        config = {
            "project": {"name": "test"},
            "features": {"core": True},
        }

        save_project_config(project, config)

        saved = json.loads((project / "astra.json").read_text())
        assert "schema_version" in saved
        assert saved["schema_version"] == "1.0"
