"""End-to-end tests for astra sync command."""

import json

import pytest


@pytest.mark.e2e
class TestSyncCommand:
    """Test astra sync command."""

    def test_sync_no_changes_needed(self, temp_project, cli_runner):
        """Should report project in sync when no changes needed."""
        # Use init to create a fully synced project state
        cli_runner.invoke(
            ["init", "server", "sync-test", "--auth", "none", "-y"],
            cwd=str(temp_project.parent),
        )
        # Update temp_project to point to the new init-ed project
        project_path = temp_project.parent / "sync-test"

        result = cli_runner.invoke(
            ["sync"],
            cwd=str(project_path),
        )

        assert result.exit_code == 0
        assert "in sync" in result.stdout.lower() or "No changes" in result.stdout

    def test_sync_regenerates_missing_files(self, temp_project, cli_runner):
        """Should regenerate missing files."""
        # Delete a file that should exist
        if (temp_project / "app" / "main.py").exists():
            (temp_project / "app" / "main.py").unlink()

        result = cli_runner.invoke(
            ["sync"],
            cwd=str(temp_project),
        )

        # Should recreate the file
        # Note: In real scenario, all missing core files would be recreated
        assert "Synced" in result.stdout or "Added" in result.stdout

    def test_sync_dry_run(self, temp_project, cli_runner):
        """Should preview sync without making changes."""
        result = cli_runner.invoke(
            ["sync", "--dry-run"],
            cwd=str(temp_project),
        )

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.stdout or "Would" in result.stdout

    def test_sync_invalid_config(self, tmp_path, cli_runner):
        """Should error on invalid config."""
        project = tmp_path / "bad-project"
        project.mkdir()

        # Write config with unknown feature
        config = {
            "schema_version": "1.0",
            "project": {"name": "bad", "type": "server"},
            "features": {"core": True, "unknown-feature": True},
        }
        (project / "astra.json").write_text(json.dumps(config))

        result = cli_runner.invoke(
            ["sync"],
            cwd=str(project),
        )

        assert result.exit_code != 0
        assert "validation" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_sync_outside_project(self, tmp_path, cli_runner):
        """Should error when run outside project."""
        result = cli_runner.invoke(
            ["sync"],
            cwd=str(tmp_path),
        )

        assert result.exit_code != 0
        assert "No Astra project found" in result.stdout

    def test_sync_preserves_manual_edits(self, temp_project, cli_runner):
        """Should not overwrite user's manual edits."""
        # Create file with custom content
        (temp_project / "app").mkdir(exist_ok=True)
        custom_file = temp_project / "app" / "main.py"
        custom_content = "# My custom edits\nprint('hello')"
        custom_file.write_text(custom_content)

        result = cli_runner.invoke(
            ["sync"],
            cwd=str(temp_project),
        )

        # Should complete successfully
        assert result.exit_code == 0
        # File should still have custom content
        assert custom_file.read_text() == custom_content
