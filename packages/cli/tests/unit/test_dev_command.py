"""Unit tests for the dev command."""

from pathlib import Path
import sys
from unittest.mock import patch

from astra_cli.commands.dev import run_dev
import pytest
from typer import Exit


@pytest.mark.unit
class TestDevCommand:
    """Test the dev command logic."""

    @pytest.fixture
    def mock_project(self):
        """Mock project discovery and config."""
        with patch("astra_cli.commands.dev.discover_project") as mock_discover:
            with patch("astra_cli.commands.dev.load_project_config") as mock_load:
                project_path = Path("/mock/project")
                mock_discover.return_value = project_path

                # Default config
                mock_load.return_value = {
                    "project": {"name": "test-project"},
                    "runtime": {"entrypoint": "app.main:app"},
                }

                yield mock_discover, mock_load

    @patch("astra_cli.commands.dev.subprocess.run")
    def test_dev_runs_uvicorn_defaults(self, mock_run, mock_project):
        """Should run uvicorn with default settings."""
        run_dev(host="127.0.0.1", port=8000, reload=True)

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]

        assert cmd[0] == sys.executable
        assert cmd[1] == "-m"
        assert cmd[2] == "uvicorn"
        assert cmd[3] == "app.main:app"  # entrypoint
        assert "--host" in cmd
        assert "127.0.0.1" in cmd
        assert "--port" in cmd
        assert "8000" in cmd
        assert "--reload" in cmd

        assert kwargs["cwd"] == Path("/mock/project")
        assert kwargs["check"] is True

    @patch("astra_cli.commands.dev.subprocess.run")
    def test_dev_custom_host_port(self, mock_run, mock_project):
        """Should respect host and port arguments."""
        run_dev(host="0.0.0.0", port=9000, reload=False)

        cmd = mock_run.call_args[0][0]

        assert "0.0.0.0" in cmd
        assert "9000" in cmd
        assert "--reload" not in cmd

    @patch("astra_cli.commands.dev.subprocess.run")
    def test_dev_uses_config_entrypoint(self, mock_run, mock_project):
        """Should use entrypoint from astra.json."""
        _, mock_load = mock_project
        mock_load.return_value = {
            "project": {"name": "custom"},
            "runtime": {"entrypoint": "custom.app:entry"},
        }

        run_dev(host="127.0.0.1", port=8000, reload=True)

        cmd = mock_run.call_args[0][0]
        assert cmd[3] == "custom.app:entry"

    @patch("astra_cli.commands.dev.discover_project", return_value=None)
    def test_dev_no_project_found(self, mock_discover):
        """Should exit if no project found."""
        with pytest.raises(Exit) as exc:
            run_dev()
        assert exc.value.exit_code == 1

    @patch("astra_cli.commands.dev.subprocess.run", side_effect=FileNotFoundError)
    def test_dev_uvicorn_missing(self, mock_run, mock_project):
        """Should handle uvicorn missing error gracefully."""
        with pytest.raises(Exit) as exc:
            run_dev(host="127.0.0.1", port=8000, reload=True)
        assert exc.value.exit_code == 1
