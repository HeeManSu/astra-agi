"""In-memory contents database implementation."""

from typing import Any

from framework.KnowledgeBase.contents_db.base import ContentsDB
from framework.KnowledgeBase.models import Content


class InMemoryContentsDB(ContentsDB):
    """In-memory implementation of ContentsDB for testing and simple use cases."""

    def __init__(self):
        """Initialize in-memory database."""
        self._contents: dict[str, Content] = {}

    async def create_content(self, content: Content) -> str:
        """
        Create a content record.

        Args:
            content: Content object

        Returns:
            Content ID
        """
        self._contents[content.id] = content
        return content.id

    async def get_content(self, content_id: str) -> Content | None:
        """
        Get content by ID.

        Args:
            content_id: Content ID

        Returns:
            Content object or None if not found
        """
        return self._contents.get(content_id)

    async def update_content(self, content: Content) -> None:
        """
        Update content record.

        Args:
            content: Content object with updated fields
        """
        if content.id not in self._contents:
            raise ValueError(f"Content not found: {content.id}")
        self._contents[content.id] = content

    async def delete_content(self, content_id: str) -> None:
        """
        Delete content record.

        Args:
            content_id: Content ID to delete
        """
        if content_id in self._contents:
            del self._contents[content_id]

    async def list_contents(self, filters: dict[str, Any] | None = None) -> list[Content]:
        """
        List all content with optional filters.

        Args:
            filters: Optional filters (not fully implemented in MVP)

        Returns:
            List of Content objects
        """
        contents = list(self._contents.values())
        if filters:
            filtered = []
            for content in contents:
                match = True
                for key, value in filters.items():
                    if key == "status" and content.status.value != value:
                        match = False
                        break
                    if key in content.metadata and content.metadata[key] != value:
                        match = False
                        break
                if match:
                    filtered.append(content)
            return filtered
        return contents
