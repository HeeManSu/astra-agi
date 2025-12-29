from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import uuid
import io

from observability.instrumentation.providers.base.adapter import ProviderAdapter
from observability.instrumentation.core.operations import OperationSpec
from observability.instrumentation.models.llm import (
    LLMRequest, LLMResponse, 
    Message as LLMMessage, 
    TokenUsage as LLMTokenUsage
)
from observability.instrumentation.models.observation import (
    Observation, TraceInfo, LLMInfo, AgentInfo, InputInfo, OutputInfo, 
    UsageInfo, TokenUsage as ObsTokenUsage, LatencyUsage, CostUsage, 
    ToolsInfo, MetricsInfo, ResourceInfo, ServiceInfo, TelemetryInfo,
    Message as ObsMessage
)

logger = logging.getLogger(__name__)

class BedrockAdapter(ProviderAdapter):
    name = "bedrock"

    def parse_request(
        self,
        operation: OperationSpec,
        args: tuple[Any, ...],
        kwargs: Dict[str, Any],
        truncate_limit: int,
    ) -> LLMRequest:
        # args[0] is self (client instance), args[1] is operation_name, args[2] is api_params
        api_params = args[2] if len(args) > 2 else kwargs
        
        model_id = api_params.get("modelId")
        body = api_params.get("body")

        if isinstance(body, (bytes, bytearray)):
            try:
                body_json = json.loads(body)
            except json.JSONDecodeError:
                body_json = {}
        elif isinstance(body, str):
            try:
                body_json = json.loads(body)
            except json.JSONDecodeError:
                body_json = {}
        else:
            # Maybe file-like object, hard to read without consuming?
            # For now assume bytes or string as that's what json.dumps produces
            body_json = {}

        messages: List[LLMMessage] = []
        
        # Anthropic Claude 3 (Messages API)
        if model_id and ("anthropic.claude-3" in model_id or "messages" in body_json):
            msgs = body_json.get("messages", [])
            system = body_json.get("system")
            if system:
                if isinstance(system, list): # Nova style: [{"text": "..."}]
                     system_text = ""
                     for s in system:
                         if isinstance(s, dict) and "text" in s:
                             system_text += s["text"]
                     if system_text:
                         messages.append(LLMMessage(role="system", content=system_text))
                else: # Claude 3 style: "system prompt"
                     messages.append(LLMMessage(role="system", content=str(system)))
            
            for m in msgs:
                role = m.get("role", "user")
                content = m.get("content", "")
                # Content can be list of blocks
                if isinstance(content, list):
                    text_content = ""
                    for block in content:
                        if block.get("type") == "text":
                            text_content += block.get("text", "")
                    content = text_content
                messages.append(LLMMessage(role=role, content=str(content)))
        
        # Legacy Anthropic / Titan / etc (Prompt API)
        elif "prompt" in body_json:
            messages.append(LLMMessage(role="user", content=str(body_json.get("prompt"))))
        elif "inputText" in body_json:
             messages.append(LLMMessage(role="user", content=str(body_json.get("inputText"))))

        return LLMRequest(
            model=model_id,
            messages=messages,
            streaming=operation.streaming,
            metadata=body_json # Store full body for debugging if needed
        )

    def parse_response(
        self,
        operation: OperationSpec,
        result: Any,
        truncate_limit: int,
    ) -> LLMResponse:
        # result is the dict returned by _make_api_call
        # We rely on the instrumentor to have attached parsed body to result
        
        response_body = result.get("_astra_response_body")
        if not response_body:
             return LLMResponse(model="unknown")

        content = ""
        role = "assistant"
        input_tokens = 0
        output_tokens = 0
        
        # Amazon Nova
        if "output" in response_body and "message" in response_body["output"]:
            message = response_body["output"]["message"]
            role = message.get("role", "assistant")
            content_blocks = message.get("content", [])
            for block in content_blocks:
                if "text" in block:
                    content += block["text"]
            
            usage = response_body.get("usage", {})
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)

        # Anthropic Claude 3
        elif "content" in response_body:
            # list of blocks
            blocks = response_body.get("content", [])
            for block in blocks:
                if block.get("type") == "text":
                    content += block.get("text", "")
            
            usage = response_body.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

        # Legacy Anthropic
        elif "completion" in response_body:
            content = response_body.get("completion", "")
        
        # Titan
        elif "results" in response_body:
             results = response_body.get("results", [])
             if results:
                 content = results[0].get("outputText", "")
                 input_tokens = results[0].get("tokenCount", 0) # Titan returns input token count sometimes?
        
        return LLMResponse(
            model="unknown", # Model is in request
            content=content,
            role=role,
            usage=LLMTokenUsage(
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens
            )
        )

    def build_request_attributes(
        self,
        operation: OperationSpec,
        request: LLMRequest,
    ) -> Dict[str, Any]:
        from observability.semantic.conventions import GenAIAttributes, LLMAttributes
        
        attrs = {
            GenAIAttributes.SYSTEM: "bedrock",
            GenAIAttributes.OPERATION: operation.kind,
            GenAIAttributes.REQUEST_MODEL: request.model or "unknown",
            LLMAttributes.SYSTEM: "bedrock",
            LLMAttributes.REQUEST_MODEL: request.model or "unknown",
            LLMAttributes.REQUEST_STREAMING: request.streaming,
        }
        
        if request.metadata:
            # Check for top-level keys (Legacy/Claude)
            if "temperature" in request.metadata:
                attrs[LLMAttributes.REQUEST_TEMPERATURE] = request.metadata["temperature"]
            if "max_tokens" in request.metadata:
                attrs[LLMAttributes.REQUEST_MAX_TOKENS] = request.metadata["max_tokens"]
            if "top_p" in request.metadata:
                attrs[LLMAttributes.REQUEST_TOP_P] = request.metadata["top_p"]

            # Check for inferenceConfig (Nova)
            inference_config = request.metadata.get("inferenceConfig")
            if inference_config:
                if "temperature" in inference_config:
                    attrs[LLMAttributes.REQUEST_TEMPERATURE] = inference_config["temperature"]
                if "maxTokens" in inference_config:
                    attrs[LLMAttributes.REQUEST_MAX_TOKENS] = inference_config["maxTokens"]
                if "topP" in inference_config:
                    attrs[LLMAttributes.REQUEST_TOP_P] = inference_config["topP"]
        
        return attrs

    def build_response_attributes(
        self,
        operation: OperationSpec,
        response: LLMResponse,
    ) -> Dict[str, Any]:
        from observability.semantic.conventions import GenAIAttributes, LLMAttributes
        
        attrs = {
            LLMAttributes.RESPONSE_MODEL: response.model or "unknown",
        }
        if response.finish_reason:
            attrs[f"{LLMAttributes.COMPLETION_FINISH_REASON_PREFIX}0]"] = response.finish_reason
            
        return attrs

    def build_usage_attributes(
        self,
        operation: OperationSpec,
        usage: Optional[LLMTokenUsage],
    ) -> Dict[str, Any]:
        from observability.semantic.conventions import GenAIAttributes, LLMAttributes
        
        if not usage:
            return {}
            
        return {
            GenAIAttributes.USAGE_INPUT_TOKENS: usage.prompt_tokens,
            GenAIAttributes.USAGE_OUTPUT_TOKENS: usage.completion_tokens,
            GenAIAttributes.USAGE_TOTAL_TOKENS: usage.total_tokens,
            LLMAttributes.USAGE_PROMPT_TOKENS: usage.prompt_tokens,
            LLMAttributes.USAGE_COMPLETION_TOKENS: usage.completion_tokens,
            LLMAttributes.USAGE_TOTAL_TOKENS: usage.total_tokens,
        }

    def calculate_cost(
        self,
        operation: OperationSpec,
        request: Optional[LLMRequest],
        response: Optional[LLMResponse],
    ) -> Dict[str, Any]:
        # Implement cost calculation based on model and usage
        # For now return empty
        return {}

    def to_observation(
        self,
        operation: OperationSpec,
        request: LLMRequest,
        response: LLMResponse,
        metadata: Dict[str, Any],
    ) -> Optional[Observation]:
        
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
            kind="INTERNAL",
            status="success" if metadata.get("success", True) else "error",
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms
        )

        llm_info = LLMInfo(
            provider="bedrock",
            system="Bedrock",
            model=request.model or "unknown",
            operation=operation.name,
            streaming=request.streaming
        )
        
        agent_info = AgentInfo(
            run_id=str(uuid.uuid4()),
            agent_id=metadata.get("agent_id", "unknown"),
            agent_name=metadata.get("agent_name", "unknown"),
            execution_mode=metadata.get("execution_mode", "traditional"),
            status="success" if metadata.get("success", True) else "error"
        )
        
        # Input Info
        obs_messages = []
        for msg in request.messages:
            obs_messages.append(ObsMessage(role=msg.role, content=msg.content))
        
        input_info = InputInfo(
            prompt="", # We use messages
            messages=obs_messages
        )
        
        # Output Info
        output_info = OutputInfo(
            completion_text=response.content or "",
            finish_reason=response.finish_reason
        )

        # Usage Info
        usage = response.usage or LLMTokenUsage()
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
                time_to_first_token_seconds=None,
                tokens_per_second=tokens_per_second
            ),
            cost=CostUsage(
                total_usd=cost_usd,
                input_usd=input_usd,
                output_usd=output_usd
            )
        )
        
        # Tools Info (placeholder)
        tools_info = ToolsInfo(
            tool_calls_count=0,
            tool_calls=[]
        )
        
        # Metrics Info
        metrics_info = MetricsInfo(
            llm_latency_ms=duration_ms,
            llm_tokens_input=input_tokens,
            llm_tokens_output=output_tokens,
            llm_tokens_total=total_tokens,
            llm_cost_usd=cost_usd,
            llm_throughput_tps=tokens_per_second
        )
        
        # Resource Info
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

        return Observation(
            observation_id=str(uuid.uuid4()),
            trace=trace_info,
            llm=llm_info,
            agent=agent_info,
            input=input_info,
            output=output_info,
            usage=usage_info,
            tools=tools_info,
            metrics=metrics_info,
            resource=resource_info,
        )
