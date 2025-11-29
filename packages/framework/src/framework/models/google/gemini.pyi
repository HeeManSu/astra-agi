"""Type stubs for Gemini model - enables IDE autocomplete for model names."""

from collections.abc import AsyncGenerator
from typing import Any, Literal

from framework.models.base import Model, ModelResponse

# Available Gemini models
GeminiModelId = Literal[
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash-001",
    "gemini-1.5-pro",
    "gemini-1.5-pro-001",
    "gemini-2.0-flash-exp",
    "gemini-exp-1206",
    "gemini-pro",
    "gemini-1.0-pro",
    "gemini-2.5-flash",
]

class Gemini(Model):
    """Google Gemini model."""

    model_id: str

    def __init__(
        self,
        model_id: GeminiModelId,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> None: ...
    async def invoke(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ModelResponse: ...
    def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[ModelResponse, None]: ...

# Export for discovery
AVAILABLE_MODELS: list[str]
