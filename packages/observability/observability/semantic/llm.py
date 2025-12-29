from __future__ import annotations
import inspect
import functools
from typing import Any, Callable, Optional, TypeVar, Dict
from observability.semantic.conventions import LLMAttributes, GenAIAttributes, AstraAttributes, AstraSpanKind
from observability.core.span import start_span, end_span, set_attributes, truncate_text
from .utils import to_json_str

F = TypeVar("F", bound=Callable[..., Any])

def trace_llm_call(model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, prompt_extractor: Optional[Callable[..., str]] = None, response_extractor: Optional[Callable[[Any], str]] = None) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        span_name = "llm.call"
        if inspect.iscoroutinefunction(func):
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                attrs: Dict[str, Any] = {
                    AstraAttributes.SPAN_KIND: AstraSpanKind.LLM,
                    LLMAttributes.REQUEST_MODEL: model,
                    LLMAttributes.REQUEST_TEMPERATURE: temperature,
                    LLMAttributes.REQUEST_MAX_TOKENS: max_tokens,
                }
                try:
                    if prompt_extractor is not None:
                        prompt = prompt_extractor(*args, **kwargs)
                        attrs[GenAIAttributes.REQUEST_PROMPT] = truncate_text(prompt, 4096)
                except Exception:
                    pass
                span_ctx, span = start_span(span_name, attrs)
                try:
                    result = await func(*args, **kwargs)
                    try:
                        if response_extractor is not None:
                            resp_text = response_extractor(result)
                            set_attributes(span, {GenAIAttributes.RESPONSE_TEXT: truncate_text(resp_text, 4096)})
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
                attrs: Dict[str, Any] = {
                    AstraAttributes.SPAN_KIND: AstraSpanKind.LLM,
                    LLMAttributes.REQUEST_MODEL: model,
                    LLMAttributes.REQUEST_TEMPERATURE: temperature,
                    LLMAttributes.REQUEST_MAX_TOKENS: max_tokens,
                }
                try:
                    if prompt_extractor is not None:
                        prompt = prompt_extractor(*args, **kwargs)
                        attrs[GenAIAttributes.REQUEST_PROMPT] = truncate_text(prompt, 4096)
                except Exception:
                    pass
                span_ctx, span = start_span(span_name, attrs)
                try:
                    result = func(*args, **kwargs)
                    try:
                        if response_extractor is not None:
                            resp_text = response_extractor(result)
                            set_attributes(span, {GenAIAttributes.RESPONSE_TEXT: truncate_text(resp_text, 4096)})
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
