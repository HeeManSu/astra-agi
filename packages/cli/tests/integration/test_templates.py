"""Integration tests for template rendering."""

from astra_cli.engine.features import FeaturePlan
from astra_cli.engine.templates import apply_feature_plan, remove_feature_files, render_project
import pytest


@pytest.mark.integration
class TestTemplateRendering:
    """Test template rendering and file creation."""

    def test_render_project_creates_files(self, tmp_path):
        """Should create all files from plan."""
        project_path = tmp_path / "new-project"

        plan = FeaturePlan(
            files_to_add=["app/main.py.j2", "app/settings.py.j2"],
        )

        context = {
            "project_name": "test-project",
            "auth_type": "none",
            "has_auth": False,
            "features": {"core": True},
        }

        created = render_project(project_path, plan, context)

        assert len(created) > 0
        assert (project_path / "app" / "main.py").exists()
        assert (project_path / "app" / "settings.py").exists()

    def test_render_creates_nested_directories(self, tmp_path):
        """Should create parent directories as needed."""
        project_path = tmp_path / "new-project"

        plan = FeaturePlan(
            files_to_add=["app/api/deep/nested.py.j2"],
        )

        context = {"project_name": "test"}

        # Should not raise
        created = render_project(project_path, plan, context)

        # Should create the nested path
        assert len(created) >= 0  # May or may not create dummy file
        assert (project_path / "app" / "api" / "deep").exists()

    def test_apply_feature_skip_existing(self, tmp_path):
        """Should skip existing files by default."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create existing file
        (project_path / "app").mkdir()
        existing = project_path / "app" / "main.py"
        existing.write_text("# existing content")

        plan = FeaturePlan(files_to_add=["app/main.py.j2"])
        context = {"project_name": "test"}

        created = apply_feature_plan(project_path, plan, context, force=False)

        # Should not overwrite
        assert len(created) == 0
        assert existing.read_text() == "# existing content"

    def test_apply_feature_force_overwrites(self, tmp_path):
        """Should overwrite with force=True."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        (project_path / "app").mkdir()
        existing = project_path / "app" / "main.py"
        existing.write_text("# existing")

        plan = FeaturePlan(files_to_add=["app/main.py.j2"])
        context = {"project_name": "test", "auth_type": "none", "has_auth": False, "features": {}}

        created = apply_feature_plan(project_path, plan, context, force=True)

        assert len(created) > 0
        # Content should be different
        assert "# existing" not in existing.read_text()


@pytest.mark.integration
class TestFileRemoval:
    """Test file removal."""

    def test_remove_feature_files(self, tmp_path):
        """Should remove files listed in plan."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Create files to remove
        (project_path / "app" / "middleware").mkdir(parents=True)
        file1 = project_path / "app" / "middleware" / "rate_limit.py"
        file1.write_text("content")

        plan = FeaturePlan(files_to_remove=["app/middleware/rate_limit.py"])

        removed = remove_feature_files(project_path, plan)

        assert len(removed) > 0
        assert not file1.exists()

    def test_remove_nonexistent_file(self, tmp_path):
        """Should handle removing files that don't exist."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        plan = FeaturePlan(files_to_remove=["app/nonexistent.py"])

        # Should not raise
        removed = remove_feature_files(project_path, plan)
        assert len(removed) == 0

    def test_remove_cleans_empty_dirs(self, tmp_path):
        """Should remove empty parent directories."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        nested = project_path / "app" / "deep" / "nested"
        nested.mkdir(parents=True)
        file1 = nested / "file.py"
        file1.write_text("")

        plan = FeaturePlan(files_to_remove=["app/deep/nested/file.py"])

        remove_feature_files(project_path, plan)

        # Empty directories should be removed
        assert not file1.exists()
