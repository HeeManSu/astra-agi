"""
ObservabilityEngine - Main orchestrator for Astra Observability.

Manages:
- Trace lifecycle (start, end)
- Span lifecycle (start, end)
- In-memory registry of active traces/spans
- Persistence to storage backend
"""

from typing import Any

from observability.storage.base import StorageBackend
from observability.tracing.span import Span, SpanKind, SpanStatus
from observability.tracing.trace import Trace, TraceStatus


class ObservabilityEngine:
    """
    Main orchestrator for observability.

    Tracks active traces and spans in memory, persists to storage on completion.

    Usage:
        engine = ObservabilityEngine(storage)

        trace_id = engine.start_trace("my_workflow")
        span_id = engine.start_span(trace_id, "step_1", SpanKind.STEP)
        await engine.end_span(span_id, SpanStatus.SUCCESS)
        await engine.end_trace(trace_id, TraceStatus.SUCCESS)
    """

    def __init__(self, storage: StorageBackend):
        """
        Initialize the engine.

        Args:
            storage: Storage backend for persistence
        """
        self._storage = storage

        # In-memory registries for active (in-flight) traces and spans
        self._active_traces: dict[str, Trace] = {}
        self._active_spans: dict[str, Span] = {}

    @property
    def storage(self) -> StorageBackend:
        """Get the storage backend."""
        return self._storage

    # Trace lifecycle

    def start_trace(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        """
        Start a new trace.

        Args:
            name: Human-readable trace name
            attributes: Optional metadata

        Returns:
            trace_id: Unique identifier for the trace
        """
        trace = Trace(name=name, attributes=attributes or {})
        self._active_traces[trace.trace_id] = trace
        return trace.trace_id

    async def end_trace(
        self,
        trace_id: str,
        status: TraceStatus,
    ) -> None:
        """
        End a trace and persist it.

        Args:
            trace_id: ID of the trace to end
            status: Final status of the trace
        """
        trace = self._active_traces.pop(trace_id, None)
        if trace is None:
            raise ValueError(f"Trace {trace_id} not found in active traces")

        trace.end(status)
        await self._storage.save_trace(trace)

    def get_active_trace(self, trace_id: str) -> Trace | None:
        """Get an active (in-flight) trace."""
        return self._active_traces.get(trace_id)

    # Span lifecycle

    def start_span(
        self,
        trace_id: str,
        name: str,
        kind: SpanKind,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        """
        Start a new span within a trace.

        Args:
            trace_id: ID of the parent trace
            name: Human-readable span name
            kind: Type of operation
            parent_span_id: Optional parent span for hierarchy
            attributes: Optional metadata

        Returns:
            span_id: Unique identifier for the span
        """
        span = Span(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            attributes=attributes or {},
        )
        self._active_spans[span.span_id] = span
        return span.span_id

    async def end_span(
        self,
        span_id: str,
        status: SpanStatus,
        error: str | None = None,
    ) -> None:
        """
        End a span and persist it.

        Args:
            span_id: ID of the span to end
            status: Final status of the span
            error: Optional error message if status is ERROR
        """
        span = self._active_spans.pop(span_id, None)
        if span is None:
            raise ValueError(f"Span {span_id} not found in active spans")

        span.end(status, error)
        await self._storage.save_span(span)

    def get_active_span(self, span_id: str) -> Span | None:
        """Get an active (in-flight) span."""
        return self._active_spans.get(span_id)

    # Convenience: set attributes on active span/trace

    def set_span_attribute(self, span_id: str, key: str, value: Any) -> None:
        """Set an attribute on an active span."""
        span = self._active_spans.get(span_id)
        if span:
            span.attributes[key] = value

    def set_trace_attribute(self, trace_id: str, key: str, value: Any) -> None:
        """Set an attribute on an active trace."""
        trace = self._active_traces.get(trace_id)
        if trace:
            trace.attributes[key] = value
