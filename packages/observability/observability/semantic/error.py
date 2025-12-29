from __future__ import annotations
import inspect
import functools
import traceback
from typing import Any, Callable, Dict, TypeVar
from opentelemetry import trace
from observability.core.span import start_span, end_span, set_attributes

F = TypeVar("F", bound=Callable[..., Any])

def trace_error() -> Callable[[F], F]:
    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    span = trace.get_current_span()
                    try:
                        st = traceback.format_exc()
                        set_attributes(span, {
                            "error.type": e.__class__.__name__,
                            "error.message": str(e),
                            "error.stacktrace": st,
                        })
                        span.record_exception(e)
                    except Exception:
                        pass
                    raise
            return functools.wraps(func)(async_wrapper)  # type: ignore
        else:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    span = trace.get_current_span()
                    try:
                        st = traceback.format_exc()
                        set_attributes(span, {
                            "error.type": e.__class__.__name__,
                            "error.message": str(e),
                            "error.stacktrace": st,
                        })
                        span.record_exception(e)
                    except Exception:
                        pass
                    raise
            return functools.wraps(func)(wrapper)  # type: ignore
    return decorator
