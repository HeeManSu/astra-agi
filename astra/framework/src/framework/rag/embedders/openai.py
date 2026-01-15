"""OpenAI embedder implementation."""

import os

from openai import AsyncOpenAI

from framework.rag.embedders.base import Embedder
from framework.rag.exceptions import EmbeddingError


class OpenAIEmbedder(Embedder):
    """OpenAI embedding model."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None):
        """
        Initialize OpenAI embedder.

        Args:
            model: OpenAI embedding model name
            api_key: OpenAI API key (uses OPENAI_API_KEY env var if not provided)
        """
        self.model = model
        self.api_key = api_key
        self._dimension = 1536 if "3-small" in model else 3072

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using OpenAI API.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise EmbeddingError("OpenAI API key not provided")

            client = AsyncOpenAI(api_key=api_key)
            response = await client.embeddings.create(model=self.model, input=texts)

            return [item.embedding for item in response.data]
        except ImportError as e:
            raise EmbeddingError(
                "openai package not installed. Install with: pip install openai"
            ) from e
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embeddings: {e}") from e

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension
