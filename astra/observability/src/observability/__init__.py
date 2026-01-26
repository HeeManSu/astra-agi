"""
Astra Observability Package

Local-first observability for agentic workflows.

Public API:
    from observability import init, trace, span, log, LogLevel

    # At startup
    init(engine)

    # In code
    async with trace("my_workflow", attributes={...}):
        async with span("step_1"):
            await log(LogLevel.INFO, "Step started")
"""

# Public API (ContextVars-based instrumentation)
# Internal (for runtime initialization)
from .engine import ObservabilityEngine
from .instrument import (
    get_current_span_id,
    get_current_trace_id,
    get_engine,
    init,
    log,
    span,
    trace,
    update_span,
)

# Types and enums
from .logs.model import Log, LogLevel

# Queries
from .query.traces import TraceWithSpans, get_logs_for_trace, get_trace_with_spans, list_traces
from .storage.base import StorageBackend
from .storage.mongodb import TelemetryMongoDB
from .storage.sqlite import TelemetrySQLite
from .tracing.span import Span, SpanKind, SpanStatus
from .tracing.trace import Trace, TraceStatus


__version__ = "0.1.0"

__all__ = [
    # Public API
    "get_current_span_id",
    "get_current_trace_id",
    "get_engine",
    "init",
    "log",
    "LogLevel",
    "span",
    "trace",
    "update_span",
    # Types (for type hints)
    "Log",
    "Span",
    "SpanKind",
    "SpanStatus",
    "Trace",
    "TraceStatus",
    # Internal (for setup)
    "ObservabilityEngine",
    "StorageBackend",
    "TelemetryMongoDB",
    "TelemetrySQLite",
    # Queries
    "TraceWithSpans",
    "get_trace_with_spans",
    "get_logs_for_trace",
    "list_traces",
]
