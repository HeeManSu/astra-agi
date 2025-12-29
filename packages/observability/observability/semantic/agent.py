from __future__ import annotations

from collections.abc import Callable
import functools
import inspect
from typing import Any, TypeVar

from observability.core.span import end_span, start_span
from observability.semantic.conventions import AstraAttributes, AstraSpanKind


F = TypeVar("F", bound=Callable[..., Any])

def trace_agent(name: str | None = None, agent_type: str | None = None, thread_id: str | None = None, conversation_id: str | None = None) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                attrs: dict[str, Any] = {
                    AstraAttributes.SPAN_KIND: AstraSpanKind.AGENT,
                    AstraAttributes.AGENT_NAME: name or getattr(func, "__name__", "agent"),
                    AstraAttributes.AGENT_TYPE: agent_type or "agent",
                    AstraAttributes.AGENT_THREAD_ID: thread_id,
                    AstraAttributes.AGENT_CONVERSATION_ID: conversation_id,
                }
                span_ctx, span = start_span("agent.run", attrs)
                try:
                    result = await func(*args, **kwargs)
                    end_span(span_ctx, span)
                    return result
                except Exception as e:
                    end_span(span_ctx, span, error=e)
                    raise
            return functools.wraps(func)(async_wrapper)  # type: ignore
        else:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                attrs: dict[str, Any] = {
                    AstraAttributes.SPAN_KIND: AstraSpanKind.AGENT,
                    AstraAttributes.AGENT_NAME: name or getattr(func, "__name__", "agent"),
                    AstraAttributes.AGENT_TYPE: agent_type or "agent",
                    AstraAttributes.AGENT_THREAD_ID: thread_id,
                    AstraAttributes.AGENT_CONVERSATION_ID: conversation_id,
                }
                span_ctx, span = start_span("agent.run", attrs)
                try:
                    result = func(*args, **kwargs)
                    end_span(span_ctx, span)
                    return result
                except Exception as e:
                    end_span(span_ctx, span, error=e)
                    raise
            return functools.wraps(func)(wrapper)  # type: ignore
    return decorator
