"""Base contents database interface."""

from abc import ABC, abstractmethod
from typing import Any

from framework.KnowledgeBase.models import Content


class ContentsDB(ABC):
    """Base class for contents databases."""

    @abstractmethod
    async def create_content(self, content: Content) -> str:
        """
        Create a content record.

        Args:
            content: Content object

        Returns:
            Content ID
        """

    @abstractmethod
    async def get_content(self, content_id: str) -> Content | None:
        """
        Get content by ID.

        Args:
            content_id: Content ID

        Returns:
            Content object or None if not found
        """

    @abstractmethod
    async def update_content(self, content: Content) -> None:
        """
        Update content record.

        Args:
            content: Content object with updated fields
        """

    @abstractmethod
    async def delete_content(self, content_id: str) -> None:
        """
        Delete content record.

        Args:
            content_id: Content ID to delete
        """

    @abstractmethod
    async def list_contents(self, filters: dict[str, Any] | None = None) -> list[Content]:
        """
        List all content with optional filters.

        Args:
            filters: Optional filters

        Returns:
            List of Content objects
        """
