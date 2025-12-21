from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple

from observability.instrumentation.common.semconv import GenAIAttributes, LLMAttributes
from observability.instrumentation.common.span_management import truncate_text
from observability.instrumentation.models.llm import LLMRequest, LLMResponse, Message, TokenUsage
from observability.instrumentation.providers.base.adapter import ProviderAdapter
from observability.instrumentation.core.operations import OperationSpec
from observability.instrumentation.providers.google_genai.attributes import _extract_usage_metadata
from observability.pricing.google_gemini import estimate_gemini_usage_cost_breakdown
import uuid
from datetime import datetime


from observability.instrumentation.models.observation import (
    Observation, TraceInfo, LLMInfo, AgentInfo, InputInfo, OutputInfo, 
    UsageInfo, TokenUsage as ObsTokenUsage, LatencyUsage, CostUsage, 
    ToolsInfo, MetricsInfo, ResourceInfo, ServiceInfo, TelemetryInfo,
    Message as ObsMessage
)

class GoogleGenAIAdapter(ProviderAdapter):
    name = "google_genai"

    def calculate_cost(
        self,
        operation: OperationSpec,
        request: Optional[LLMRequest],
        response: Optional[LLMResponse],
    ) -> Dict[str, Any]:
        if operation.kind != "generate":
            return {}
        if response is None or response.usage is None:
            return {}
        model = response.model
        if not model and request is not None:
            model = request.model
        if not model:
            return {}
        
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        
        breakdown = estimate_gemini_usage_cost_breakdown(model, prompt_tokens, completion_tokens)
        if breakdown is None:
            return {}
            
        return {
            "llm.cost.usd": breakdown.total_usd,
            "genai.cost.total_usd": breakdown.total_usd,
            "genai.cost.input_usd": breakdown.input_usd,
            "genai.cost.output_usd": breakdown.output_usd,
        }

    def to_observation(
        self,
        operation: OperationSpec,
        request: LLMRequest,
        response: LLMResponse,
        metadata: Dict[str, Any],
    ) -> Optional[Observation]:
        
        # 1. Trace Info
        # Metadata must contain trace details passed from wrapper
        start_time_ns = metadata.get("start_time_ns", 0)
        end_time_ns = metadata.get("end_time_ns", 0)
        start_time = datetime.fromtimestamp(start_time_ns / 1e9)
        end_time = datetime.fromtimestamp(end_time_ns / 1e9)
        duration_ms = (end_time_ns - start_time_ns) / 1e6
        
        trace_info = TraceInfo(
            trace_id=metadata.get("trace_id", "unknown"),
            span_id=metadata.get("span_id", "unknown"),
            parent_span_id=metadata.get("parent_span_id"),
            name=metadata.get("span_name", "unknown"),
            kind="INTERNAL", # Default for now
            status="success" if metadata.get("success", True) else "error",
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms
        )

        # 2. LLM Info
        llm_info = LLMInfo(
            provider="google_genai",
            system="Gemini",
            model=response.model or request.model or "unknown",
            operation=operation.name,
            streaming=request.streaming
        )

        # 3. Agent Info
        agent_info = AgentInfo(
            run_id=str(uuid.uuid4()), # Unique ID for this run event
            agent_id=metadata.get("agent_id", "unknown"),
            agent_name=metadata.get("agent_name", "unknown"),
            execution_mode=metadata.get("execution_mode", "traditional"),
            status="success" if metadata.get("success", True) else "error"
        )

        # 4. Input Info
        messages = []
        for msg in request.messages:
            messages.append(ObsMessage(role=msg.role, content=msg.content))
        
        # If no messages parsed but we have raw prompt
        if not messages and request.metadata.get("prompt_text"):
             messages.append(ObsMessage(role="user", content=request.metadata["prompt_text"]))

        input_info = InputInfo(
            prompt=request.metadata.get("prompt_text", ""),
            messages=messages
        )

        # 5. Output Info
        output_info = OutputInfo(
            completion_text=response.content or "",
            finish_reason=response.finish_reason
        )

        # 6. Usage Info
        usage = response.usage or TokenUsage()
        input_tokens = usage.prompt_tokens or 0
        output_tokens = usage.completion_tokens or 0
        total_tokens = usage.total_tokens or (input_tokens + output_tokens)
        
        duration_seconds = duration_ms / 1000.0
        tokens_per_second = 0.0
        if duration_seconds > 0 and output_tokens > 0:
            tokens_per_second = output_tokens / duration_seconds

        cost_usd = metadata.get("cost_usd", 0.0)
        input_usd = metadata.get("input_usd", 0.0)
        output_usd = metadata.get("output_usd", 0.0)

        usage_info = UsageInfo(
            tokens=ObsTokenUsage(
                prompt=input_tokens,
                completion=output_tokens,
                total=total_tokens
            ),
            latency=LatencyUsage(
                total_seconds=duration_seconds,
                time_to_first_token_seconds=None, # Not tracked yet
                tokens_per_second=tokens_per_second
            ),
            cost=CostUsage(
                total_usd=cost_usd,
                input_usd=input_usd,
                output_usd=output_usd
            )
        )

        # 7. Tools Info
        tools_info = ToolsInfo(
            tool_calls_count=0,
            tool_calls=[]
        )

        # 8. Metrics Info
        metrics_info = MetricsInfo(
            llm_latency_ms=duration_ms,
            llm_tokens_input=input_tokens,
            llm_tokens_output=output_tokens,
            llm_tokens_total=total_tokens,
            llm_cost_usd=cost_usd,
            llm_throughput_tps=tokens_per_second
        )

        # 9. Resource Info
        # These should ideally come from the Tracer's resource, passed in metadata
        resource_info = ResourceInfo(
            service=ServiceInfo(
                name=metadata.get("service_name", "unknown"),
                namespace=metadata.get("service_namespace", "unknown"),
                version=metadata.get("service_version", "unknown")
            ),
            telemetry=TelemetryInfo(
                sdk_language="python",
                sdk_name="Observability",
                sdk_version="0.1.0"
            )
        )

        # 10. Metadata
        final_metadata = {
            "user_id": metadata.get("user_id", "unknown"),
            "environment": metadata.get("environment", "production"),
            **request.metadata
        }

        return Observation(
            trace=trace_info,
            llm=llm_info,
            agent=agent_info,
            input=input_info,
            output=output_info,
            usage=usage_info,
            tools=tools_info,
            metrics=metrics_info,
            resource=resource_info,
            metadata=final_metadata
        )

    def parse_request(
        self,
        operation: OperationSpec,
        args,
        kwargs,
        truncate_limit: int,
    ) -> LLMRequest:
        model = kwargs.get("model", None)
        if model is None and len(args) > 1:
            model = args[1]
        contents = kwargs.get("contents", None)
        if contents is None and len(args) > 2:
            contents = args[2]
        req_config = kwargs.get("config", None)
        temperature = getattr(req_config, "temperature", None)
        max_tokens = getattr(req_config, "max_output_tokens", None)
        if isinstance(req_config, dict):
            if temperature is None:
                temperature = req_config.get("temperature")
            if max_tokens is None:
                max_tokens = req_config.get("max_output_tokens")
        prompt_text: Optional[str] = None
        try:
            from observability.instrumentation.providers.google_genai.attributes import _extract_prompt_text

            prompt_text = _extract_prompt_text(contents, truncate_limit)
        except Exception:
            prompt_text = None
        messages = []
        if isinstance(prompt_text, str):
            messages.append(Message(role="user", content=prompt_text))
        provider_params = {
            "contents": contents,
            "config": req_config,
        }
        if args and len(args) > 0:
            provider_params["instance"] = args[0]

        request = LLMRequest(
            system="Gemini",
            operation=operation.name,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=operation.streaming,
            provider_params=provider_params,
        )
        if prompt_text is not None:
            request.metadata["prompt_text"] = truncate_text(prompt_text, truncate_limit)
        return request

    def parse_response(
        self,
        operation: OperationSpec,
        response: Any,
        truncate_limit: int,
    ) -> LLMResponse:
        text = getattr(response, "text", None)
        if isinstance(text, str):
            text = truncate_text(text, truncate_limit)
        role = getattr(response, "role", None)
        finish_reason = getattr(response, "finish_reason", None)
        if finish_reason is None:
            candidates = getattr(response, "candidates", None)
            try:
                if candidates is not None:
                    for candidate in candidates:
                        value = getattr(candidate, "finish_reason", None)
                        if isinstance(value, str):
                            finish_reason = value
                            break
            except Exception:
                finish_reason = None
        model_name = getattr(response, "model", None) or getattr(response, "model_version", None)
        usage_dict = _extract_usage_metadata(response)
        usage = self._usage_from_genai_dict(usage_dict)
        return LLMResponse(
            system="Gemini",
            operation=operation.name,
            model=model_name,
            content=text,
            role=role,
            finish_reason=finish_reason,
            usage=usage,
        )

    def build_request_attributes(
        self,
        operation: OperationSpec,
        request: LLMRequest,
    ) -> Dict[str, Any]:
        attrs: Dict[str, Any] = {
            GenAIAttributes.SYSTEM: "google",
            GenAIAttributes.OPERATION: operation.name,
            GenAIAttributes.REQUEST_MODEL: request.model,
            GenAIAttributes.REQUEST_TEMPERATURE: request.temperature,
            GenAIAttributes.REQUEST_MAX_TOKENS: request.max_tokens,
            LLMAttributes.SYSTEM: request.system,
            LLMAttributes.REQUEST_MODEL: request.model,
            LLMAttributes.REQUEST_STREAMING: request.streaming,
            LLMAttributes.REQUEST_TEMPERATURE: request.temperature,
            LLMAttributes.REQUEST_MAX_TOKENS: request.max_tokens,
            LLMAttributes.REQUEST_TOP_P: request.top_p,
            LLMAttributes.REQUEST_TOP_K: request.top_k,
            LLMAttributes.REQUEST_SEED: request.seed,
            LLMAttributes.REQUEST_STOP_SEQUENCES: request.stop_sequences,
        }
        prompt_text = request.metadata.get("prompt_text")
        if isinstance(prompt_text, str):
            attrs[GenAIAttributes.REQUEST_PROMPT] = prompt_text
        for idx, message in enumerate(request.messages):
            key_content = f"{LLMAttributes.PROMPT_CONTENT_PREFIX}{idx}]"
            key_role = f"{LLMAttributes.PROMPT_ROLE_PREFIX}{idx}]"
            attrs[key_content] = message.content
            attrs[key_role] = message.role
        return attrs

    def build_response_attributes(
        self,
        operation: OperationSpec,
        response: LLMResponse,
    ) -> Dict[str, Any]:
        attrs: Dict[str, Any] = {
            GenAIAttributes.RESPONSE_TEXT: response.content,
            LLMAttributes.RESPONSE_MODEL: response.model,
        }
        if response.content is not None:
            attrs[f"{LLMAttributes.COMPLETION_CONTENT_PREFIX}0]"] = response.content
        if response.role is not None:
            attrs[f"{LLMAttributes.COMPLETION_ROLE_PREFIX}0]"] = response.role
        if response.finish_reason is not None:
            attrs[f"{LLMAttributes.COMPLETION_FINISH_REASON_PREFIX}0]"] = response.finish_reason
        return attrs

    def build_usage_attributes(
        self,
        operation: OperationSpec,
        usage: Optional[TokenUsage],
    ) -> Dict[str, Any]:
        if usage is None:
            return {}
        attrs: Dict[str, Any] = {}
        if usage.prompt_tokens is not None:
            attrs[GenAIAttributes.USAGE_INPUT_TOKENS] = usage.prompt_tokens
            attrs[LLMAttributes.USAGE_PROMPT_TOKENS] = usage.prompt_tokens
        if usage.completion_tokens is not None:
            attrs[GenAIAttributes.USAGE_OUTPUT_TOKENS] = usage.completion_tokens
            attrs[LLMAttributes.USAGE_COMPLETION_TOKENS] = usage.completion_tokens
        if usage.total_tokens is not None:
            attrs[GenAIAttributes.USAGE_TOTAL_TOKENS] = usage.total_tokens
            attrs[LLMAttributes.USAGE_TOTAL_TOKENS] = usage.total_tokens
        if usage.cached_tokens is not None:
            attrs[GenAIAttributes.USAGE_CACHED_TOKENS] = usage.cached_tokens
        return attrs

    def init_stream_state(self, operation: OperationSpec, request: LLMRequest) -> Dict[str, Any]:
        return {
            "combined_text": "",
            "usage_acc": {
                GenAIAttributes.USAGE_INPUT_TOKENS: 0,
                GenAIAttributes.USAGE_OUTPUT_TOKENS: 0,
                GenAIAttributes.USAGE_TOTAL_TOKENS: 0,
                GenAIAttributes.USAGE_CACHED_TOKENS: 0,
            },
            "have_usage": False,
        }

    def accumulate_stream_chunk(
        self,
        operation: OperationSpec,
        request: LLMRequest,
        state: Dict[str, Any],
        chunk: Any,
    ) -> None:
        text = getattr(chunk, "text", None)
        if isinstance(text, str):
            state["combined_text"] += text
        usage_dict = _extract_usage_metadata(chunk)
        if usage_dict:
            have_usage = state.get("have_usage", False)
            usage_acc = state.get("usage_acc")
            if isinstance(usage_acc, dict):
                for key, value in usage_dict.items():
                    if not isinstance(value, int):
                        continue
                    if key not in usage_acc:
                        continue
                    usage_acc[key] = value
                    if value:
                        have_usage = True
            state["have_usage"] = have_usage

    def finalize_stream(
        self,
        operation: OperationSpec,
        state: Dict[str, Any],
        truncate_limit: int,
        request: Optional[LLMRequest] = None,
    ) -> Tuple[LLMResponse, Optional[Iterable[Any]]]:
        combined_text = state.get("combined_text") or ""
        usage_acc = state.get("usage_acc") or {}
        have_usage = bool(state.get("have_usage"))
        usage = None
        if have_usage and isinstance(usage_acc, dict):
            usage = self._usage_from_genai_dict(usage_acc)
        content = truncate_text(combined_text, truncate_limit) if combined_text else None
        response = LLMResponse(
            system="Gemini",
            operation=operation.name,
            model=request.model if request is not None else None,
            content=content,
            usage=usage,
        )
        return response, None

    def _usage_from_genai_dict(self, usage: Dict[str, Any]) -> Optional[TokenUsage]:
        prompt = usage.get(GenAIAttributes.USAGE_INPUT_TOKENS)
        completion = usage.get(GenAIAttributes.USAGE_OUTPUT_TOKENS)
        total = usage.get(GenAIAttributes.USAGE_TOTAL_TOKENS)
        cached = usage.get(GenAIAttributes.USAGE_CACHED_TOKENS)
        if not any(isinstance(v, int) for v in (prompt, completion, total, cached)):
            return None
        return TokenUsage(
            prompt_tokens=prompt if isinstance(prompt, int) else None,
            completion_tokens=completion if isinstance(completion, int) else None,
            total_tokens=total if isinstance(total, int) else None,
            cached_tokens=cached if isinstance(cached, int) else None,
        )
