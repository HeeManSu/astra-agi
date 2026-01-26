"""
ObservabilityEngine - Main orchestrator for Astra Observability.

Manages:
- Trace lifecycle (start, end)
- Span lifecycle (start, end)
- In-memory registry of active traces/spans
- Persistence to storage backend

Note: This is the internal implementation. Use the public API from instrument.py:
    from observability import trace, span, log
"""

from __future__ import annotations

from typing import Any

from observability.console_debugger import ConsoleDebugger
from observability.logs.model import Log, LogLevel
from observability.storage.base import StorageBackend
from observability.tracing.span import Span, SpanKind, SpanStatus
from observability.tracing.trace import Trace, TraceStatus


class ObservabilityEngine:
    """
    Main orchestrator for observability.

    Tracks active traces and spans in memory, persists to storage on completion.

    Usage (via instrument.py):
        from observability import init, trace, span, log

        init(engine)  # At startup

        async with trace("my_workflow"):
            async with span("step_1"):
                await log(LogLevel.INFO, "Step started")
    """

    def __init__(self, storage: StorageBackend, debug_mode: bool = False):
        """
        Initialize the engine.

        Args:
            storage: Storage backend for persistence
            debug_mode: Whether to enable console debug output (default: False)
        """
        self._storage = storage
        self._debug_mode = debug_mode

        # Console debugger for real-time output
        self._console_debugger = ConsoleDebugger(enabled=debug_mode)

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

        # Notify console debugger
        self._console_debugger.trace_start(trace.trace_id, name, trace.attributes)

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

        # Notify console debugger
        self._console_debugger.trace_end(
            trace_id,
            status.value,
            trace.duration_ms or 0.0,  # Default to 0 if not calculated
        )

        # Automatic trace duration logging
        trace_msg = (
            f"Trace '{trace.name}' completed in {trace.duration_ms}ms with status {status.value}"
        )
        await self.log_event(
            Log(
                trace_id=trace_id,
                level=LogLevel.DEBUG if status == TraceStatus.SUCCESS else LogLevel.ERROR,
                message=trace_msg,
                attributes={
                    "duration_ms": trace.duration_ms,
                    "total_tokens": trace.total_tokens,
                    "input_tokens": trace.input_tokens,
                    "output_tokens": trace.output_tokens,
                    "thoughts_tokens": trace.thoughts_tokens,
                    "model": trace.model,
                },
            )
        )

        await self._storage.save_trace(trace)

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

        # Notify console debugger
        self._console_debugger.span_start(
            span.span_id, trace_id, name, kind.value, parent_span_id, span.attributes
        )

        return span.span_id

    def update_span(
        self,
        span_id: str,
        attributes: dict[str, Any],
    ) -> None:
        """
        Update attributes of an active span.

        Args:
            span_id: ID of the span to update
            attributes: New attributes to merge with existing ones
        """
        span = self._active_spans.get(span_id)
        if span:
            span.attributes.update(attributes)
            # Notify console debugger (if we want real-time updates)
            # For now we'll just update the span object in memory
        else:
            # Span may have already finished or trace id is invalid
            pass

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

        # Aggregate token usage into the trace
        trace = self._active_traces.get(span.trace_id)
        if trace:
            attrs = span.attributes or {}
            total = attrs.get("total_tokens", 0) or 0
            input_tokens = attrs.get("input_tokens", 0) or attrs.get("prompt_tokens", 0) or 0
            output_tokens = attrs.get("output_tokens", 0) or attrs.get("completion_tokens", 0) or 0
            thoughts_tokens = attrs.get("thoughts_tokens", 0) or 0
            model_name = attrs.get("model") or attrs.get("model_name")

            trace.add_token_usage(
                total=total,
                input_=input_tokens,
                output=output_tokens,
                thoughts=thoughts_tokens,
                model_name=model_name,
            )

        # Notify console debugger
        self._console_debugger.span_end(
            span.span_id,
            span.name,
            status.value,
            span.duration_ms or 0.0,  # Default to 0 if not calculated
            span.attributes,
        )

        # Automatic duration logging
        duration_msg = f"Span '{span.name}' completed in {span.duration_ms}ms"
        if status == SpanStatus.ERROR:
            duration_msg += f" with error: {error}"

        # Add metrics to log attributes if available
        log_attrs = {"duration_ms": span.duration_ms}
        if span.attributes:
            for k in ["total_tokens", "input_tokens", "output_tokens", "thoughts_tokens", "model"]:
                if k in span.attributes:
                    log_attrs[k] = span.attributes[k]

        await self.log_event(
            Log(
                trace_id=span.trace_id,
                span_id=span.span_id,
                level=LogLevel.DEBUG if status == SpanStatus.SUCCESS else LogLevel.ERROR,
                message=duration_msg,
                attributes=log_attrs,
            )
        )

        await self._storage.save_span(span)

    # Logging

    async def log_event(self, log: Log) -> None:
        """Log a structured event."""
        if log.level == LogLevel.DEBUG and not self._debug_mode:
            return

        # Notify console debugger (real-time) - only if span_id is set
        if log.span_id:
            self._console_debugger.span_log(
                log.span_id, log.level.value, log.message, log.attributes
            )

        # Persist log to database
        await self._storage.save_log(log)
