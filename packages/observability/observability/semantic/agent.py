from __future__ import annotations
import functools
import inspect
from typing import Any, Callable, Dict, Optional, TypeVar
from observability.core.span import start_span, end_span, set_attributes

from observability.semantic.conventions import AstraAttributes, AstraSpanKind

F = TypeVar("F", bound=Callable[..., Any])

def trace_agent(name: Optional[str] = None, agent_type: Optional[str] = None, thread_id: Optional[str] = None, conversation_id: Optional[str] = None) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                attrs: Dict[str, Any] = {
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
                attrs: Dict[str, Any] = {
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
