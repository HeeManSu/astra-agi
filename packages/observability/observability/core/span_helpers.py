import functools
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


def _get_tracer():
    # Use the standard OTel global tracer provider
    # This assumes Client has been initialized and set the provider
    return trace.get_tracer("observability.tracing")

def trace_span(name: str | None = None, attributes: dict[str, Any] | None = None):
    """
    Decorator to trace a function execution.
    
    Args:
        name (str): Optional name for the span. Defaults to function name.
        attributes (dict): Optional initial attributes for the span.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = _get_tracer()
            span_name = name or func.__name__

            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    span.set_attributes(attributes)

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        return wrapper
    return decorator

def start_span(name: str, attributes: dict[str, Any] | None = None):
    """
    Context manager to start a span manually.
    Preserves original API returning a context manager.
    """
    tracer = _get_tracer()
    return tracer.start_as_current_span(name, attributes=attributes)

def set_span_attributes(attributes: dict[str, Any] | None = None):
    """
    Sets attributes on the current active span.
    """
    span = trace.get_current_span()
    if span.is_recording() and attributes:
        span.set_attributes(attributes)

def add_event(name: str, attributes: dict[str, Any] = None):
    """
    Adds an event to the current span.
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.add_event(name, attributes=attributes)
