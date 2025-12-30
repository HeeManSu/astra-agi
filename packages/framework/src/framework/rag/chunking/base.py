"""Base chunking strategy interface."""

from abc import ABC, abstractmethod

from framework.rag.vectordb.models import Document


class ChunkingStrategy(ABC):
    """Base class for document chunking strategies."""

    @abstractmethod
    async def chunk(self, document: Document) -> list[Document]:
        """
        Split a document into chunks.

        Args:
            document: Document to chunk

        Returns:
            List of chunked Document objects
        """
