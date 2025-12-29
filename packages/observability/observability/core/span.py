from __future__ import annotations

from typing import Dict, Any, Optional
import time
import threading
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


_timing_lock = threading.Lock()
_span_start_perf_ns: Dict[int, int] = {}


def get_tracer() -> trace.Tracer:
    return trace.get_tracer("observability.instrumentation")


def start_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    tracer = get_tracer()
    span_ctx = tracer.start_as_current_span(name)
    parent = None
    try:
        parent = trace.get_current_span()
    except Exception:
        parent = None
    span = span_ctx.__enter__()
    try:
        parent_ctx = getattr(parent, "get_span_context", lambda: None)()
        if parent_ctx and getattr(parent_ctx, "is_valid", lambda: False)():
            span.set_attribute("span.parent_id", parent_ctx.span_id)
    except Exception:
        pass
    if attributes:
        for k, v in attributes.items():
            if v is not None:
                span.set_attribute(k, v)
    try:
        start_unix_ns = time.time_ns()
        start_perf_ns = time.perf_counter_ns()
        span.set_attribute("span.start_time_unix_ns", start_unix_ns)
        with _timing_lock:
            _span_start_perf_ns[id(span)] = start_perf_ns
    except Exception:
        pass
    return span_ctx, span


def end_span(span_ctx, span, status_code: StatusCode = StatusCode.UNSET, error: Optional[Exception] = None):
    from observability.semantic.conventions import AstraErrorAttributes
    try:
        if error:
            span.record_exception(error)
            span.set_status(Status(status_code=StatusCode.ERROR, description=str(error)))
            
            # Extract standard error attributes if present on the exception object
            # Check for retryable
            retryable = getattr(error, "retryable", None)
            if retryable is not None:
                span.set_attribute(AstraErrorAttributes.RETRYABLE, bool(retryable))
                
            # Check for error type
            error_type = getattr(error, "error_type", getattr(error, "type", None))
            if error_type:
                span.set_attribute(AstraErrorAttributes.TYPE, str(error_type))
                
            # Check for stage
            stage = getattr(error, "stage", None)
            if stage:
                span.set_attribute(AstraErrorAttributes.STAGE, str(stage))
                
            # Check for category
            category = getattr(error, "category", None)
            if category:
                span.set_attribute(AstraErrorAttributes.CATEGORY, str(category))

        elif status_code is not StatusCode.UNSET:
            span.set_status(Status(status_code=status_code))
        try:
            end_unix_ns = time.time_ns()
            span.set_attribute("span.end_time_unix_ns", end_unix_ns)
            end_perf_ns = time.perf_counter_ns()
            start_perf_ns = None
            with _timing_lock:
                start_perf_ns = _span_start_perf_ns.pop(id(span), None)
            if isinstance(start_perf_ns, int):
                duration_ms = (end_perf_ns - start_perf_ns) / 1_000_000.0
                span.set_attribute("span.duration_ms", duration_ms)
        except Exception:
            pass
    finally:
        span_ctx.__exit__(None, None, None)


def truncate_text(text: Optional[str], limit: int) -> Optional[str]:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[:limit]


def set_attributes(span, attrs: Dict[str, Any]) -> None:
    for k, v in attrs.items():
        if v is not None:
            span.set_attribute(k, v)
