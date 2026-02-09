# ruff: noqa: TID252
"""Composite storage for multi-domain data."""

from typing import Any

from .base import FileStorage, InMemoryStorage, StorageProvider


class CompositeStorage:
    """Multi-domain storage manager.

    Domains:
    - index: Symbol tables, graphs (CodeIndex data)
    - wiki: Generated wiki pages
    - embeddings: Vector embeddings for semantic search
    - cache: Temporary cached data
    """

    VALID_DOMAINS = {"index", "wiki", "embeddings", "cache"}

    def __init__(
        self,
        domains: dict[str, StorageProvider] | None = None,
        default_storage: StorageProvider | None = None,
    ) -> None:
        """Initialize composite storage.

        Args:
            domains: Optional mapping of domain names to storage providers
            default_storage: Fallback storage for domains not explicitly set
        """
        self._domains: dict[str, StorageProvider] = domains or {}
        self._default = default_storage or InMemoryStorage()

    def get_store(self, domain: str) -> StorageProvider:
        """Get storage provider for a domain.

        Args:
            domain: Domain name (index, wiki, embeddings, cache)

        Returns:
            StorageProvider for the domain
        """
        if domain not in self.VALID_DOMAINS:
            raise ValueError(f"Invalid domain: {domain}. Valid: {self.VALID_DOMAINS}")
        return self._domains.get(domain, self._default)

    def set_store(self, domain: str, storage: StorageProvider) -> None:
        """Set storage provider for a domain."""
        if domain not in self.VALID_DOMAINS:
            raise ValueError(f"Invalid domain: {domain}. Valid: {self.VALID_DOMAINS}")
        self._domains[domain] = storage

    # Convenience methods for common patterns

    async def get_index(self, key: str) -> Any | None:
        """Get from index domain."""
        return await self.get_store("index").get(key)

    async def set_index(self, key: str, value: Any) -> None:
        """Set in index domain."""
        await self.get_store("index").set(key, value)

    async def get_wiki(self, key: str) -> Any | None:
        """Get from wiki domain."""
        return await self.get_store("wiki").get(key)

    async def set_wiki(self, key: str, value: Any) -> None:
        """Set in wiki domain."""
        await self.get_store("wiki").set(key, value)

    async def get_embedding(self, key: str) -> Any | None:
        """Get from embeddings domain."""
        return await self.get_store("embeddings").get(key)

    async def set_embedding(self, key: str, value: Any) -> None:
        """Set in embeddings domain."""
        await self.get_store("embeddings").set(key, value)


def create_file_storage(base_path: str) -> CompositeStorage:
    """Create file-based composite storage.

    Creates separate directories for each domain under base_path.
    """
    import os

    return CompositeStorage(
        domains={
            "index": FileStorage(os.path.join(base_path, "index")),
            "wiki": FileStorage(os.path.join(base_path, "wiki")),
            "embeddings": FileStorage(os.path.join(base_path, "embeddings")),
            "cache": FileStorage(os.path.join(base_path, "cache")),
        }
    )


def create_memory_storage() -> CompositeStorage:
    """Create in-memory composite storage (for testing)."""
    return CompositeStorage(
        domains={
            "index": InMemoryStorage(),
            "wiki": InMemoryStorage(),
            "embeddings": InMemoryStorage(),
            "cache": InMemoryStorage(),
        }
    )
