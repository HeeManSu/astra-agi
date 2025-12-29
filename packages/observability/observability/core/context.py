
from opentelemetry import trace


def get_current_span() -> trace.Span:
    """
    Returns the currently active span from the context.
    """
    return trace.get_current_span()

def get_current_trace_id() -> str | None:
    """
    Returns the current trace ID as a hex string.
    Returns None if no active span context exists.
    """
    span = get_current_span()
    if span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, "032x")
    return None

def get_current_span_id() -> str | None:
    """
    Returns the current span ID as a hex string.
    Returns None if no active span context exists.
    """
    span = get_current_span()
    if span.get_span_context().is_valid:
        return format(span.get_span_context().span_id, "016x")
    return None

def attach_context(token: object):
    """
    Attaches a context token. 
    (Wrapper around context.attach if needed, but usually context management is automatic)
    """
    # OpenTelemetry handles this via ContextVars automatically
