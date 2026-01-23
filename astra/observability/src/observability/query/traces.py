"""
Pure Python query functions for traces.

These functions provide the query layer for observability data.
They do NOT depend on any web framework.
"""

from dataclasses import dataclass

from observability.storage.base import StorageBackend
from observability.tracing.span import Span
from observability.tracing.trace import Trace


@dataclass
class TraceWithSpans:
    """A trace with its associated spans."""

    trace: Trace
    spans: list[Span]


async def list_traces(
    storage: StorageBackend,
    limit: int = 50,
    offset: int = 0,
) -> list[Trace]:
    """
    List traces with pagination.

    Args:
        storage: Storage backend to query
        limit: Maximum number of traces to return
        offset: Number of traces to skip

    Returns:
        List of traces ordered by start_time DESC
    """
    return await storage.list_traces(limit=limit, offset=offset)


async def get_trace_with_spans(
    storage: StorageBackend,
    trace_id: str,
) -> TraceWithSpans | None:
    """
    Get a trace with all its spans.

    Args:
        storage: Storage backend to query
        trace_id: ID of the trace to retrieve

    Returns:
        TraceWithSpans or None if not found
    """
    trace = await storage.get_trace(trace_id)
    if trace is None:
        return None

    spans = await storage.get_spans_for_trace(trace_id)
    return TraceWithSpans(trace=trace, spans=spans)
