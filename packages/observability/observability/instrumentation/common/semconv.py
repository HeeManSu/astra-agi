from __future__ import annotations


class GenAIAttributes:
    SYSTEM = "genai.system"
    OPERATION = "genai.operation"
    REQUEST_MODEL = "genai.request.model"
    REQUEST_TEMPERATURE = "genai.request.temperature"
    REQUEST_MAX_TOKENS = "genai.request.max_tokens"
    REQUEST_PROMPT = "genai.request.prompt"
    RESPONSE_TEXT = "genai.response.text"
    USAGE_INPUT_TOKENS = "genai.usage.input_tokens"
    USAGE_OUTPUT_TOKENS = "genai.usage.output_tokens"
    USAGE_TOTAL_TOKENS = "genai.usage.total_tokens"
    USAGE_CACHED_TOKENS = "genai.usage.cached_tokens"


class LLMAttributes:
    SYSTEM = "llm.system"
    REQUEST_MODEL = "llm.request.model"
    REQUEST_STREAMING = "llm.request.streaming"
    REQUEST_TEMPERATURE = "llm.request.temperature"
    REQUEST_MAX_TOKENS = "llm.request.max_tokens"
    REQUEST_TOP_P = "llm.request.top_p"
    REQUEST_TOP_K = "llm.request.top_k"
    REQUEST_SEED = "llm.request.seed"
    REQUEST_STOP_SEQUENCES = "llm.request.stop_sequences"
    PROMPT_CONTENT_PREFIX = "prompt.content["
    PROMPT_ROLE_PREFIX = "prompt.role["
    COMPLETION_CONTENT_PREFIX = "completion.content["
    COMPLETION_ROLE_PREFIX = "completion.role["
    COMPLETION_FINISH_REASON_PREFIX = "completion.finish_reason["
    RESPONSE_MODEL = "llm.response.model"
    USAGE_PROMPT_TOKENS = "llm.usage.prompt_tokens"
    USAGE_COMPLETION_TOKENS = "llm.usage.completion_tokens"
    USAGE_TOTAL_TOKENS = "llm.usage.total_tokens"

