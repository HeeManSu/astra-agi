"""
Google Gemini model implementation for Astra Framework.
Supports all Gemini models via the Google Generative AI SDK.
"""

from collections.abc import AsyncIterator
import os
import time
from typing import Any, ClassVar

from framework.models.base import Model, ModelResponse
from google.generativeai.generative_models import GenerativeModel


class Gemini(Model):
    """
    Gemini model provider for Astra.

    Example:
      model = Gemini("gemini-1.5-flash")
    """

    # Use set for O(1) model lookup
    AVAILABLE_MODELS: ClassVar[set[str]] = {
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-flash-001",
        "gemini-1.5-pro",
        "gemini-1.5-pro-001",
        "gemini-2.0-flash-exp",
        "gemini-exp-1206",
        "gemini-pro",
        "gemini-1.0-pro",
    }

    def __init__(self, model_id: str, api_key: str | None = None, **kwargs: Any):
        super().__init__(
            model_id=model_id, api_key=api_key or os.getenv("GOOGLE_API_KEY"), **kwargs
        )
        self._model: GenerativeModel | None = None

    def _lazy_init(self) -> None:
        """
        Performs validation + model build only when first used.
        Ensures self._model is initialized.
        """

        if self._model is not None:
            return

        # Validate model ID
        if self.model_id not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Unknown Gemini model: '{self.model_id}'. "
                f"Available: {', '.join(sorted(self.AVAILABLE_MODELS))}"
            )

        # Validate API key
        if not self.api_key:
            raise ValueError("Missing API key for Gemini. Provide api_key or set GOOGLE_API_KEY.")

        try:
            self._model = GenerativeModel(self.model_id)
        except Exception as e:
            raise ValueError(f"Failed to initialize Gemini model '{self.model_id}'.") from e

    async def invoke(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        """Invoke Gemini model for full response.

        Returns:
            ModelResponse: Complete model response
        """

        self._lazy_init()
        start_time = time.perf_counter()

        # Build prompt
        prompt = "\n".join(msg["content"] for msg in messages)

        # Build generation config
        gen_config: dict[str, Any] = {"temperature": temperature}

        # Apply token limits if provided
        if max_tokens:
            gen_config["max_output_tokens"] = max_tokens

        # If JSON mode is requested → set correct response mime type & schema
        if response_format:
            gen_config["response_mime_type"] = "application/json"
            if "json_schema" in response_format:
                gen_config["response_schema"] = response_format["json_schema"]

        # Build final kwargs for Gemini SDK call
        gen_kwargs = {
            "generation_config": gen_config,
            **kwargs,
        }

        # TODO: Full tool calling to be added later
        # We are calling the model asynchronously to avoid blocking the main thread.

        if self._model is None:
            raise ValueError("Model not initialized")

        response = await self._model.generate_content_async(prompt, **gen_kwargs)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        usage_meta = getattr(response, "usage_metadata", {}) or {}

        return ModelResponse(
            content=response.text or "",
            tool_calls=[],
            usage={
                "input_tokens": usage_meta.get("prompt_token_count"),
                "output_tokens": usage_meta.get("candidates_token_count"),
                "total_tokens": usage_meta.get("total_token_count"),
            },
            metadata={
                "provider": "gemini",
                "latency_ms": latency_ms,
                "model_id": self.model_id,
            },
        )

    async def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ModelResponse]:
        """Stream Gemini model responses."""
        self._lazy_init()
        start = time.perf_counter()

        prompt = "\n".join(m["content"] for m in messages)
        gen_config = {"temperature": temperature}
        if max_tokens:
            gen_config["max_output_tokens"] = max_tokens

        gen_kwargs = {"generation_config": gen_config, **kwargs}

        if self._model is None:
            raise ValueError("Model not initialized")

        stream = await self._model.generate_content_async(prompt, **gen_kwargs)

        async for chunk in stream:
            text = getattr(chunk, "text", "")
            if not text:
                continue

            yield ModelResponse(content=text, metadata={"is_stream": True})

        yield ModelResponse(
            content="",
            usage=getattr(stream, "usage_metadata", {}),
            metadata={
                "provider": "gemini",
                "model_id": self.model_id,
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                "final": True,
            },
        )
