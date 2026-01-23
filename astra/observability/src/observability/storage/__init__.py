"""Storage module for Astra Observability."""

from .base import StorageBackend
from .sqlite import SQLiteStorage


__all__ = ["SQLiteStorage", "StorageBackend"]
