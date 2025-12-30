"""HuggingFace embedder implementation using HuggingFace Inference API."""

import os

from framework.rag.embedders.base import Embedder
from framework.rag.exceptions import EmbeddingError


class HuggingFaceEmbedder(Embedder):
    """HuggingFace embedding model using Inference API."""

    def __init__(
        self,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        api_key: str | None = None,
    ):
        """
        Initialize HuggingFace embedder.

        Args:
            model: HuggingFace model name (e.g., "sentence-transformers/all-MiniLM-L6-v2")
            api_key: HuggingFace API key (uses HUGGINGFACE_API_KEY env var if not provided)
                     Optional for public models, required for private models
        """
        self.model = model
        self.api_key = api_key or os.getenv("HUGGINGFACE_API_KEY")
        self._dimension = self._get_model_dimension(model)

    def _get_model_dimension(self, model: str) -> int:
        """Get embedding dimension for common models."""
        dimension_map = {
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-mpnet-base-v2": 768,
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
            "intfloat/multilingual-e5-large": 1024,
            "intfloat/e5-large-v2": 1024,
            "BAAI/bge-small-en-v1.5": 384,
            "BAAI/bge-base-en-v1.5": 768,
            "BAAI/bge-large-en-v1.5": 1024,
        }
        return dimension_map.get(model, 384)  # Default to 384

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using HuggingFace Inference API.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            from huggingface_hub import AsyncInferenceClient

            client = AsyncInferenceClient(token=self.api_key)

            embeddings: list[list[float]] = []
            for text in texts:
                response = await client.feature_extraction(text=text, model=self.model)

                if isinstance(response, list):
                    embedding = response
                elif hasattr(response, "tolist"):
                    embedding = response.tolist()
                else:
                    embedding = list(response)

                if not embedding:
                    raise EmbeddingError(f"Empty embedding returned for text: {text[:50]}...")

                embeddings.append(embedding)

            return embeddings
        except ImportError as e:
            raise EmbeddingError(
                "huggingface_hub package not installed. Install with: pip install huggingface-hub"
            ) from e
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embeddings: {e}") from e

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension
