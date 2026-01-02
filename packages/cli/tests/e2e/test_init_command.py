"""End-to-end tests for astra init command."""

import json

import pytest


@pytest.mark.e2e
class TestInitCommand:
    """Test astra init server command."""

    def test_init_creates_project(self, tmp_path, cli_runner):
        """Should create complete project structure."""
        result = cli_runner.invoke(
            ["init", "server", "my-project", "--auth", "none", "-y"],
            cwd=str(tmp_path),
        )

        assert result.exit_code == 0
        assert "✅ Created my-project" in result.stdout

        project_path = tmp_path / "my-project"
        assert project_path.exists()
        assert (project_path / "astra.json").exists()
        assert (project_path / "app" / "main.py").exists()

    def test_init_with_jwt_auth(self, tmp_path, cli_runner):
        """Should create project with JWT auth."""
        result = cli_runner.invoke(
            ["init", "server", "auth-project", "--auth", "jwt", "-y"],
            cwd=str(tmp_path),
        )

        assert result.exit_code == 0

        project_path = tmp_path / "auth-project"
        config = json.loads((project_path / "astra.json").read_text())

        assert config["features"]["auth"] == "jwt"
        assert (project_path / "app" / "auth" / "jwt.py").exists()

    def test_init_with_api_key_auth(self, tmp_path, cli_runner):
        """Should create project with API key auth."""
        result = cli_runner.invoke(
            ["init", "server", "api-project", "--auth", "api-key", "-y"],
            cwd=str(tmp_path),
        )

        assert result.exit_code == 0

        project_path = tmp_path / "api-project"
        assert (project_path / "app" / "auth" / "api_key.py").exists()

    def test_init_dry_run(self, tmp_path, cli_runner):
        """Should preview without creating files."""
        result = cli_runner.invoke(
            ["init", "server", "dry-project", "--auth", "none", "-y", "--dry-run"],
            cwd=str(tmp_path),
        )

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.stdout
        assert not (tmp_path / "dry-project").exists()

    def test_init_existing_directory_fails(self, tmp_path, cli_runner):
        """Should fail if directory already exists."""
        existing = tmp_path / "existing"
        existing.mkdir()

        result = cli_runner.invoke(
            ["init", "server", "existing", "--auth", "none", "-y"],
            cwd=str(tmp_path),
        )

        assert result.exit_code != 0
        assert "already exists" in result.stdout.lower()

    def test_init_saves_correct_config(self, tmp_path, cli_runner):
        """Should save valid astra.json."""
        result = cli_runner.invoke(
            ["init", "server", "config-test", "--auth", "jwt", "-y"],
            cwd=str(tmp_path),
        )

        assert result.exit_code == 0

        config_path = tmp_path / "config-test" / "astra.json"
        config = json.loads(config_path.read_text())

        assert config["schema_version"] == "1.0"
        assert config["project"]["name"] == "config-test"
        assert config["project"]["type"] == "server"
        assert config["features"]["core"] is True
        assert config["features"]["auth"] == "jwt"
        assert config["runtime"]["entrypoint"] == "app.main:app"
