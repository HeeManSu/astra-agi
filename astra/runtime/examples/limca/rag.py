"""RAG manager for Limca.

Provides a unified interface for embeddings and vector search.
"""

import os
from typing import Any

from framework.rag.embedders.gemini import GeminiEmbedder
from framework.rag.vectordb.lancedb import LanceDB
from framework.rag.vectordb.models import Document


class LimcaRAG:
    """RAG manager that handles embeddings and vector search for Limca."""

    def __init__(
        self,
        db_path: str = ".limca/vectordb",
        embedder: Any = None,
    ) -> None:
        """Initialize RAG manager.

        Args:
            db_path: Path to store LanceDB data
            embedder: Optional custom embedder (defaults to Gemini)
        """
        self._embedder = embedder
        self._db_path = db_path
        self._vector_db: LanceDB | None = None

    @property
    def embedder(self) -> Any:
        """Get or create embedder."""
        if self._embedder is None:
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                self._embedder = GeminiEmbedder(
                    model="models/text-embedding-004",
                    api_key=api_key,
                )
        return self._embedder

    @property
    def vector_db(self) -> LanceDB:
        """Get or create vector database."""
        if self._vector_db is None:
            self._vector_db = LanceDB(
                uri=self._db_path,
                table_name="limca_docs",
                embedder=self.embedder,
            )
        return self._vector_db

    async def index_code(self, file_path: str, content: str, metadata: dict | None = None) -> None:
        """Index a code file for semantic search.

        Args:
            file_path: Path to the file
            content: File content
            metadata: Optional additional metadata
        """
        if not self.embedder:
            return

        # Create document
        doc = Document(
            content=content,
            source=file_path,
            metadata=metadata or {},
            name=os.path.basename(file_path),
        )

        # Generate embedding
        embeddings = await self.embedder.embed([content])
        doc.embedding = embeddings[0]

        # Insert into vector DB
        await self.vector_db.insert([doc])

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search for relevant code chunks.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of search results with content, source, and metadata
        """
        if not self.embedder:
            return []

        try:
            docs = await self.vector_db.search(query, limit=limit)
            return [
                {
                    "content": doc.content,
                    "source": doc.source or "",
                    "metadata": doc.metadata,
                }
                for doc in docs
            ]
        except Exception:
            return []

    async def embed_query(self, query: str) -> list[float] | None:
        """Get embedding for a query.

        Args:
            query: Query text

        Returns:
            Embedding vector or None
        """
        if not self.embedder:
            return None
        try:
            embeddings = await self.embedder.embed([query])
            return embeddings[0]
        except Exception:
            return None


# Global RAG instance
_rag: LimcaRAG | None = None


def get_rag() -> LimcaRAG:
    """Get the global RAG instance."""
    global _rag
    if _rag is None:
        _rag = LimcaRAG()
    return _rag
