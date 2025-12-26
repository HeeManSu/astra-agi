"""Base content store interface."""

from abc import ABC, abstractmethod
from typing import Any

from framework.KnowledgeBase.vectordb.models import Content


class ContentStore(ABC):
    """Base class for content storage.

    Stores metadata about ingested content (not the vectors themselves).
    This is separate from the vector database.
    """

    @abstractmethod
    async def create(self, content: Content) -> str:
        """
        Create a content record.

        Args:
            content: Content object

        Returns:
            Content ID
        """

    @abstractmethod
    async def get(self, content_id: str) -> Content | None:
        """
        Get content by ID.

        Args:
            content_id: Content ID

        Returns:
            Content object or None if not found
        """

    @abstractmethod
    async def update(self, content: Content) -> None:
        """
        Update content record.

        Args:
            content: Content object with updated fields
        """

    @abstractmethod
    async def delete(self, content_id: str) -> None:
        """
        Delete content record.

        Args:
            content_id: Content ID to delete
        """

    @abstractmethod
    async def list(self, filters: dict[str, Any] | None = None) -> list[Content]:
        """
        List all content with optional filters.

        Args:
            filters: Optional filters

        Returns:
            List of Content objects
        """
