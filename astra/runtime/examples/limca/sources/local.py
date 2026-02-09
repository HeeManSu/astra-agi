"""Local source loader for Limca."""

from pathlib import Path
from typing import ClassVar


class LocalSource:
    """Load files from a local directory."""

    DEFAULT_EXTENSIONS: ClassVar[list[str]] = [".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs"]
    DEFAULT_EXCLUDES: ClassVar[list[str]] = [
        "node_modules",
        "venv",
        ".venv",
        "__pycache__",
        ".git",
        "dist",
        "build",
        ".next",
        "vendor",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        "site-packages",
    ]
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

    def __init__(
        self,
        path: str,
        extensions: list[str] | None = None,
        excludes: list[str] | None = None,
    ):
        """Initialize local source.

        Args:
            path: Root path to load files from
            extensions: File extensions to include (default: common code files)
            excludes: Directory names to exclude
        """
        self.root = Path(path).resolve()
        self.extensions = extensions or self.DEFAULT_EXTENSIONS
        self.excludes = set(excludes or self.DEFAULT_EXCLUDES)

        if not self.root.exists():
            raise FileNotFoundError(f"Path not found: {self.root}")
        if not self.root.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.root}")

    def get_files(self) -> list[Path]:
        """Get all matching files.

        Returns:
            List of file paths relative to root
        """
        files = [
            path
            for ext in self.extensions
            for path in self.root.rglob(f"*{ext}")
            if self._should_include(path)
        ]
        return sorted(files)

    def _should_include(self, path: Path) -> bool:
        """Check if file should be included."""
        # Check exclusions
        for part in path.parts:
            if part in self.excludes:
                return False

        # Check file size
        try:
            if path.stat().st_size > self.MAX_FILE_SIZE:
                return False
        except OSError:
            return False

        return True

    def read_file(self, path: Path) -> str:
        """Read file content.

        Args:
            path: Absolute path or relative to root

        Returns:
            File content as string
        """
        if not path.is_absolute():
            path = self.root / path

        return path.read_text(encoding="utf-8", errors="replace")

    def get_relative_path(self, path: Path) -> str:
        """Get path relative to root as string."""
        if path.is_absolute():
            return str(path.relative_to(self.root))
        return str(path)
