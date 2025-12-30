"""Base reader interface."""

from abc import ABC, abstractmethod
from typing import Any

from framework.rag.vectordb.models import Document


class Reader(ABC):
    """Base class for content readers."""

    @abstractmethod
    async def read(self, source: Any, name: str | None = None) -> list[Document]:
        """
        Read and parse content from source.

        Args:
            source: Content source (file path, URL, text, etc.)
            name: Optional name for the content

        Returns:
            List of Document objects
        """

    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported file extensions or MIME types.

        Returns:
            List of supported formats
        """
        return []
