"""Unit tests for Dependency Engine."""

from astra_cli.engine.deps import remove_dependencies, update_dependencies
import pytest


@pytest.mark.unit
class TestDependencyUpdates:
    """Test dependency addition."""

    def test_add_new_dependency(self, tmp_path):
        """Should add new dependency to pyproject.toml."""
        project = tmp_path / "project"
        project.mkdir()

        # Create minimal pyproject.toml
        pyproject = project / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test"
dependencies = []
""")

        update_dependencies(project, ["fastapi>=0.100.0"])

        content = pyproject.read_text()
        assert "fastapi>=0.100.0" in content

    def test_add_duplicate_dependency(self, tmp_path):
        """Should not add duplicate dependency."""
        project = tmp_path / "project"
        project.mkdir()

        pyproject = project / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test"
dependencies = ["fastapi>=0.100.0"]
""")

        update_dependencies(project, ["fastapi>=0.101.0"])

        content = pyproject.read_text()
        # Should not duplicate (may or may not update version)
        count = content.count("fastapi")
        assert count == 1

    def test_add_multiple_dependencies(self, tmp_path):
        """Should add multiple new dependencies."""
        project = tmp_path / "project"
        project.mkdir()

        pyproject = project / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test"
dependencies = []
""")

        update_dependencies(project, ["fastapi>=0.100.0", "pydantic>=2.0.0"])

        content = pyproject.read_text()
        assert "fastapi>=0.100.0" in content
        assert "pydantic>=2.0.0" in content

    def test_missing_pyproject(self, tmp_path):
        """Should return gracefully if pyproject.toml missing."""
        project = tmp_path / "project"
        project.mkdir()

        # Should not raise
        update_dependencies(project, ["fastapi>=0.100.0"])


@pytest.mark.unit
class TestDependencyRemoval:
    """Test dependency removal."""

    def test_remove_existing_dependency(self, tmp_path):
        """Should remove dependency from pyproject.toml."""
        project = tmp_path / "project"
        project.mkdir()

        pyproject = project / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test"
dependencies = ["fastapi>=0.100.0", "pydantic>=2.0.0"]
""")

        remove_dependencies(project, ["fastapi>=0.100.0"])

        content = pyproject.read_text()
        assert "fastapi" not in content
        assert "pydantic>=2.0.0" in content

    def test_remove_nonexistent_dependency(self, tmp_path):
        """Should handle removing dependency that doesn't exist."""
        project = tmp_path / "project"
        project.mkdir()

        pyproject = project / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test"
dependencies = ["pydantic>=2.0.0"]
""")

        # Should not raise
        remove_dependencies(project, ["fastapi>=0.100.0"])

        content = pyproject.read_text()
        assert "pydantic>=2.0.0" in content

    def test_remove_from_empty_deps(self, tmp_path):
        """Should handle removing when no dependencies."""
        project = tmp_path / "project"
        project.mkdir()

        pyproject = project / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test"
dependencies = []
""")

        # Should not raise
        remove_dependencies(project, ["fastapi>=0.100.0"])
