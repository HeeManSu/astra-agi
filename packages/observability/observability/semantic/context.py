from __future__ import annotations

from collections.abc import Callable
import functools
import inspect
from typing import Any, TypeVar

from opentelemetry import trace


F = TypeVar("F", bound=Callable[..., Any])

def with_context(attributes: dict[str, Any] = None, **kwargs: Any) -> Callable[[F], F] | Any:
    """
    Decorator and context manager to add context attributes to the current span.
    
    Usage:
        @with_context(user_id="123")
        def my_func():
            ...
            
        with with_context(user_id="123"):
            ...
    """
    if attributes is None:
        attributes = {}
    attributes.update(kwargs)

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                span = trace.get_current_span()
                if span.is_recording():
                    for k, v in attributes.items():
                        span.set_attribute(k, v)
                return await func(*args, **kwargs)
            return functools.wraps(func)(async_wrapper)
        else:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                span = trace.get_current_span()
                if span.is_recording():
                    for k, v in attributes.items():
                        span.set_attribute(k, v)
                return func(*args, **kwargs)
            return functools.wraps(func)(wrapper)

    # Support use as context manager
    class ContextManager:
        def __enter__(self):
            span = trace.get_current_span()
            if span.is_recording():
                for k, v in attributes.items():
                    span.set_attribute(k, v)
            return span

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def __call__(self, func: F) -> F:
            return decorator(func)

    return ContextManager()
