"""Gemini embedder implementation using google-genai SDK."""

import os
from typing import Any

from framework.rag.embedders.base import Embedder
from framework.rag.exceptions import EmbeddingError


try:
    from google import genai
    from google.genai import Client as GeminiClient
except ImportError:
    genai = None  # type: ignore
    GeminiClient = None  # type: ignore


class GeminiEmbedder(Embedder):
    """Google Gemini embedding model using google-genai SDK."""

    def __init__(
        self,
        model: str = "gemini-embedding-001",
        api_key: str | None = None,
        dimensions: int = 768,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ):
        """
        Initialize Gemini embedder.

        Args:
            model: Gemini embedding model name (without models/ prefix)
            api_key: Google API key (uses GOOGLE_API_KEY env var if not provided)
            dimensions: Output embedding dimensions
            task_type: Task type for embedding (RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, etc.)
        """
        self.model = model.replace("models/", "")  # Strip prefix if provided
        self.api_key = api_key
        self._dimension = dimensions
        self.task_type = task_type
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Get or create Gemini client."""
        if self._client is None:
            if genai is None:
                raise EmbeddingError(
                    "google-genai package not installed. Install with: pip install google-genai"
                )

            api_key = self.api_key or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise EmbeddingError("Google API key not provided. Set GOOGLE_API_KEY env var.")

            self._client = genai.Client(api_key=api_key)

        return self._client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using Gemini API.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            embeddings = []

            for text in texts:
                request_params: dict[str, Any] = {
                    "contents": text,
                    "model": self.model,
                    "config": {
                        "task_type": self.task_type,
                        "output_dimensionality": self._dimension,
                    },
                }

                response = await self.client.aio.models.embed_content(**request_params)

                if response.embeddings and len(response.embeddings) > 0:
                    values = response.embeddings[0].values
                    if values is not None:
                        embeddings.append(list(values))
                    else:
                        embeddings.append([])
                else:
                    embeddings.append([])

            return embeddings

        except Exception as e:
            raise EmbeddingError(f"Failed to generate embeddings: {e}") from e

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension
