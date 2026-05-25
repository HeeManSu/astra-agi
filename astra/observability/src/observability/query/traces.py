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


SYSTEM_TRACE_PREFIXES = ("server.",)


def _is_system_trace(trace: Trace) -> bool:
    """True for internal/operational traces (e.g. server.startup) that should
    be hidden from user-facing trace lists."""
    return any(trace.name.startswith(p) for p in SYSTEM_TRACE_PREFIXES)


async def list_traces(
    storage: StorageBackend,
    limit: int = 50,
    offset: int = 0,
    include_system: bool = False,
) -> list[Trace]:
    """
    List traces with pagination.

    Args:
        storage: Storage backend to query
        limit: Maximum number of traces to return
        offset: Number of traces to skip
        include_system: If True, include operational traces like ``server.startup``.
            Default False so user-facing dashboards only show request traces.

    Returns:
        List of traces ordered by start_time DESC
    """
    if include_system:
        return await storage.list_traces(limit=limit, offset=offset)

    # Over-fetch and filter, so the post-filter result still respects the
    # caller's limit. System traces are rare so a 2x window is safe.
    raw = await storage.list_traces(limit=limit * 2 + 16, offset=offset)
    filtered = [t for t in raw if not _is_system_trace(t)]
    return filtered[:limit]


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


async def get_logs_for_trace(
    storage: StorageBackend,
    trace_id: str,
    limit: int = 500,
) -> list:
    """
    Get all logs for a trace.

    Args:
        storage: Storage backend to query
        trace_id: ID of the trace
        limit: Maximum number of logs to return

    Returns:
        List of logs ordered by timestamp
    """

    return await storage.list_logs(trace_id, limit=limit)
