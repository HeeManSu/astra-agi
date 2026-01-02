"""End-to-end tests for astra add/remove commands."""

import json

import pytest


@pytest.mark.e2e
class TestAddCommand:
    """Test astra add command."""

    def test_add_rate_limit(self, temp_project, cli_runner):
        """Should add rate-limit feature."""
        result = cli_runner.invoke(
            ["add", "rate-limit"],
            cwd=str(temp_project),
        )

        assert result.exit_code == 0
        assert "✅ Added rate-limit" in result.stdout

        # Verify files created
        assert (temp_project / "app" / "middleware" / "rate_limit.py").exists()

        # Verify config updated
        config = json.loads((temp_project / "astra.json").read_text())
        assert config["features"]["rate-limit"] is True

    def test_add_unknown_feature(self, temp_project, cli_runner):
        """Should error on unknown feature."""
        result = cli_runner.invoke(
            ["add", "unknown-feature"],
            cwd=str(temp_project),
        )

        assert result.exit_code != 0
        assert "Error" in result.stdout

    def test_add_already_enabled(self, temp_project, cli_runner):
        """Should warn if feature already enabled."""
        # Add once
        cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))

        # Add again
        result = cli_runner.invoke(
            ["add", "rate-limit"],
            cwd=str(temp_project),
        )

        assert "already enabled" in result.stdout.lower()

    def test_add_dry_run(self, temp_project, cli_runner):
        """Should preview without making changes."""
        result = cli_runner.invoke(
            ["add", "rate-limit", "--dry-run"],
            cwd=str(temp_project),
        )

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.stdout
        assert not (temp_project / "app" / "middleware").exists()

    def test_add_outside_project(self, tmp_path, cli_runner):
        """Should error when run outside project."""
        result = cli_runner.invoke(
            ["add", "rate-limit"],
            cwd=str(tmp_path),
        )

        assert result.exit_code != 0
        assert "No Astra project found" in result.stdout


@pytest.mark.e2e
class TestRemoveCommand:
    """Test astra remove command."""

    def test_remove_feature(self, temp_project, cli_runner):
        """Should remove feature and files."""
        # First add
        cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))

        # Then remove
        result = cli_runner.invoke(
            ["remove", "rate-limit", "-f"],
            cwd=str(temp_project),
        )

        assert result.exit_code == 0
        assert "✅ Removed rate-limit" in result.stdout

        # Verify files removed
        assert not (temp_project / "app" / "middleware" / "rate_limit.py").exists()

        # Verify config updated
        config = json.loads((temp_project / "astra.json").read_text())
        assert "rate-limit" not in config["features"]

    def test_remove_nonexistent_feature(self, temp_project, cli_runner):
        """Should warn if feature not enabled."""
        result = cli_runner.invoke(
            ["remove", "rate-limit", "-f"],
            cwd=str(temp_project),
        )

        assert "not enabled" in result.stdout.lower()

    def test_remove_protected_core(self, temp_project, cli_runner):
        """Should error when removing core."""
        result = cli_runner.invoke(
            ["remove", "core", "-f"],
            cwd=str(temp_project),
        )

        assert result.exit_code != 0
        assert "protected" in result.stdout.lower()

    def test_remove_dry_run(self, temp_project, cli_runner):
        """Should preview without removing."""
        cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))

        result = cli_runner.invoke(
            ["remove", "rate-limit", "--dry-run"],
            cwd=str(temp_project),
        )

        assert "[DRY RUN]" in result.stdout
        # Files should still exist
        assert (temp_project / "app" / "middleware" / "rate_limit.py").exists()


@pytest.mark.e2e
class TestFeatureWorkflow:
    """Test complete add/remove workflows."""

    def test_add_remove_cycle(self, temp_project, cli_runner):
        """Should handle add → remove → add cycle."""
        # Add
        result1 = cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))
        assert result1.exit_code == 0

        # Remove
        result2 = cli_runner.invoke(["remove", "rate-limit", "-f"], cwd=str(temp_project))
        assert result2.exit_code == 0

        # Add again
        result3 = cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))
        assert result3.exit_code == 0

        # Should work
        config = json.loads((temp_project / "astra.json").read_text())
        assert config["features"]["rate-limit"] is True
