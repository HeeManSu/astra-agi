from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, Field


# --- Nested Models ---

class TraceInfo(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    name: str
    kind: str
    status: str
    start_time: datetime
    end_time: datetime
    duration_ms: float

class LLMInfo(BaseModel):
    provider: str
    system: str
    model: str
    operation: str
    streaming: bool

class AgentInfo(BaseModel):
    run_id: str
    agent_id: str
    agent_name: str
    execution_mode: str
    status: str

class Message(BaseModel):
    role: str
    content: str

class InputInfo(BaseModel):
    prompt: str
    messages: list[Message]

class OutputInfo(BaseModel):
    completion_text: str
    finish_reason: str | None = None

class TokenUsage(BaseModel):
    prompt: int
    completion: int
    total: int

class LatencyUsage(BaseModel):
    total_seconds: float
    time_to_first_token_seconds: float | None = None
    tokens_per_second: float

class CostUsage(BaseModel):
    total_usd: float
    input_usd: float
    output_usd: float

class UsageInfo(BaseModel):
    tokens: TokenUsage
    latency: LatencyUsage
    cost: CostUsage

class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] | None = None

class ToolsInfo(BaseModel):
    tool_calls_count: int
    tool_calls: list[ToolCall]

class MetricsInfo(BaseModel):
    llm_latency_ms: float
    llm_tokens_input: int
    llm_tokens_output: int
    llm_tokens_total: int
    llm_cost_usd: float
    llm_throughput_tps: float

class ServiceInfo(BaseModel):
    name: str
    namespace: str
    version: str

class TelemetryInfo(BaseModel):
    sdk_language: str
    sdk_name: str
    sdk_version: str

class ResourceInfo(BaseModel):
    service: ServiceInfo
    telemetry: TelemetryInfo

# --- Root Model ---

class Observation(BaseModel):
    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace: TraceInfo
    llm: LLMInfo
    agent: AgentInfo
    input: InputInfo
    output: OutputInfo
    usage: UsageInfo
    tools: ToolsInfo
    metrics: MetricsInfo
    resource: ResourceInfo
    metadata: dict[str, Any] = Field(default_factory=dict)
