"""
Astra Observability Package - Phase 0

Local-first observability for agentic workflows.
Provides tracing with SQLite storage.

This package is framework-agnostic (no FastAPI, no HTTP).
"""

from .engine import ObservabilityEngine
from .query.traces import TraceWithSpans, get_trace_with_spans, list_traces
from .storage.base import StorageBackend
from .storage.sqlite import SQLiteStorage
from .tracing.span import Span, SpanKind, SpanStatus
from .tracing.trace import Trace, TraceStatus


__version__ = "0.1.0"

__all__ = [
    # Engine
    "ObservabilityEngine",
    # Query
    "TraceWithSpans",
    "get_trace_with_spans",
    "list_traces",
    # Span
    "Span",
    "SpanKind",
    "SpanStatus",
    # Storage
    "SQLiteStorage",
    "StorageBackend",
    # Trace
    "Trace",
    "TraceStatus",
]
