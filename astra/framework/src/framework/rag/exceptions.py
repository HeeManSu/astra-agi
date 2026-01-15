"""RAG-related exceptions."""


class RagError(Exception):
    """Base exception for RAG errors."""

    def __init__(self, message: str, suggestion: str | None = None):
        self.message = message
        self.suggestion = suggestion
        full_message = message
        if suggestion:
            full_message += f"\n\nSuggestion: {suggestion}"
        super().__init__(full_message)


class RagConfigurationError(RagError):
    """Error in RAG pipeline configuration."""


class RagIngestionError(RagError):
    """Error during content ingestion."""


class RagQueryError(RagError):
    """Error during query execution."""


class ReaderError(RagError):
    """Error during content reading."""


class ChunkingError(RagError):
    """Error during content chunking."""


class EmbeddingError(RagError):
    """Error during embedding generation."""


class VectorDBError(RagError):
    """Error during vector database operations."""


class StorageError(RagError):
    """Error during content storage operations."""
