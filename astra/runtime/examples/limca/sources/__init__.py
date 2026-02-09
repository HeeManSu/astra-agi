"""Source loaders for Limca."""

from .github import GitHubSource
from .local import LocalSource


__all__ = ["GitHubSource", "LocalSource"]
