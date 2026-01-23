"""
Abstract base class for storage backends.

Defines the interface that all storage implementations must follow.
"""

from abc import ABC, abstractmethod

from observability.tracing.span import Span
from observability.tracing.trace import Trace


class StorageBackend(ABC):
    """
    Abstract storage backend for observability data.

    Implementations: SQLiteStorage, PostgresStorage (future)
    """

    @abstractmethod
    async def init(self) -> None:
        """Initialize the storage (create tables, connections, etc.)."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the storage connection."""
        ...

    # Trace operations
    @abstractmethod
    async def save_trace(self, trace: Trace) -> None:
        """Save or update a trace."""
        ...

    @abstractmethod
    async def get_trace(self, trace_id: str) -> Trace | None:
        """Get a trace by ID."""
        ...

    @abstractmethod
    async def list_traces(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Trace]:
        """List traces with pagination."""
        ...

    # Span operations
    @abstractmethod
    async def save_span(self, span: Span) -> None:
        """Save or update a span."""
        ...

    @abstractmethod
    async def get_spans_for_trace(self, trace_id: str) -> list[Span]:
        """Get all spans for a trace, ordered by start_time."""
        ...
