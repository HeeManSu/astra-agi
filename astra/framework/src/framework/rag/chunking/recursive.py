"""Recursive chunking strategy."""

from framework.rag.chunking.base import ChunkingStrategy
from framework.rag.vectordb.models import Document


class RecursiveChunking(ChunkingStrategy):
    """Recursive chunking that splits by separators in order of preference."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] | None = None,
    ):
        """
        Initialize recursive chunking.

        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            separators: List of separators to try (in order)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

    async def chunk(self, document: Document) -> list[Document]:
        """
        Split document into chunks recursively.

        Args:
            document: Document to chunk

        Returns:
            List of chunked Document objects
        """
        if len(document.content) <= self.chunk_size:
            return [document]

        chunks: list[Document] = []
        text = document.content
        chunk_index = 0

        while text:
            if len(text) <= self.chunk_size:
                chunks.append(
                    Document(
                        content=text,
                        metadata=document.metadata.copy(),
                        id=f"{document.id}_{chunk_index}" if document.id else None,
                        name=document.name,
                        source=document.source,
                        chunk_index=chunk_index,
                        content_id=document.content_id,
                    )
                )
                break

            chunk_text = None
            for separator in self.separators:
                if separator:
                    split_pos = text[: self.chunk_size].rfind(separator)
                    if split_pos > 0:
                        chunk_text = text[: split_pos + len(separator)]
                        text = text[split_pos + len(separator) :]
                        break

            if chunk_text is None:
                chunk_text = text[: self.chunk_size]
                text = text[self.chunk_size :]

            chunks.append(
                Document(
                    content=chunk_text.strip(),
                    metadata=document.metadata.copy(),
                    id=f"{document.id}_{chunk_index}" if document.id else None,
                    name=document.name,
                    source=document.source,
                    chunk_index=chunk_index,
                    content_id=document.content_id,
                )
            )
            chunk_index += 1

            if text and self.chunk_overlap > 0 and len(chunk_text) > self.chunk_overlap:
                overlap_text = chunk_text[-self.chunk_overlap :]
                text = overlap_text + text

        return chunks
