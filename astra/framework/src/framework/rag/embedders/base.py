"""Base embedder interface."""

from abc import ABC, abstractmethod


class Embedder(ABC):
    """Base class for text embedders."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Convert texts to embeddings.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Get embedding dimension.

        Returns:
            Dimension of embeddings
        """
