"""LanceDB vector database implementation."""

from typing import Any

import lancedb
import pyarrow as pa

from framework.rag.exceptions import VectorDBError
from framework.rag.vectordb.base import SearchType, VectorDB
from framework.rag.vectordb.models import Document


class LanceDB(VectorDB):
    """LanceDB vector database implementation."""

    def __init__(
        self,
        uri: str = "lancedb_data",
        table_name: str = "documents",
        embedder: Any | None = None,
    ):
        """
        Initialize LanceDB.

        Args:
            uri: Database URI (path for local storage)
            table_name: Table name for documents
            embedder: Embedder instance (required for search)
        """
        self.uri = uri
        self.table_name = table_name
        self.embedder = embedder
        self._db: Any = None
        self._table: Any = None
        self._content_hashes: set[str] = set()

    async def _ensure_db(self) -> None:
        """Ensure database and table are initialized."""
        try:
            if self._db is None:
                self._db = lancedb.connect(self.uri)

            if self._table is None:
                try:
                    self._table = self._db.open_table(self.table_name)
                except Exception:
                    self._table = None
        except ImportError:
            raise VectorDBError("lancedb package not installed. Install with: pip install lancedb")

    async def insert(
        self, documents: list[Document], filters: dict[str, Any] | None = None
    ) -> None:
        """
        Insert documents with embeddings.

        Args:
            documents: List of Document objects with embeddings
            filters: Optional metadata filters (not used in LanceDB MVP)
        """
        await self._ensure_db()

        if not documents:
            return

        if not all(doc.embedding for doc in documents):
            raise VectorDBError("Documents must have embeddings before insertion")

        try:
            data = []
            for doc in documents:
                row = {
                    "id": doc.id or "",
                    "content": doc.content,
                    "embedding": doc.embedding,
                    "metadata": doc.metadata,
                    "name": doc.name or "",
                    "source": doc.source or "",
                    "chunk_index": doc.chunk_index or 0,
                    "content_id": doc.content_id or "",
                }
                data.append(row)

            table = pa.Table.from_pylist(data)
            if self._table is None:
                self._table = self._db.create_table(self.table_name, table)
            else:
                self._table.add(table)
        except ImportError:
            raise VectorDBError("pyarrow package not installed. Install with: pip install pyarrow")
        except Exception as e:
            raise VectorDBError(f"Failed to insert documents: {e}") from e

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
            filters: Optional metadata filters (not fully supported in MVP)
            search_type: Type of search (only VECTOR supported in MVP)

        Returns:
            List of relevant Document objects
        """
        await self._ensure_db()

        if self._table is None:
            return []

        if not self.embedder:
            raise VectorDBError("Embedder required for search")

        try:
            query_embedding = (await self.embedder.embed([query]))[0]
            # Use to_arrow().to_pylist() - to_pylist() doesn't exist on LanceVectorQueryBuilder
            arrow_table = self._table.search(query_embedding).limit(limit).to_arrow()
            results = arrow_table.to_pylist()

            documents: list[Document] = []
            for result in results:
                doc = Document(
                    id=result.get("id"),
                    content=result.get("content", ""),
                    metadata=result.get("metadata", {}),
                    name=result.get("name"),
                    source=result.get("source"),
                    chunk_index=result.get("chunk_index"),
                    content_id=result.get("content_id"),
                    embedding=result.get("embedding"),
                )
                documents.append(doc)

            return documents
        except Exception as e:
            raise VectorDBError(f"Failed to search: {e}") from e

    async def upsert(self, content_hash: str, documents: list[Document]) -> None:
        """
        Update existing content or insert if not exists.

        Args:
            content_hash: Content hash identifier
            documents: List of Document objects
        """
        if self.content_hash_exists(content_hash):
            await self.delete_by_content_id(content_hash)
        await self.insert(documents)

    async def delete_by_content_id(self, content_id: str) -> None:
        """
        Delete all documents for a content ID.

        Args:
            content_id: Content ID to delete
        """
        await self._ensure_db()

        if self._table is None:
            return

        try:
            self._table.delete(f"content_id = '{content_id}'")
        except Exception as e:
            raise VectorDBError(f"Failed to delete documents: {e}") from e

    def content_hash_exists(self, content_hash: str) -> bool:
        """
        Check if content hash already exists.

        Args:
            content_hash: Content hash to check

        Returns:
            True if content exists, False otherwise
        """
        return content_hash in self._content_hashes
