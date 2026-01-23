"""Query module for Astra Observability."""

from .traces import get_trace_with_spans, list_traces


__all__ = ["get_trace_with_spans", "list_traces"]
