"""Base vector database interface."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from framework.rag.vectordb.models import Document


class SearchType(str, Enum):
    """Search type enumeration."""

    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class VectorDB(ABC):
    """Base class for vector databases."""

    @abstractmethod
    async def insert(
        self, documents: list[Document], filters: dict[str, Any] | None = None
    ) -> None:
        """
        Insert documents with embeddings.

        Args:
            documents: List of Document objects with embeddings
            filters: Optional metadata filters
        """

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        search_type: SearchType = SearchType.VECTOR,
    ) -> list[Document]:
        """
        Search for relevant documents.

        Args:
            query: Search query string
            limit: Maximum number of results
            filters: Optional metadata filters
            search_type: Type of search to perform

        Returns:
            List of relevant Document objects
        """

    @abstractmethod
    async def upsert(self, content_hash: str, documents: list[Document]) -> None:
        """
        Update existing content or insert if not exists.

        Args:
            content_hash: Content hash identifier
            documents: List of Document objects
        """

    @abstractmethod
    async def delete_by_content_id(self, content_id: str) -> None:
        """
        Delete all documents for a content ID.

        Args:
            content_id: Content ID to delete
        """

    @abstractmethod
    def content_hash_exists(self, content_hash: str) -> bool:
        """
        Check if content hash already exists.

        Args:
            content_hash: Content hash to check

        Returns:
            True if content exists, False otherwise
        """
