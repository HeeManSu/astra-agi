from __future__ import annotations

from collections.abc import Callable
import functools
import inspect
from typing import Any, TypeVar

from observability.core.span import end_span, start_span
from observability.semantic.conventions import AstraAttributes, AstraSpanKind


F = TypeVar("F", bound=Callable[..., Any])

def trace_step(step_name: str, step_type: str = "reasoning", step_purpose: str | None = None) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        span_label = f"agent.step.{step_name}"
        if inspect.iscoroutinefunction(func):
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                attrs = {
                   AstraAttributes.SPAN_KIND: AstraSpanKind.STEP,
                   AstraAttributes.STEP_NAME: step_name,
                   AstraAttributes.STEP_TYPE: step_type,
                   AstraAttributes.STEP_PURPOSE: step_purpose
                }
                span_ctx, span = start_span(span_label, attrs)
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
                attrs = {
                   AstraAttributes.SPAN_KIND: AstraSpanKind.STEP,
                   AstraAttributes.STEP_NAME: step_name,
                   AstraAttributes.STEP_TYPE: step_type,
                   AstraAttributes.STEP_PURPOSE: step_purpose
                }
                span_ctx, span = start_span(span_label, attrs)
                try:
                    result = func(*args, **kwargs)
                    end_span(span_ctx, span)
                    return result
                except Exception as e:
                    end_span(span_ctx, span, error=e)
                    raise
            return functools.wraps(func)(wrapper)  # type: ignore
    return decorator
