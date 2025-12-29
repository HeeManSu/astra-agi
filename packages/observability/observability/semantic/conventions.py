from __future__ import annotations


class LLMAttributes:
    SYSTEM = "llm.system"
    OPERATION = "llm.operation"
    REQUEST_MODEL = "llm.request.model"
    REQUEST_STREAMING = "llm.request.streaming"
    REQUEST_TEMPERATURE = "llm.request.temperature"
    REQUEST_MAX_TOKENS = "llm.request.max_tokens"
    REQUEST_PROMPT = "llm.request.prompt"
    REQUEST_TOP_P = "llm.request.top_p"
    REQUEST_TOP_K = "llm.request.top_k"
    REQUEST_SEED = "llm.request.seed"
    REQUEST_STOP_SEQUENCES = "llm.request.stop_sequences"
    PROMPT_CONTENT_PREFIX = "prompt.content["
    PROMPT_ROLE_PREFIX = "prompt.role["
    RESPONSE_TEXT = "llm.response.text"
    COMPLETION_CONTENT_PREFIX = "completion.content["
    COMPLETION_ROLE_PREFIX = "completion.role["
    COMPLETION_FINISH_REASON_PREFIX = "completion.finish_reason["
    RESPONSE_MODEL = "llm.response.model"
    USAGE_PROMPT_TOKENS = "llm.usage.prompt_tokens"
    USAGE_COMPLETION_TOKENS = "llm.usage.completion_tokens"
    USAGE_TOTAL_TOKENS = "llm.usage.total_tokens"
    USAGE_CACHED_TOKENS = "llm.usage.cached_tokens"


class GenAIAttributes:
    """
    Deprecated: Use LLMAttributes instead.
    Kept for backward compatibility.
    """
    SYSTEM = LLMAttributes.SYSTEM
    OPERATION = LLMAttributes.OPERATION
    REQUEST_MODEL = LLMAttributes.REQUEST_MODEL
    REQUEST_TEMPERATURE = LLMAttributes.REQUEST_TEMPERATURE
    REQUEST_MAX_TOKENS = LLMAttributes.REQUEST_MAX_TOKENS
    REQUEST_PROMPT = LLMAttributes.REQUEST_PROMPT
    RESPONSE_TEXT = LLMAttributes.RESPONSE_TEXT
    USAGE_INPUT_TOKENS = LLMAttributes.USAGE_PROMPT_TOKENS
    USAGE_OUTPUT_TOKENS = LLMAttributes.USAGE_COMPLETION_TOKENS
    USAGE_TOTAL_TOKENS = LLMAttributes.USAGE_TOTAL_TOKENS
    USAGE_CACHED_TOKENS = LLMAttributes.USAGE_CACHED_TOKENS


class AstraSpanKind:
    AGENT = "agent"
    TOOL = "tool"
    STEP = "step"
    LLM = "llm"


class AstraAttributes:
    # Common
    SPAN_KIND = "astra.span.kind"

    # Agent
    AGENT_NAME = "agent.name"
    AGENT_TYPE = "agent.type"
    AGENT_THREAD_ID = "agent.thread_id"
    AGENT_CONVERSATION_ID = "agent.conversation_id"

    # Step
    STEP_NAME = "step.name"
    STEP_TYPE = "step.type"
    STEP_PURPOSE = "step.purpose"

    # Tool
    TOOL_NAME = "tool.name"
    TOOL_TYPE = "tool.type"
    TOOL_INPUT = "tool.input"
    TOOL_OUTPUT = "tool.output"
    TOOL_ERROR = "tool.error"


class AstraErrorAttributes:
    TYPE = "error.type"
    RETRYABLE = "error.retryable"
    STAGE = "error.stage"
    CATEGORY = "error.category"
