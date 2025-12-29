from __future__ import annotations

from collections.abc import Callable
import logging
import time
from typing import Any, TypeVar

from observability.core.span import end_span, set_attributes, start_span
from observability.instrumentation.common.metrics import get_meter
from observability.instrumentation.core.base_instrumentor import InstrumentorConfig
from observability.instrumentation.core.operations import OperationSpec
from observability.instrumentation.models.llm import LLMRequest, LLMResponse, TokenUsage
from observability.instrumentation.providers.base.adapter import ProviderAdapter
from opentelemetry import baggage
from opentelemetry.metrics import Counter, Histogram
from opentelemetry.trace import StatusCode


logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

_meter = get_meter()
_request_counter: Counter | None = None
_error_counter: Counter | None = None
_duration_histogram: Histogram | None = None
_tokens_histogram: Histogram | None = None

if _meter is not None:
    try:
        _request_counter = _meter.create_counter(
            "observability.llm.requests",
            unit="1",
        )
        _error_counter = _meter.create_counter(
            "observability.llm.errors",
            unit="1",
        )
        _duration_histogram = _meter.create_histogram(
            "observability.llm.duration_ms",
            unit="ms",
        )
        _tokens_histogram = _meter.create_histogram(
            "observability.llm.tokens",
            unit="1",
        )
    except Exception:
        _request_counter = None
        _error_counter = None
        _duration_histogram = None
        _tokens_histogram = None


def _record_metrics(
    operation: OperationSpec,
    start_ns: int,
    success: bool,
    usage: TokenUsage | None,
) -> None:
    if _request_counter is not None:
        _request_counter.add(1, {"operation": operation.name})
    if not success and _error_counter is not None:
        _error_counter.add(1, {"operation": operation.name})
    if _duration_histogram is not None:
        duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        _duration_histogram.record(duration_ms, {"operation": operation.name})
    if usage is not None and _tokens_histogram is not None:
        total = usage.total_tokens or 0
        if total:
            _tokens_histogram.record(total, {"operation": operation.name})



def _record_agent_run(
    span: Any,
    adapter: ProviderAdapter,
    operation: OperationSpec,
    request: LLMRequest | None,
    response: LLMResponse | None,
    cost_attrs: dict[str, Any],
    start_ns: int,
    success: bool = True,
) -> None:
    if request is None:
        return
    try:
        has_observation = hasattr(adapter, "to_observation")
        if not has_observation:
            return
        end_ns = time.perf_counter_ns()
        duration_s = (end_ns - start_ns) / 1e9
        trace_id = format(span.get_span_context().trace_id, "032x")
        span_id = format(span.get_span_context().span_id, "016x")
        agent_id = "unknown"
        agent_name = "unknown"
        execution_mode = "traditional"
        if hasattr(span, "attributes") and span.attributes:
            agent_id = span.attributes.get("agent.id", "unknown")
            agent_name = span.attributes.get("agent.name", "unknown")
            execution_mode = span.attributes.get("agent.execution_mode", "traditional")
        if agent_id == "unknown":
            agent_id = baggage.get_baggage("agent.id") or "unknown"
        if agent_name == "unknown":
            agent_name = baggage.get_baggage("agent.name") or "unknown"
        if execution_mode == "traditional":
             execution_mode = baggage.get_baggage("agent.execution_mode") or "traditional"
        metadata = {
            "duration_seconds": duration_s,
            "start_time_ns": int(time.time() * 1e9) - (end_ns - start_ns), # Approx start time
            "end_time_ns": int(time.time() * 1e9), # Approx end time
            "cost_usd": cost_attrs.get("llm.cost.usd", 0.0),
            "input_usd": cost_attrs.get("genai.cost.input_usd", 0.0),
            "output_usd": cost_attrs.get("genai.cost.output_usd", 0.0),
            "success": success,
            "trace_id": trace_id,
            "span_id": span_id,
            "span_name": span.name,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "execution_mode": execution_mode,
            "service_name": span.resource.attributes.get("service.name", "unknown") if hasattr(span, "resource") else "unknown",
            "service_namespace": span.resource.attributes.get("service.namespace", "unknown") if hasattr(span, "resource") else "unknown",
            "service_version": span.resource.attributes.get("service.version", "unknown") if hasattr(span, "resource") else "unknown",
        }
        if has_observation:
            obs_response = response or LLMResponse()
            observation = adapter.to_observation(operation, request, obs_response, metadata)
            if observation:
                span.set_attribute("astra.agent_run", observation.model_dump_json())
                return
    except Exception as e:
        logger.warning("Failed to record agent run/observation: %s", e)


def create_sync_wrapper(
    adapter: ProviderAdapter,
    operation: OperationSpec,
    config: InstrumentorConfig,
) -> Callable[[F], F]:
    def _factory(func: F) -> F:
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            if not config.instrument_llm_calls:
                return func(*args, **kwargs)
            truncate_limit = int(config.privacy_truncate_chars)
            start_ns = time.perf_counter_ns()
            request: LLMRequest | None = None
            response_model: LLMResponse | None = None
            success = False
            try:
                request = adapter.parse_request(operation, args, kwargs, truncate_limit)
                request_attrs = adapter.build_request_attributes(operation, request)
                span_ctx, span = start_span(operation.span_name, request_attrs)
                try:
                    result = func(*args, **kwargs)
                    response_model = adapter.parse_response(operation, result, truncate_limit)
                    response_attrs = adapter.build_response_attributes(operation, response_model)
                    usage_attrs = adapter.build_usage_attributes(operation, response_model.usage)
                    cost_attrs = adapter.calculate_cost(operation, request, response_model)
                    set_attributes(span, response_attrs)
                    set_attributes(span, usage_attrs)
                    if cost_attrs:
                        set_attributes(span, cost_attrs)
                    _record_agent_run(span, adapter, operation, request, response_model, cost_attrs, start_ns, True)
                    end_span(span_ctx, span, status_code=StatusCode.OK)
                    success = True
                    return result
                except Exception as e:
                    cost_attrs = {}
                    _record_agent_run(span, adapter, operation, request, response_model, cost_attrs, start_ns, False)
                    end_span(span_ctx, span, status_code=StatusCode.ERROR, error=e)
                    raise
            except Exception as e:
                if config.fail_safe:
                    logger.exception("LLM sync wrapper failed for %s: %s", operation.name, e)
                    return func(*args, **kwargs)
                raise
            finally:
                _record_metrics(
                    operation=operation,
                    start_ns=start_ns,
                    success=success,
                    usage=response_model.usage if response_model is not None else None,
                )

        return _wrapper  # type: ignore[return-value]

    return _factory


def create_async_wrapper(
    adapter: ProviderAdapter,
    operation: OperationSpec,
    config: InstrumentorConfig,
) -> Callable[[F], F]:
    def _factory(func: F) -> F:
        async def _wrapper(*args: Any, **kwargs: Any) -> Any:
            if not config.instrument_llm_calls:
                return await func(*args, **kwargs)
            truncate_limit = int(config.privacy_truncate_chars)
            start_ns = time.perf_counter_ns()
            request: LLMRequest | None = None
            response_model: LLMResponse | None = None
            success = False
            try:
                request = adapter.parse_request(operation, args, kwargs, truncate_limit)
                request_attrs = adapter.build_request_attributes(operation, request)
                span_ctx, span = start_span(operation.span_name, request_attrs)
                try:
                    result = await func(*args, **kwargs)
                    response_model = adapter.parse_response(operation, result, truncate_limit)
                    response_attrs = adapter.build_response_attributes(operation, response_model)
                    usage_attrs = adapter.build_usage_attributes(operation, response_model.usage)
                    cost_attrs = adapter.calculate_cost(operation, request, response_model)
                    set_attributes(span, response_attrs)
                    set_attributes(span, usage_attrs)
                    if cost_attrs:
                        set_attributes(span, cost_attrs)
                    _record_agent_run(span, adapter, operation, request, response_model, cost_attrs, start_ns, True)
                    end_span(span_ctx, span, status_code=StatusCode.OK)
                    success = True
                    return result
                except Exception as e:
                    cost_attrs = {}
                    _record_agent_run(span, adapter, operation, request, response_model, cost_attrs, start_ns, False)
                    end_span(span_ctx, span, status_code=StatusCode.ERROR, error=e)
                    raise
            except Exception as e:
                if config.fail_safe:
                    logger.exception("LLM async wrapper failed for %s: %s", operation.name, e)
                    return await func(*args, **kwargs)
                raise
            finally:
                _record_metrics(
                    operation=operation,
                    start_ns=start_ns,
                    success=success,
                    usage=response_model.usage if response_model is not None else None,
                )

        return _wrapper  # type: ignore[return-value]

    return _factory


def create_streaming_wrapper(
    adapter: ProviderAdapter,
    operation: OperationSpec,
    config: InstrumentorConfig,
) -> Callable[[F], F]:
    def _factory(func: F) -> F:
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            if not config.instrument_llm_calls:
                return func(*args, **kwargs)
            truncate_limit = int(config.privacy_truncate_chars)
            start_ns = time.perf_counter_ns()

            request: LLMRequest | None = None
            try:
                request = adapter.parse_request(operation, args, kwargs, truncate_limit)
                request_attrs = adapter.build_request_attributes(operation, request)
                span_ctx, span = start_span(operation.span_name, request_attrs)

                def on_stream_finish(response_model: LLMResponse) -> None:
                    try:
                        response_attrs = adapter.build_response_attributes(operation, response_model)
                        usage_attrs = adapter.build_usage_attributes(operation, response_model.usage)
                        cost_attrs = adapter.calculate_cost(operation, request, response_model)
                        set_attributes(span, response_attrs)
                        set_attributes(span, usage_attrs)
                        if cost_attrs:
                            set_attributes(span, cost_attrs)
                        _record_agent_run(span, adapter, operation, request, response_model, cost_attrs, start_ns, True)
                        end_span(span_ctx, span, status_code=StatusCode.OK)

                        _record_metrics(
                            operation=operation,
                            start_ns=start_ns,
                            success=True,
                            usage=response_model.usage,
                        )
                    except Exception as e:
                        logger.warning("Error in stream finish callback: %s", e)
                        # We don't re-raise here as it would break the user's stream consumption
                        # But we should ensure the span is ended if it wasn't already?
                        # end_span checks if span is ended usually? No, but span.end() is idempotent.

                try:
                    result = func(*args, **kwargs)
                    return adapter.instrument_stream(
                        operation, request, result, on_stream_finish, truncate_limit
                    )
                except Exception as e:
                    _record_agent_run(span, adapter, operation, request, None, {}, start_ns, False)
                    end_span(span_ctx, span, status_code=StatusCode.ERROR, error=e)
                    _record_metrics(
                        operation=operation,
                        start_ns=start_ns,
                        success=False,
                        usage=None,
                    )
                    raise
            except Exception as e:
                if config.fail_safe:
                    logger.exception("LLM streaming wrapper failed for %s: %s", operation.name, e)
                    return func(*args, **kwargs)
                else:
                    raise

        return _wrapper  # type: ignore[return-value]

    return _factory


def create_async_streaming_wrapper(
    adapter: ProviderAdapter,
    operation: OperationSpec,
    config: InstrumentorConfig,
) -> Callable[[F], F]:
    def _factory(func: F) -> F:
        async def _wrapper(*args: Any, **kwargs: Any) -> Any:
            if not config.instrument_llm_calls:
                return await func(*args, **kwargs)
            truncate_limit = int(config.privacy_truncate_chars)
            start_ns = time.perf_counter_ns()

            request: LLMRequest | None = None
            try:
                request = adapter.parse_request(operation, args, kwargs, truncate_limit)
                request_attrs = adapter.build_request_attributes(operation, request)
                span_ctx, span = start_span(operation.span_name, request_attrs)

                def on_stream_finish(response_model: LLMResponse) -> None:
                    try:
                        response_attrs = adapter.build_response_attributes(operation, response_model)
                        usage_attrs = adapter.build_usage_attributes(operation, response_model.usage)
                        cost_attrs = adapter.calculate_cost(operation, request, response_model)
                        set_attributes(span, response_attrs)
                        set_attributes(span, usage_attrs)
                        if cost_attrs:
                            set_attributes(span, cost_attrs)
                        _record_agent_run(span, adapter, operation, request, response_model, cost_attrs, start_ns, True)
                        end_span(span_ctx, span, status_code=StatusCode.OK)

                        _record_metrics(
                            operation=operation,
                            start_ns=start_ns,
                            success=True,
                            usage=response_model.usage,
                        )
                    except Exception as e:
                        logger.warning("Error in async stream finish callback: %s", e)

                try:
                    result = await func(*args, **kwargs)
                    return adapter.instrument_async_stream(
                        operation, request, result, on_stream_finish, truncate_limit
                    )
                except Exception as e:
                    _record_agent_run(span, adapter, operation, request, None, {}, start_ns, False)
                    end_span(span_ctx, span, status_code=StatusCode.ERROR, error=e)
                    _record_metrics(
                        operation=operation,
                        start_ns=start_ns,
                        success=False,
                        usage=None,
                    )
                    raise
            except Exception as e:
                if config.fail_safe:
                    logger.exception("LLM async streaming wrapper failed for %s: %s", operation.name, e)
                    return await func(*args, **kwargs)
                else:
                    raise

        return _wrapper  # type: ignore[return-value]

    return _factory
