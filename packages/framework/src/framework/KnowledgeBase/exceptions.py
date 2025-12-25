"""Exceptions for KnowledgeBase operations."""


class KnowledgeBaseError(Exception):
    """Base exception for KnowledgeBase operations."""


class ReaderError(KnowledgeBaseError):
    """Error during content reading."""


class ChunkingError(KnowledgeBaseError):
    """Error during document chunking."""


class EmbeddingError(KnowledgeBaseError):
    """Error during embedding generation."""


class VectorDBError(KnowledgeBaseError):
    """Error during vector database operations."""


class ContentsDBError(KnowledgeBaseError):
    """Error during contents database operations."""
