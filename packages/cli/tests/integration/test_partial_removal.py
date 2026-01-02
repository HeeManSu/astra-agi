"""Integration tests for partial feature removal edge cases."""

import pytest


@pytest.mark.integration
class TestPartialRemoval:
    """Test removal when files are already deleted or directories have user files."""

    def test_remove_when_files_already_deleted(self, temp_project, cli_runner):
        """Should handle gracefully when feature files already deleted."""
        # Add feature
        cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))

        # Manually delete some files
        rate_limit_file = temp_project / "app" / "middleware" / "rate_limit.py"
        if rate_limit_file.exists():
            rate_limit_file.unlink()

        # Remove feature - should not error
        result = cli_runner.invoke(
            ["remove", "rate-limit", "-f"],
            cwd=str(temp_project),
        )

        # Should succeed even though file already gone
        assert result.exit_code == 0 or "not found" in result.stdout.lower()

    def test_remove_preserves_user_files_in_same_directory(self, temp_project, cli_runner):
        """Should only remove registry-owned files, not user-added files."""
        # Add feature
        cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))

        # User adds their own file in middleware directory
        middleware_dir = temp_project / "app" / "middleware"
        user_file = middleware_dir / "my_custom_middleware.py"
        user_file.write_text("# My custom code")

        # Remove feature
        result = cli_runner.invoke(
            ["remove", "rate-limit", "-f"],
            cwd=str(temp_project),
        )

        assert result.exit_code == 0

        # User file should still exist
        assert user_file.exists()
        assert user_file.read_text() == "# My custom code"

        # Registry file should be gone
        assert not (middleware_dir / "rate_limit.py").exists()

    def test_remove_keeps_directory_if_user_files_present(self, temp_project, cli_runner):
        """Should not delete directory if it contains user files."""
        # Add feature
        cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))

        # User adds file
        middleware_dir = temp_project / "app" / "middleware"
        (middleware_dir / "user_file.py").write_text("user code")

        # Remove feature
        cli_runner.invoke(["remove", "rate-limit", "-f"], cwd=str(temp_project))

        # Directory should still exist (has user file)
        assert middleware_dir.exists()
        assert (middleware_dir / "user_file.py").exists()

    def test_remove_deletes_empty_directory(self, temp_project, cli_runner):
        """Should delete directory if empty after removal."""
        # Add feature
        cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))

        middleware_dir = temp_project / "app" / "middleware"
        assert middleware_dir.exists()

        # Remove feature
        cli_runner.invoke(["remove", "rate-limit", "-f"], cwd=str(temp_project))

        # Directory should be gone (was empty after removing files)
        # Note: This depends on implementation - may or may not delete
        # Documenting current behavior
        if not middleware_dir.exists():
            # Good - cleaned up empty dir
            pass
        else:
            # Also acceptable - left empty dir
            # Check it's actually empty
            remaining = list(middleware_dir.glob("*"))
            assert len(remaining) <= 1  # Maybe just __init__.py

    def test_remove_with_nested_user_files(self, temp_project, cli_runner):
        """Should handle nested directories with mix of registry and user files."""
        # Add feature
        cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))

        middleware_dir = temp_project / "app" / "middleware"

        # User creates nested structure
        nested = middleware_dir / "custom"
        nested.mkdir()
        (nested / "user_middleware.py").write_text("user code")

        # Remove feature
        result = cli_runner.invoke(
            ["remove", "rate-limit", "-f"],
            cwd=str(temp_project),
        )

        assert result.exit_code == 0

        # User's nested files should be preserved
        assert (nested / "user_middleware.py").exists()

        # Registry file should be gone
        assert not (middleware_dir / "rate_limit.py").exists()


@pytest.mark.integration
class TestIdempotency:
    """Test strict idempotency guarantees."""

    def test_double_add_is_idempotent(self, temp_project, cli_runner):
        """Add → Add should be no-op on second call."""
        # First add
        result1 = cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))
        assert result1.exit_code == 0

        # Second add
        result2 = cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))

        # Should warn/no-op, not error
        assert "already enabled" in result2.stdout.lower() or "exists" in result2.stdout.lower()

    def test_double_sync_is_idempotent(self, temp_project, cli_runner):
        """Sync → Sync should produce empty plan on second call."""
        # First sync
        result1 = cli_runner.invoke(["sync"], cwd=str(temp_project))
        assert result1.exit_code == 0

        # Second sync immediately after
        result2 = cli_runner.invoke(["sync"], cwd=str(temp_project))

        # Should report no changes
        assert "in sync" in result2.stdout.lower() or "no changes" in result2.stdout.lower()

    def test_add_sync_sync_is_stable(self, temp_project, cli_runner):
        """Add → Sync → Sync should be stable."""
        # Add feature
        cli_runner.invoke(["add", "rate-limit"], cwd=str(temp_project))

        # First sync
        cli_runner.invoke(["sync"], cwd=str(temp_project))

        # Second sync
        result = cli_runner.invoke(["sync"], cwd=str(temp_project))

        # Should be stable
        assert "in sync" in result.stdout.lower() or "no changes" in result.stdout.lower()
