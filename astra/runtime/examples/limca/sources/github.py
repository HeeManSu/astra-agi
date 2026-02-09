"""GitHub source loader."""

from pathlib import Path
import shutil
import tempfile

import git


class GitHubSource:
    """Clones a GitHub repository."""

    def __init__(self, url: str, branch: str = "main"):
        """Initialize GitHub source.

        Args:
            url: Repository URL (e.g., https://github.com/user/repo)
            branch: Branch to clone (default: main)
        """
        self.url = url
        self.branch = branch
        self.temp_dir: Path | None = None
        self.repo_dir: Path | None = None

    def clone(self) -> str:
        """Clone repository to temporary directory.

        Returns:
            Path to cloned repository
        """
        self.temp_dir = Path(tempfile.mkdtemp(prefix="limca_repo_"))
        self.repo_dir = self.temp_dir / "repo"

        print(f"Cloning {self.url} ({self.branch}) to {self.repo_dir}...")

        git.Repo.clone_from(
            self.url,
            self.repo_dir,
            branch=self.branch,
            depth=1,  # Shallow clone for speed
        )

        return str(self.repo_dir)

    def cleanup(self) -> None:
        """Remove temporary directory."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
            self.repo_dir = None
