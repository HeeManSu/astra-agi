"""Unit tests for shared dependency handling."""

from unittest.mock import patch

from astra_cli.engine.features import FEATURES, get_remove_feature_plan
import pytest


@pytest.fixture
def mock_features():
    """Mock registry with shared dependencies."""
    mock_registry = {
        "feat-a": {
            "files": [],
            "deps": ["shared-dep>=1.0.0", "unique-a>=1.0.0"],
        },
        "feat-b": {
            "files": [],
            "deps": ["shared-dep>=1.0.0", "unique-b>=1.0.0"],
        },
        "core": {
            "files": [],
            "deps": ["core-dep>=1.0.0"],
        },
    }
    with patch.dict(FEATURES, mock_registry, clear=True):
        yield


@pytest.mark.unit
class TestSharedDependencies:
    """Test that shared dependencies are preserved correctly."""

    def test_remove_feature_preserves_shared_dep(self, mock_features):
        """Removing feat-a should NOT remove shared-dep if feat-b uses it."""
        config = {
            "features": {
                "core": True,
                "feat-a": True,
                "feat-b": True,
            }
        }

        # Remove feat-a
        plan = get_remove_feature_plan(config, "feat-a")

        # Should remove unique-a
        assert "unique-a>=1.0.0" in plan.deps_to_remove

        # Should NOT remove shared-dep (used by feat-b)
        assert "shared-dep>=1.0.0" not in plan.deps_to_remove
        assert "core-dep>=1.0.0" not in plan.deps_to_remove

    def test_remove_last_feature_removes_shared_dep(self, mock_features):
        """Removing feat-a should remove shared-dep if no other feature uses it."""
        config = {
            "features": {
                "core": True,
                "feat-a": True,
                # feat-b is NOT enabled
            }
        }

        # Remove feat-a
        plan = get_remove_feature_plan(config, "feat-a")

        # Should remove both
        assert "unique-a>=1.0.0" in plan.deps_to_remove
        assert "shared-dep>=1.0.0" in plan.deps_to_remove

    def test_remove_multiple_shared_deps(self, mock_features):
        """Should handle multiple shared dependencies correctly."""
        # Add another shared dep to mock
        extra_mock = {
            "feat-c": {"deps": ["d1", "d2"]},
            "feat-d": {"deps": ["d2", "d3"]},
        }

        with patch.dict(FEATURES, extra_mock):
            config = {
                "features": {
                    "feat-c": True,
                    "feat-d": True,
                }
            }

            # Remove feat-c
            plan = get_remove_feature_plan(config, "feat-c")

            # d1 should go (unique to c)
            assert "d1" in plan.deps_to_remove
            # d2 should stay (shared with d)
            assert "d2" not in plan.deps_to_remove

            # Now verify if d was also removed
            config_d_only = {"features": {"feat-c": True}}
            plan_last = get_remove_feature_plan(config_d_only, "feat-c")
            assert "d1" in plan_last.deps_to_remove
            assert "d2" in plan_last.deps_to_remove
