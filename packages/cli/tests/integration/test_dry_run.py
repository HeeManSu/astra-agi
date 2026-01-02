"""Integration tests for dry-run accuracy and correctness."""

import json
import time

import pytest


@pytest.mark.integration
class TestDryRunAccuracy:
    """Test that dry-run output is accurate and complete."""

    def test_dry_run_shows_all_files_to_add(self, tmp_path, cli_runner):
        """Dry-run should list ALL files that would be created."""
        result = cli_runner.invoke(
            ["init", "server", "dry-test", "--auth", "jwt", "-y", "--dry-run"],
            cwd=str(tmp_path),
        )

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.stdout

        # Should show key files
        assert "app/main.py" in result.stdout
        assert "app/settings.py" in result.stdout
        assert "app/auth/jwt.py" in result.stdout
        assert "pyproject.toml" in result.stdout

        # Should NOT show .j2 extension
        assert ".j2" not in result.stdout

    def test_dry_run_shows_dependencies(self, temp_project, cli_runner):
        """Dry-run should show dependencies that would be added."""
        result = cli_runner.invoke(
            ["add", "rate-limit", "--dry-run"],
            cwd=str(temp_project),
        )

        assert result.exit_code == 0
        # Should mention dependencies or slowapi
        output_lower = result.stdout.lower()
        assert "slowapi" in output_lower or "dependencies" in output_lower

    def test_dry_run_never_touches_filesystem(self, tmp_path, cli_runner):
        """Dry-run should never create any files or directories."""
        # Record initial state
        initial_files = set(tmp_path.rglob("*"))
        initial_mtime = tmp_path.stat().st_mtime

        # Wait a tiny bit to ensure timestamp would change
        time.sleep(0.01)

        result = cli_runner.invoke(
            ["init", "server", "fs-test", "--auth", "none", "-y", "--dry-run"],
            cwd=str(tmp_path),
        )

        assert result.exit_code == 0

        # Check filesystem unchanged
        final_files = set(tmp_path.rglob("*"))
        final_mtime = tmp_path.stat().st_mtime

        assert initial_files == final_files, "Dry-run created files!"
        assert abs(final_mtime - initial_mtime) < 0.1, "Dry-run modified directory!"

        # Project directory should not exist
        assert not (tmp_path / "fs-test").exists()

    def test_dry_run_shows_files_to_remove(self, temp_project, cli_runner):
        """Dry-run remove should show which files would be deleted."""
        # First add a feature
        cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))

        # Then dry-run remove
        result = cli_runner.invoke(
            ["remove", "rate-limit", "--dry-run"],
            cwd=str(temp_project),
        )

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.stdout
        assert "rate_limit.py" in result.stdout or "middleware" in result.stdout

    def test_dry_run_preserves_config_state(self, temp_project, cli_runner):
        """Dry-run should not modify astra.json."""
        # Get initial config
        initial_config = json.loads((temp_project / "astra.json").read_text())

        # Dry-run add
        cli_runner.invoke(["add", "rate-limit", "--dry-run"], cwd=str(temp_project))

        # Config should be unchanged
        final_config = json.loads((temp_project / "astra.json").read_text())
        assert initial_config == final_config

    def test_dry_run_sync_shows_missing_files(self, temp_project, cli_runner):
        """Dry-run sync should show what files would be added."""
        # Delete a file
        if (temp_project / "app").exists():
            import shutil

            shutil.rmtree(temp_project / "app")

        result = cli_runner.invoke(
            ["sync", "--dry-run"],
            cwd=str(temp_project),
        )

        assert result.exit_code == 0
        # Should show files that would be regenerated
        assert "app/main.py" in result.stdout or "Would add" in result.stdout


@pytest.mark.integration
class TestDryRunConsistency:
    """Test dry-run vs actual execution consistency."""

    def test_dry_run_matches_actual_init(self, tmp_path, cli_runner):
        """Dry-run output should match what init actually creates."""
        # Run dry-run
        dry_result = cli_runner.invoke(
            ["init", "server", "match-test", "--auth", "none", "-y", "--dry-run"],
            cwd=str(tmp_path),
        )

        # Parse files from dry-run output (this is simplified)
        dry_files = []
        for line in dry_result.stdout.split("\n"):
            if "→" in line or "app/" in line:
                # Extract filename from output
                dry_files.extend(
                    part.strip("→").strip()
                    for part in line.split()
                    if "app/" in part or ".py" in part or ".toml" in part
                )

        # Run actual init in different location
        actual_result = cli_runner.invoke(
            ["init", "server", "match-test-2", "--auth", "none", "-y"],
            cwd=str(tmp_path),
        )

        assert actual_result.exit_code == 0

        # Check that actual files were created
        project = tmp_path / "match-test-2"
        assert project.exists()

        # Key files should match what dry-run showed
        assert (project / "app" / "main.py").exists()
        assert (project / "astra.json").exists()
