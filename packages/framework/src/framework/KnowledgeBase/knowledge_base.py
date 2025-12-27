"""Main KnowledgeBase class for RAG operations."""

import hashlib
from pathlib import Path
from typing import Any
import uuid

from framework.KnowledgeBase.chunking.base import ChunkingStrategy
from framework.KnowledgeBase.chunking.recursive import RecursiveChunking
from framework.KnowledgeBase.embedders.base import Embedder
from framework.KnowledgeBase.exceptions import (
    ChunkingError,
    EmbeddingError,
    ReaderError,
    StorageError,
    VectorDBError,
)
from framework.KnowledgeBase.readers.base import Reader
from framework.KnowledgeBase.readers.factory import ReaderFactory
from framework.KnowledgeBase.storage.base import ContentStore
from framework.KnowledgeBase.storage.in_memory import InMemoryStore
from framework.KnowledgeBase.vectordb.base import SearchType, VectorDB
from framework.KnowledgeBase.vectordb.models import Content, ContentStatus, Document


class KnowledgeBase:
    """Main class for managing knowledge bases and RAG operations."""

    def __init__(
        self,
        vector_db: VectorDB,
        embedder: Embedder | None = None,
        chunking: ChunkingStrategy | None = None,
        storage: ContentStore | None = None,
        max_results: int = 10,
    ):
        """
        Initialize KnowledgeBase.

        Args:
            vector_db: Vector database instance
            embedder: Embedder instance (required if vector_db doesn't have one)
            chunking: Chunking strategy (defaults to RecursiveChunking)
            storage: Content store (defaults to InMemoryStore)
            max_results: Default max results for search
        """
        self.vector_db = vector_db
        self.embedder = embedder or getattr(vector_db, "embedder", None)
        self.chunking = chunking or RecursiveChunking()
        self.storage = storage or InMemoryStore()
        self.max_results = max_results

    def _build_content_hash(self, source: str, metadata: dict[str, Any] | None = None) -> str:
        """Build content hash for deduplication."""
        content_str = f"{source}:{metadata or {}!s}"
        return hashlib.sha256(content_str.encode()).hexdigest()

    async def add_content(
        self,
        path: str | Path | None = None,
        url: str | None = None,
        text: str | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        reader: Reader | None = None,
        upsert: bool = True,
        skip_if_exists: bool = False,
    ) -> str:
        """
        Add content to knowledge base.

        Args:
            path: File path to add
            url: URL to fetch and add
            text: Text content to add
            name: Optional name for content
            metadata: Optional metadata
            reader: Optional custom reader
            upsert: Whether to update if exists
            skip_if_exists: Whether to skip if already exists

        Returns:
            Content ID

        Raises:
            ValueError: If no source provided
        """
        if not any([path, url, text]):
            raise ValueError("At least one of path, url, or text must be provided")

        source: str | Path
        if path:
            source = path
        elif url:
            source = url
        else:
            source = text  # type: ignore[assignment]  # text is guaranteed to be str here

        try:
            content_hash = self._build_content_hash(str(source), metadata)
            content_id = str(uuid.uuid4())

            content = Content(
                id=content_id,
                name=name or str(source),
                source=str(source),
                metadata=metadata or {},
                content_hash=content_hash,
                status=ContentStatus.PROCESSING,
            )

            if skip_if_exists and self.vector_db.content_hash_exists(content_hash):
                return content_id

            await self.storage.create(content)

            documents = await self._read_content(source, reader, name)
            chunked_docs = await self._chunk_documents(documents, content_id)
            await self._embed_and_store(chunked_docs, content, upsert)

            content.update_status(ContentStatus.COMPLETED)
            await self.storage.update(content)

            return content_id

        except Exception as e:
            if "content" in locals():
                content.update_status(ContentStatus.FAILED, str(e))
                await self.storage.update(content)
            raise

    async def _read_content(
        self, source: str | Path, reader: Reader | None, name: str | None
    ) -> list[Document]:
        """Read content using appropriate reader."""
        try:
            if reader:
                selected_reader = reader
            elif isinstance(source, str) and source.startswith(("http://", "https://")):
                # URL content - check this first
                selected_reader = ReaderFactory.get_reader_for_url(source)
            elif isinstance(source, Path):
                # Explicit Path object - file path
                selected_reader = ReaderFactory.get_reader_for_path(source)
            elif isinstance(source, str) and len(source) < 260 and self._is_valid_path(source):
                # String that looks like a file path (short, no newlines, exists)
                selected_reader = ReaderFactory.get_reader_for_path(source)
            else:
                # Default: treat as raw text content
                selected_reader = ReaderFactory.get_reader_for_text()

            documents = await selected_reader.read(source, name)
            return documents

        except Exception as e:
            raise ReaderError(f"Failed to read content: {e}") from e

    def _is_valid_path(self, source: str) -> bool:
        """Check if source string is likely a valid file path."""
        # Quick checks to avoid OS errors on long strings
        if "\n" in source or "\r" in source:
            return False
        try:
            return Path(source).exists()
        except OSError:
            return False

    async def _chunk_documents(self, documents: list[Document], content_id: str) -> list[Document]:
        """Chunk documents using chunking strategy."""
        try:
            chunked_docs: list[Document] = []
            for doc in documents:
                doc.content_id = content_id
                chunks = await self.chunking.chunk(doc)
                chunked_docs.extend(chunks)

            return chunked_docs

        except Exception as e:
            raise ChunkingError(f"Failed to chunk documents: {e}") from e

    async def _embed_and_store(
        self, documents: list[Document], content: Content, upsert: bool
    ) -> None:
        """Generate embeddings and store in vector database."""
        try:
            if not self.embedder:
                raise EmbeddingError("Embedder required for embedding generation")

            texts = [doc.content for doc in documents]
            embeddings = await self.embedder.embed(texts)

            for doc, embedding in zip(documents, embeddings, strict=False):
                doc.embedding = embedding

            if upsert and content.content_hash:
                await self.vector_db.upsert(content.content_hash, documents)
            else:
                await self.vector_db.insert(documents, content.metadata)

        except Exception as e:
            raise VectorDBError(f"Failed to store documents: {e}") from e

    async def search(
        self,
        query: str,
        limit: int | None = None,
        filters: dict[str, Any] | None = None,
        search_type: SearchType = SearchType.VECTOR,
    ) -> list[Document]:
        """
        Search knowledge base.

        Args:
            query: Search query
            limit: Maximum results (defaults to max_results)
            filters: Optional metadata filters
            search_type: Type of search

        Returns:
            List of relevant Document objects
        """
        try:
            limit = limit or self.max_results
            results = await self.vector_db.search(query, limit, filters, search_type)
            return results

        except Exception as e:
            raise VectorDBError(f"Search failed: {e}") from e

    async def delete_content(self, content_id: str) -> None:
        """
        Delete content and associated documents.

        Args:
            content_id: Content ID to delete
        """
        try:
            await self.vector_db.delete_by_content_id(content_id)
            await self.storage.delete(content_id)
        except Exception as e:
            raise StorageError(f"Failed to delete content: {e}") from e

    async def update_content_metadata(self, content_id: str, metadata: dict[str, Any]) -> None:
        """
        Update content metadata.

        Args:
            content_id: Content ID
            metadata: Updated metadata
        """
        content = await self.storage.get(content_id)
        if not content:
            raise StorageError(f"Content not found: {content_id}")

        content.metadata.update(metadata)
        await self.storage.update(content)

    async def list_contents(self, filters: dict[str, Any] | None = None) -> list[Content]:
        """
        List all content.

        Args:
            filters: Optional filters

        Returns:
            List of Content objects
        """
        return await self.storage.list(filters)
