from __future__ import annotations

from collections.abc import Callable
import functools
import inspect
from typing import Any, TypeVar

from observability.core.span import end_span, set_attributes, start_span
from observability.semantic.conventions import AstraAttributes, AstraSpanKind

from .utils import sanitize_args, to_json_str


F = TypeVar("F", bound=Callable[..., Any])

def trace_tool(name: str | None = None) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        tool_name = name or getattr(func, "__name__", "tool")
        if inspect.iscoroutinefunction(func):
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                attrs: dict[str, Any] = {
                    AstraAttributes.SPAN_KIND: AstraSpanKind.TOOL,
                    AstraAttributes.TOOL_NAME: tool_name,
                    AstraAttributes.TOOL_TYPE: "function", # Default type
                }
                span_ctx, span = start_span(f"tool.{tool_name}", attrs)
                try:
                    in_payload = sanitize_args(args, kwargs)
                    set_attributes(span, {AstraAttributes.TOOL_INPUT: to_json_str(in_payload)})
                    result = await func(*args, **kwargs)
                    set_attributes(span, {AstraAttributes.TOOL_OUTPUT: to_json_str(result)})
                    end_span(span_ctx, span)
                    return result
                except Exception as e:
                    set_attributes(span, {AstraAttributes.TOOL_ERROR: to_json_str({"error": str(e)})})
                    end_span(span_ctx, span, error=e)
                    raise
            return functools.wraps(func)(async_wrapper)  # type: ignore
        else:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                attrs: dict[str, Any] = {
                    AstraAttributes.SPAN_KIND: AstraSpanKind.TOOL,
                    AstraAttributes.TOOL_NAME: tool_name,
                    AstraAttributes.TOOL_TYPE: "function", # Default type
                }
                span_ctx, span = start_span(f"tool.{tool_name}", attrs)
                try:
                    in_payload = sanitize_args(args, kwargs)
                    set_attributes(span, {AstraAttributes.TOOL_INPUT: to_json_str(in_payload)})
                    result = func(*args, **kwargs)
                    set_attributes(span, {AstraAttributes.TOOL_OUTPUT: to_json_str(result)})
                    end_span(span_ctx, span)
                    return result
                except Exception as e:
                    set_attributes(span, {AstraAttributes.TOOL_ERROR: to_json_str({"error": str(e)})})
                    end_span(span_ctx, span, error=e)
                    raise
            return functools.wraps(func)(wrapper)  # type: ignore
    return decorator
