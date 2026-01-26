"""
ContextVars-based observability instrumentation.

Provides implicit context propagation for traces and spans.
No parameter passing needed - just call span() and log() anywhere.

Usage:
    from observability.instrument import trace, span, log
    from observability import LogLevel

    async with trace("agent.stream", attributes={...}):
        async with span("middleware"):
            await log(LogLevel.INFO, "Running middlewares")
            ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from observability.logs.model import LogLevel
from observability.tracing.span import SpanKind, SpanStatus
from observability.tracing.trace import TraceStatus


if TYPE_CHECKING:
    from observability.engine import ObservabilityEngine


# ContextVars for implicit context propagation
# NOTE: _engine is a module-level variable (not ContextVar) because:
# - The engine is a singleton initialized once at app startup
# - ContextVars don't propagate from FastAPI lifespan to request handlers
# - Request handlers are sibling contexts, not children of lifespan
_engine: ObservabilityEngine | None = None
_current_trace_id: ContextVar[str | None] = ContextVar("_current_trace_id", default=None)

# Span stack for proper nesting (None by default to avoid mutable default)
_span_stack: ContextVar[list[str] | None] = ContextVar("_span_stack", default=None)


# Engine initialization


def init(engine: ObservabilityEngine) -> None:
    """
    Initialize the instrumentation with an ObservabilityEngine.

    Must be called once at application startup (e.g., in runtime/server.py).

    Args:
        engine: The ObservabilityEngine instance to use
    """
    # instrument._engine = obs_engine
    # instrument module stores it in _engine
    # `global` is required so this assignment modifies the module-level `_engine` variable. Without it, Python would create a new local `_engine` inside this function and the real one would stay None.
    global _engine
    _engine = engine


def get_engine() -> ObservabilityEngine | None:
    """Get the current ObservabilityEngine."""
    return _engine


# Trace/Span context getters


def get_current_trace_id() -> str | None:
    """Get the current trace ID, or None if no trace is active."""
    return _current_trace_id.get()


def get_current_span_id() -> str | None:
    """Get the current span ID (top of stack), or None if no span is active."""
    stack = _span_stack.get()
    return stack[-1] if stack else None


# Async context managers
@asynccontextmanager
async def trace(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> AsyncGenerator[str | None, None]:
    """
    Async context manager for creating a trace.

    Usage:
        async with trace("agent.stream", attributes={"agent_id": "x"}):
            # ... code runs within trace context ...

    Args:
        name: Trace name (e.g., "agent.finance.stream")
        attributes: Optional metadata

    Yields:
        trace_id: The trace ID, or None if engine not initialized
    """
    engine = _engine

    if engine is None:
        # No engine configured, run without tracing
        yield None
        return

    # Create trace
    trace_id = engine.start_trace(name, attributes or {})

    # Set current trace in ContextVar
    token = _current_trace_id.set(trace_id)

    # Initialize span stack for this trace
    stack_token = _span_stack.set([])

    try:
        yield trace_id
        # Success path
        await engine.end_trace(trace_id, TraceStatus.SUCCESS)
    except Exception:
        # Error path
        await engine.end_trace(trace_id, TraceStatus.ERROR)
        raise
    finally:
        # Restore ContextVars
        _current_trace_id.reset(token)
        _span_stack.reset(stack_token)


@asynccontextmanager
async def span(
    name: str,
    kind: SpanKind = SpanKind.STEP,
    attributes: dict[str, Any] | None = None,
) -> AsyncGenerator[str | None, None]:
    """
    Async context manager for creating a span within the current trace.

    Automatically handles:
    - Parent-child relationships via span stack
    - Proper nesting restoration on exit

    Usage:
        async with span("middleware.input", attributes={"count": 2}):
            await log(LogLevel.INFO, "Running middlewares")
            # ... code runs within span context ...

    Args:
        name: Span name (e.g., "middleware.input")
        kind: Span kind (STEP, GENERATION, TOOL, etc.)
        attributes: Optional metadata

    Yields:
        span_id: The span ID, or None if no trace is active
    """
    engine = _engine
    trace_id = _current_trace_id.get()

    if engine is None or trace_id is None:
        # No engine or no active trace, run without spanning
        yield None
        return

    # Get parent span from stack (if any)
    current_stack = _span_stack.get() or []
    parent_span_id = current_stack[-1] if current_stack else None

    # Create span
    span_id = engine.start_span(
        trace_id=trace_id,
        name=name,
        kind=kind,
        parent_span_id=parent_span_id,
        attributes=attributes or {},
    )

    # Push to span stack (create new list to avoid mutation)
    new_stack = current_stack.copy()
    new_stack.append(span_id)
    stack_token = _span_stack.set(new_stack)

    try:
        yield span_id
        # Success path
        await engine.end_span(span_id, SpanStatus.SUCCESS)
    except Exception:
        # Error path
        await engine.end_span(span_id, SpanStatus.ERROR)
        raise
    finally:
        # Restore span stack
        _span_stack.reset(stack_token)


def update_span(attributes: dict[str, Any]) -> None:
    """
    Update attributes of the current span.

    Args:
        attributes: Metadata to add to the current span
    """
    engine = _engine
    span_id = get_current_span_id()

    if engine and span_id:
        engine.update_span(span_id, attributes)


# Logging


async def log(
    level: LogLevel,
    message: str,
    attributes: dict[str, Any] | None = None,
) -> None:
    """
    Log an event to the current span.

    If no span is active, this is a no-op.

    Usage:
        await log(LogLevel.INFO, "Starting middleware")
        await log(LogLevel.DEBUG, "Middleware passed", {"name": "RateLimiter"})

    Args:
        level: Log level (DEBUG, INFO, WARN, ERROR)
        message: Human-readable message
        attributes: Optional structured data
    """
    engine = _engine
    trace_id = _current_trace_id.get()
    span_id = get_current_span_id()

    if engine is None or trace_id is None:
        # No engine or trace, no-op
        return

    from observability.logs.model import Log

    log_entry = Log(
        trace_id=trace_id,
        span_id=span_id,
        level=level,
        message=message,
        attributes=attributes or {},
    )

    await engine.log_event(log_entry)
