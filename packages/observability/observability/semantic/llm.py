from __future__ import annotations

from collections.abc import Callable
import functools
import inspect
from typing import Any, TypeVar

from observability.core.span import end_span, set_attributes, start_span, truncate_text
from observability.semantic.conventions import AstraAttributes, AstraSpanKind, LLMAttributes


F = TypeVar("F", bound=Callable[..., Any])

def trace_llm_call(model: str | None = None, temperature: float | None = None, max_tokens: int | None = None, prompt_extractor: Callable[..., str] | None = None, response_extractor: Callable[[Any], str] | None = None) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        span_name = "llm.call"
        if inspect.iscoroutinefunction(func):
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                attrs: dict[str, Any] = {
                    AstraAttributes.SPAN_KIND: AstraSpanKind.LLM,
                    LLMAttributes.REQUEST_MODEL: model,
                    LLMAttributes.REQUEST_TEMPERATURE: temperature,
                    LLMAttributes.REQUEST_MAX_TOKENS: max_tokens,
                }
                try:
                    if prompt_extractor is not None:
                        prompt = prompt_extractor(*args, **kwargs)
                        attrs[LLMAttributes.REQUEST_PROMPT] = truncate_text(prompt, 4096)
                except Exception:
                    pass
                span_ctx, span = start_span(span_name, attrs)
                try:
                    result = await func(*args, **kwargs)
                    try:
                        if response_extractor is not None:
                            resp_text = response_extractor(result)
                            set_attributes(span, {LLMAttributes.RESPONSE_TEXT: truncate_text(resp_text, 4096)})
                    except Exception:
                        pass
                    end_span(span_ctx, span)
                    return result
                except Exception as e:
                    end_span(span_ctx, span, error=e)
                    raise
            return functools.wraps(func)(async_wrapper)  # type: ignore
        else:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                attrs: dict[str, Any] = {
                    AstraAttributes.SPAN_KIND: AstraSpanKind.LLM,
                    LLMAttributes.REQUEST_MODEL: model,
                    LLMAttributes.REQUEST_TEMPERATURE: temperature,
                    LLMAttributes.REQUEST_MAX_TOKENS: max_tokens,
                }
                try:
                    if prompt_extractor is not None:
                        prompt = prompt_extractor(*args, **kwargs)
                        attrs[LLMAttributes.REQUEST_PROMPT] = truncate_text(prompt, 4096)
                except Exception:
                    pass
                span_ctx, span = start_span(span_name, attrs)
                try:
                    result = func(*args, **kwargs)
                    try:
                        if response_extractor is not None:
                            resp_text = response_extractor(result)
                            set_attributes(span, {LLMAttributes.RESPONSE_TEXT: truncate_text(resp_text, 4096)})
                    except Exception:
                        pass
                    end_span(span_ctx, span)
                    return result
                except Exception as e:
                    end_span(span_ctx, span, error=e)
                    raise
            return functools.wraps(func)(wrapper)  # type: ignore
    return decorator

trace_llm = trace_llm_call
