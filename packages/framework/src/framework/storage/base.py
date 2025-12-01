from abc import abstractmethod
from typing import Any


class StorageBackend:
    """
    Abstract base class for storage backends.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage backend."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection to the storage backend."""

    @abstractmethod
    async def execute(self, query: Any, params: dict[str, Any] | None = None) -> None:
        """Execute a write operation."""

    @abstractmethod
    async def fetch_all(
        self, query: Any, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all rows."""

    @abstractmethod
    async def fetch_one(
        self, query: Any, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Fetch a single row."""

    @abstractmethod
    async def create_tables(self) -> None:
        """Create the necessary tables if they don't exist."""
