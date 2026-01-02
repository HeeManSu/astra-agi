"""Unit tests for Registry Integrity."""

from astra_cli.templates.registry import FEATURES
import pytest


@pytest.mark.unit
class TestRegistryIntegrity:
    """Test registry is well-formed and consistent."""

    def test_all_features_have_files_key(self):
        """Every feature must have a 'files' key."""
        for feature_name, feature_def in FEATURES.items():
            assert "files" in feature_def, f"Feature '{feature_name}' missing 'files' key"

    def test_no_empty_feature_definitions(self):
        """Feature definitions should not be completely empty."""
        for feature_name, feature_def in FEATURES.items():
            assert feature_def, f"Feature '{feature_name}' has empty definition"
            assert isinstance(feature_def, dict), f"Feature '{feature_name}' is not a dict"

    def test_files_is_list(self):
        """'files' key must be a list."""
        for feature_name, feature_def in FEATURES.items():
            files = feature_def.get("files")
            assert isinstance(files, list), f"Feature '{feature_name}' files is not a list"

    def test_deps_is_list_if_present(self):
        """'deps' key must be a list if present."""
        for feature_name, feature_def in FEATURES.items():
            if "deps" in feature_def:
                deps = feature_def["deps"]
                assert isinstance(deps, list), f"Feature '{feature_name}' deps is not a list"

    def test_no_duplicate_files_across_features(self):
        """No two non-auth features should reference the same file."""
        file_to_feature = {}

        for feature_name, feature_def in FEATURES.items():
            # Skip auth variants (they're mutually exclusive)
            if feature_name.startswith("auth-"):
                continue

            files = feature_def.get("files", [])
            if not isinstance(files, list):
                continue
            for file_path in files:
                if file_path in file_to_feature:
                    pytest.fail(
                        f"File '{file_path}' referenced by both "
                        f"'{feature_name}' and '{file_to_feature[file_path]}'"
                    )
                file_to_feature[file_path] = feature_name

    def test_auth_variants_can_share_files(self):
        """Auth variants are mutually exclusive, can share file paths."""
        auth_features = {k: v for k, v in FEATURES.items() if k.startswith("auth-")}

        # All auth variants should reference auth directory
        for feature_name, feature_def in auth_features.items():
            if feature_name == "auth-none":
                continue  # none has no files

            files = feature_def.get("files", [])
            if not isinstance(files, list):
                continue
            assert any("auth/" in f for f in files), (
                f"Auth feature '{feature_name}' should reference auth/ files"
            )

    def test_core_marked_as_always(self):
        """Core feature should be marked as always=True."""
        assert "core" in FEATURES
        assert FEATURES["core"].get("always") is True

    def test_template_files_have_j2_extension(self):
        """All template files should end with .j2."""
        for feature_name, feature_def in FEATURES.items():
            files = feature_def.get("files", [])
            if not isinstance(files, list):
                continue
            for file_path in files:
                assert file_path.endswith(".j2"), (
                    f"Template '{file_path}' in feature '{feature_name}' missing .j2 extension"
                )

    def test_conflicts_reference_valid_features(self):
        """Conflict declarations should reference existing features."""
        for feature_name, feature_def in FEATURES.items():
            conflicts = feature_def.get("conflicts", [])
            if not isinstance(conflicts, list):
                continue
            for conflict in conflicts:
                assert conflict in FEATURES, (
                    f"Feature '{feature_name}' conflicts with unknown feature '{conflict}'"
                )

    def test_conflicts_are_symmetric(self):
        """If A conflicts with B, B should conflict with A."""
        for feature_name, feature_def in FEATURES.items():
            conflicts = feature_def.get("conflicts", [])
            if not isinstance(conflicts, list):
                continue
            for conflict in conflicts:
                conflict_def = FEATURES.get(conflict, {})
                conflict_conflicts = conflict_def.get("conflicts", [])
                if not isinstance(conflict_conflicts, list):
                    continue
                assert feature_name in conflict_conflicts, (
                    f"Feature '{feature_name}' conflicts with '{conflict}', "
                    f"but '{conflict}' doesn't conflict with '{feature_name}'"
                )


@pytest.mark.integration
class TestRegistryTemplatesExist:
    """Test that all referenced templates actually exist on disk."""

    def test_all_template_files_exist(self, tmp_path):
        """All templates in registry should exist on disk."""
        from pathlib import Path

        # Get templates directory
        import astra_cli.templates

        templates_dir = Path(astra_cli.templates.__file__).parent / "server"

        if not templates_dir.exists():
            pytest.skip("Templates directory not found")

        missing_templates = []

        for feature_name, feature_def in FEATURES.items():
            files = feature_def.get("files", [])
            if not isinstance(files, list):
                continue
            for template_path in files:
                full_path = templates_dir / template_path
                if not full_path.exists():
                    missing_templates.append((feature_name, template_path))

        if missing_templates:
            msg = "Missing templates:\n" + "\n".join(
                f"  {feat}: {tmpl}" for feat, tmpl in missing_templates
            )
            pytest.fail(msg)
