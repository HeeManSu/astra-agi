"""
Type definitions and constants for AWS Bedrock model implementation.
This file contains ONLY constants, type aliases, and enums - no logic.
"""

from typing import Literal


# Supported Bedrock Chat Model IDs
# Reference: https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html
BEDROCK_SUPPORTED_MODELS: set[str] = {
    # Amazon Titan models
    "amazon.titan-tg1-large",
    "amazon.titan-text-express-v1",
    "amazon.titan-text-lite-v1",
    # Amazon Nova models
    "us.amazon.nova-premier-v1:0",
    "us.amazon.nova-pro-v1:0",
    "us.amazon.nova-micro-v1:0",
    "us.amazon.nova-lite-v1:0",
    # Anthropic Claude models
    "anthropic.claude-v2",
    "anthropic.claude-v2:1",
    "anthropic.claude-instant-v1",
    "anthropic.claude-haiku-4-5-20251001-v1:0",
    "anthropic.claude-sonnet-4-20250514-v1:0",
    "anthropic.claude-sonnet-4-5-20250929-v1:0",
    "anthropic.claude-opus-4-20250514-v1:0",
    "anthropic.claude-opus-4-1-20250805-v1:0",
    "anthropic.claude-3-7-sonnet-20250219-v1:0",
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-5-haiku-20241022-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-3-opus-20240229-v1:0",
    # US Anthropic models
    "us.anthropic.claude-3-sonnet-20240229-v1:0",
    "us.anthropic.claude-3-opus-20240229-v1:0",
    "us.anthropic.claude-3-haiku-20240307-v1:0",
    "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
    "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "us.anthropic.claude-opus-4-20250514-v1:0",
    "us.anthropic.claude-opus-4-1-20250805-v1:0",
    # Meta Llama models
    "meta.llama3-70b-instruct-v1:0",
    "meta.llama3-8b-instruct-v1:0",
    "meta.llama3-1-405b-instruct-v1:0",
    "meta.llama3-1-70b-instruct-v1:0",
    "meta.llama3-1-8b-instruct-v1:0",
    "meta.llama3-2-11b-instruct-v1:0",
    "meta.llama3-2-1b-instruct-v1:0",
    "meta.llama3-2-3b-instruct-v1:0",
    "meta.llama3-2-90b-instruct-v1:0",
    # US Meta models
    "us.meta.llama3-2-11b-instruct-v1:0",
    "us.meta.llama3-2-3b-instruct-v1:0",
    "us.meta.llama3-2-90b-instruct-v1:0",
    "us.meta.llama3-2-1b-instruct-v1:0",
    "us.meta.llama3-1-8b-instruct-v1:0",
    "us.meta.llama3-1-70b-instruct-v1:0",
    "us.meta.llama3-3-70b-instruct-v1:0",
    "us.meta.llama4-scout-17b-instruct-v1:0",
    "us.meta.llama4-maverick-17b-instruct-v1:0",
    # Mistral models
    "mistral.mistral-7b-instruct-v0:2",
    "mistral.mixtral-8x7b-instruct-v0:1",
    "mistral.mistral-large-2402-v1:0",
    "mistral.mistral-small-2402-v1:0",
    # US Mistral models
    "us.mistral.pixtral-large-2502-v1:0",
    # Cohere models
    "cohere.command-text-v14",
    "cohere.command-light-text-v14",
    "cohere.command-r-v1:0",
    "cohere.command-r-plus-v1:0",
    # OpenAI models
    "openai.gpt-oss-120b-1:0",
    "openai.gpt-oss-20b-1:0",
    # DeepSeek models
    "us.deepseek.r1-v1:0",
}

# Valid stop reasons from Bedrock API
# Reference: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html
BEDROCK_STOP_REASONS: list[str] = [
    "stop",
    "stop_sequence",
    "end_turn",
    "length",
    "max_tokens",
    "content-filter",
    "content_filtered",
    "guardrail_intervened",
    "tool-calls",
    "tool_use",
]

# Supported image MIME types and formats
# Reference: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ImageBlock.html
BEDROCK_IMAGE_MIME_TYPES: dict[str, str] = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}

# Supported document MIME types and formats
# Reference: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_DocumentBlock.html
BEDROCK_DOCUMENT_MIME_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "text/csv": "csv",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/html": "html",
    "text/plain": "txt",
    "text/markdown": "md",
}

# Default AWS region if not specified
BEDROCK_DEFAULT_REGION: str = "us-east-1"

from typing import Any


# Type aliases for better type hints
BedrockModelId = str
BedrockContentBlock = dict[str, Any]
BedrockMessage = dict[str, Any]
BedrockStopReason = Literal[
    "stop",
    "stop_sequence",
    "end_turn",
    "length",
    "max_tokens",
    "content-filter",
    "content_filtered",
    "guardrail_intervened",
    "tool-calls",
    "tool_use",
]
