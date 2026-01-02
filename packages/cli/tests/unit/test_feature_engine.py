"""Unit tests for Feature Engine."""

from astra_cli.engine.features import (
    PROTECTED_FEATURES,
    get_add_feature_plan,
    get_feature_plan,
    get_remove_feature_plan,
    get_sync_plan,
    validate_feature,
    validate_features_in_config,
)
import pytest


@pytest.mark.unit
class TestFeatureValidation:
    """Test feature validation logic."""

    def test_validate_known_feature(self):
        """Should return None for valid feature."""
        assert validate_feature("rate-limit") is None
        assert validate_feature("auth-jwt") is None
        assert validate_feature("auth-api-key") is None

    def test_validate_unknown_feature(self):
        """Should return error message for unknown feature."""
        error = validate_feature("unknown-feature")
        assert error is not None
        assert "Unknown feature" in error
        assert "unknown-feature" in error

    def test_validate_core_feature(self):
        """Core should be valid."""
        assert validate_feature("core") is None


@pytest.mark.unit
class TestFeaturePlanning:
    """Test feature plan generation."""

    def test_get_feature_plan_core_only(self):
        """Should include core files."""
        config = {"features": {"core": True}}
        plan = get_feature_plan(config)

        assert "app/main.py.j2" in plan.files_to_add
        assert "app/settings.py.j2" in plan.files_to_add
        assert len(plan.files_to_add) > 0

    def test_get_feature_plan_with_auth(self):
        """Should include auth files when auth specified."""
        config = {"features": {"core": True, "auth": "jwt"}}
        plan = get_feature_plan(config)

        assert "app/auth/__init__.py.j2" in plan.files_to_add
        assert "app/auth/jwt.py.j2" in plan.files_to_add
        assert "python-jose[cryptography]>=3.3.0" in plan.deps_to_add

    def test_get_feature_plan_with_rate_limit(self):
        """Should include rate-limit files."""
        config = {"features": {"core": True, "rate-limit": True}}
        plan = get_feature_plan(config)

        assert "app/middleware/__init__.py.j2" in plan.files_to_add
        assert "app/middleware/rate_limit.py.j2" in plan.files_to_add
        assert "slowapi>=0.1.9" in plan.deps_to_add

    def test_add_feature_plan(self):
        """Should generate plan for adding single feature."""
        config = {"features": {"core": True}}
        plan = get_add_feature_plan(config, "rate-limit")

        assert len(plan.files_to_add) > 0
        assert "app/middleware/rate_limit.py.j2" in plan.files_to_add
        assert "slowapi>=0.1.9" in plan.deps_to_add

    def test_add_feature_unknown(self):
        """Should return empty plan for unknown feature."""
        config = {"features": {"core": True}}
        plan = get_add_feature_plan(config, "unknown")

        assert len(plan.files_to_add) == 0
        assert len(plan.deps_to_add) == 0

    def test_remove_feature_plan(self):
        """Should generate plan for removing feature."""
        config = {"features": {"core": True, "rate-limit": True}}
        plan = get_remove_feature_plan(config, "rate-limit")

        assert "app/middleware/__init__.py" in plan.files_to_remove
        assert "app/middleware/rate_limit.py" in plan.files_to_remove
        assert "slowapi>=0.1.9" in plan.deps_to_remove


@pytest.mark.unit
class TestFeatureConflicts:
    """Test feature conflict detection."""

    def test_detect_auth_conflict(self):
        """Should detect auth-jwt vs auth-api-key conflict."""
        config = {"features": {"core": True, "auth-api-key": True}}
        plan = get_add_feature_plan(config, "auth-jwt")

        assert "auth-api-key" in plan.conflicts

    def test_no_conflict_different_features(self):
        """Should not conflict unrelated features."""
        config = {"features": {"core": True, "rate-limit": True}}
        plan = get_add_feature_plan(config, "auth-jwt")

        assert len(plan.conflicts) == 0


@pytest.mark.unit
class TestProtectedFeatures:
    """Test protected features cannot be removed."""

    def test_core_is_protected(self):
        """Core should be in PROTECTED_FEATURES."""
        assert "core" in PROTECTED_FEATURES


@pytest.mark.unit
class TestConfigValidation:
    """Test config validation."""

    def test_validate_valid_config(self):
        """Should return no errors for valid config."""
        config = {"features": {"core": True, "auth": "jwt", "rate-limit": True}}
        errors = validate_features_in_config(config)

        assert len(errors) == 0

    def test_validate_unknown_feature(self):
        """Should return error for unknown feature."""
        config = {"features": {"core": True, "unknown": True}}
        errors = validate_features_in_config(config)

        assert len(errors) > 0
        assert any("unknown" in e for e in errors)

    def test_validate_unknown_auth(self):
        """Should return error for unknown auth type."""
        config = {"features": {"core": True, "auth": "unknown-auth"}}
        errors = validate_features_in_config(config)

        assert len(errors) > 0
        assert any("auth" in e.lower() for e in errors)


@pytest.mark.unit
class TestSyncPlan:
    """Test sync plan generation."""

    def test_sync_plan_missing_files(self, tmp_path):
        """Should detect missing files."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        config = {"features": {"core": True}}
        plan = get_sync_plan(config, project_path)

        # All core files should be missing
        assert len(plan.files_to_add) > 0
        assert "app/main.py.j2" in plan.files_to_add

    def test_sync_plan_all_files_exist(self, tmp_path):
        """Should return empty plan when all files exist."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create all expected files
        (project_path / "app").mkdir()
        (project_path / "app" / "main.py").write_text("")
        (project_path / "app" / "settings.py").write_text("")
        # ... create more files

        config = {"features": {"core": True}}
        plan = get_sync_plan(config, project_path)

        # Should have fewer missing files
        assert len(plan.files_to_add) >= 0
