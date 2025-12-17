"""
Google Gemini model implementation for Astra Framework.
Supports all Gemini models via the Google Generative AI SDK.
"""

from collections.abc import AsyncIterator
import json
import os
import time
from typing import Any, ClassVar

from dotenv import load_dotenv
from framework.models.base import Model, ModelResponse


load_dotenv()


try:
    from google import genai
    from google.genai import Client as GeminiClient
    from google.genai.errors import ClientError, ServerError
    from google.genai.types import (
        Content,
        GenerateContentConfig,
        Part,
    )
except ImportError as err:
    raise ImportError(
        "`google-genai` not installed or outdated. "
        "Install or upgrade using: pip install -U google-genai"
    ) from err


class Gemini(Model):
    """
    Gemini model provider for Astra.

    Example:
      model = Gemini("gemini-1.5-flash")
    """

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
        "gemini-2.5-flash",
    }

    def __init__(self, model_id: str, api_key: str | None = None, **kwargs: Any):
        super().__init__(
            model_id=model_id,
            api_key=api_key or os.getenv("GOOGLE_API_KEY"),
            **kwargs,
        )
        self._client: GeminiClient | None = None

    def _get_client(self) -> GeminiClient:
        """Get or create Gemini client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "Missing API key for Gemini. Provide api_key or set GOOGLE_API_KEY."
                )
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _lazy_init(self) -> None:
        """Lazy initialization - just validate model ID."""
        if self.model_id not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Unknown Gemini model: '{self.model_id}'. "
                f"Available: {', '.join(sorted(self.AVAILABLE_MODELS))}"
            )

    def _convert_messages_to_content(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[Content], str | None]:
        """
        Convert message list to Gemini SDK Content format.

        Returns:
            Tuple of (formatted_messages, system_message)
        """
        formatted_messages: list[Content] = []
        system_message: str | None = None

        reverse_role_map = {
            "assistant": "model",
            "tool": "user",
        }

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])
            tool_name = msg.get("name")

            # Handle system messages separately
            if role == "system":
                system_message = content
                continue

            # Map role
            gemini_role = reverse_role_map.get(role, role)
            message_parts: list[Part] = []

            if role == "assistant":
                # Assistant messages can have text and/or tool calls
                if content:
                    message_parts.append(Part.from_text(text=content))

                # Add function calls if present
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("arguments", {})
                    if tool_name:
                        message_parts.append(
                            Part.from_function_call(name=tool_name, args=tool_args)
                        )

            elif role == "tool":
                # Tool results are function responses
                tool_name = tool_name or msg.get("name", "")
                tool_content = content

                # Parse JSON content if it's a string
                if isinstance(tool_content, str):
                    try:
                        tool_content = json.loads(tool_content)
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Wrap primitive values in dict
                if not isinstance(tool_content, dict):
                    tool_content = {"result": tool_content}

                if tool_name:
                    message_parts.append(
                        Part.from_function_response(name=tool_name, response=tool_content)
                    )

            elif role == "user":
                # User messages are text parts
                if content:
                    message_parts.append(Part.from_text(text=content))

            # Create Content object
            if message_parts:
                formatted_messages.append(Content(role=gemini_role, parts=message_parts))

        return formatted_messages, system_message

    async def invoke(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Invoke Gemini model for full response."""
        self._lazy_init()
        start_time = time.perf_counter()

        # Convert messages to Content format
        formatted_messages, system_message = self._convert_messages_to_content(messages)

        # Build config
        config_dict: dict[str, Any] = {
            "temperature": temperature,
        }
        if max_tokens:
            config_dict["max_output_tokens"] = max_tokens
        if system_message:
            config_dict["system_instruction"] = system_message

        # Add tools
        if tools:
            # Sanitize tool parameters to remove $schema which causes validation errors
            def sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
                if not params:
                    return {}
                # Remove $schema if present (recursively handle nested schemas)
                sanitized = {k: v for k, v in params.items() if k != "$schema"}

                # Recursively sanitize nested schemas in properties
                if "properties" in sanitized and isinstance(sanitized["properties"], dict):
                    sanitized["properties"] = {
                        key: sanitize_params(value) if isinstance(value, dict) else value
                        for key, value in sanitized["properties"].items()
                    }

                # Recursively sanitize items in arrays
                if "items" in sanitized and isinstance(sanitized["items"], dict):
                    sanitized["items"] = sanitize_params(sanitized["items"])

                return sanitized

            # Use plain dictionaries instead of SDK types
            config_dict["tools"] = [
                {
                    "function_declarations": [
                        {
                            "name": tool.get("name", ""),
                            "description": tool.get("description", ""),
                            "parameters": sanitize_params(tool.get("parameters", {})),
                        }
                    ]
                }
                for tool in tools
            ]

        config = GenerateContentConfig(**{k: v for k, v in config_dict.items() if v is not None})

        client = self._get_client()

        try:
            response = await client.aio.models.generate_content(
                model=self.model_id,
                contents=formatted_messages,
                config=config,
            )
        except (ClientError, ServerError) as e:
            raise RuntimeError(f"Gemini request failed: {e}") from e
        except ValueError as e:
            if "output text or tool calls" in str(e):
                # Handle empty response (likely due to safety filters)
                return ModelResponse(
                    content="(Response blocked by safety filters)",
                    tool_calls=[],
                    usage={},
                    metadata={
                        "provider": "gemini",
                        "model_id": self.model_id,
                        "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
                        "blocked": True,
                        "error": str(e),
                    },
                )
            raise RuntimeError(f"Gemini request failed: {e}") from e

        # Parse response
        tool_calls = []
        content_parts: list[str] = []

        if response.candidates:
            candidate = response.candidates[0]
            parts = getattr(candidate.content, "parts", None)

        if parts:
            for part in parts:
                # When model returns text responses
                if hasattr(part, "text") and part.text:
                    content_parts.append(part.text)
                # When model returns function calls
                elif hasattr(part, "function_call") and part.function_call:
                    tool_calls.append(
                        {
                            "name": part.function_call.name,
                            "arguments": dict(part.function_call.args or {}),
                        }
                    )

        content = "".join(content_parts)

        # Parse usage
        usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage["input_tokens"] = response.usage_metadata.prompt_token_count or 0
            usage["output_tokens"] = response.usage_metadata.candidates_token_count or 0
            usage["total_tokens"] = response.usage_metadata.total_token_count or 0

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if not content and not tool_calls:
            content = "(No response from model)"

        return ModelResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            metadata={
                "provider": "gemini",
                "model_id": self.model_id,
                "latency_ms": latency_ms,
                "has_tool_calls": bool(tool_calls),
            },
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ModelResponse]:
        """Stream Gemini model responses."""
        self._lazy_init()
        start = time.perf_counter()

        # Convert messages to Content format
        formatted_messages, system_message = self._convert_messages_to_content(messages)

        # Build config
        config_dict: dict[str, Any] = {
            "temperature": temperature,
        }
        if max_tokens:
            config_dict["max_output_tokens"] = max_tokens
        if system_message:
            config_dict["system_instruction"] = system_message

        if tools:

            def sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
                if not params:
                    return {}
                # Remove $schema if present (recursively handle nested schemas)
                sanitized = {k: v for k, v in params.items() if k != "$schema"}

                # Recursively sanitize nested schemas in properties
                if "properties" in sanitized and isinstance(sanitized["properties"], dict):
                    sanitized["properties"] = {
                        key: sanitize_params(value) if isinstance(value, dict) else value
                        for key, value in sanitized["properties"].items()
                    }

                # Recursively sanitize items in arrays
                if "items" in sanitized and isinstance(sanitized["items"], dict):
                    sanitized["items"] = sanitize_params(sanitized["items"])

                return sanitized

            config_dict["tools"] = [
                {
                    "function_declarations": [
                        {
                            "name": tool.get("name", ""),
                            "description": tool.get("description", ""),
                            "parameters": sanitize_params(tool.get("parameters", {})),
                        }
                    ]
                }
                for tool in tools
            ]

        config = GenerateContentConfig(**{k: v for k, v in config_dict.items() if v is not None})

        client = self._get_client()

        try:
            async_stream = await client.aio.models.generate_content_stream(
                model=self.model_id,
                contents=formatted_messages,
                config=config,
            )

            async for chunk in async_stream:
                # Parse chunk
                text = ""
                tool_calls = []

                # Check candidates
                if chunk.candidates and len(chunk.candidates) > 0:
                    candidate = chunk.candidates[0]
                    candidate_content = candidate.content

                    # Create Content object (for safety)
                    response_message = Content(role="model", parts=[])
                    if candidate_content is not None:
                        response_message = candidate_content

                    # Access parts
                    if response_message.parts is not None:
                        for part in response_message.parts:
                            # Extract text
                            if hasattr(part, "text") and part.text is not None:
                                text_content = str(part.text) if part.text is not None else ""
                                text += text_content

                            # Extract function call if present (matching invoke format)
                            if hasattr(part, "function_call") and part.function_call is not None:
                                # Match the format used in invoke method: {"name": ..., "arguments": {...}}
                                tool_call = {
                                    "name": part.function_call.name
                                    if hasattr(part.function_call, "name")
                                    else "",
                                    "arguments": dict(part.function_call.args or {})
                                    if hasattr(part.function_call, "args")
                                    and part.function_call.args is not None
                                    else {},
                                }
                                # Only add if name is present and not already added (avoid duplicates)
                                if tool_call["name"] and tool_call not in tool_calls:
                                    tool_calls.append(tool_call)

                # Yield response if we have text or tool calls (some chunks might be empty, which is normal)
                if text or tool_calls:
                    yield ModelResponse(
                        content=text,
                        tool_calls=tool_calls if tool_calls else None,
                        metadata={"is_stream": True},
                    )

            # Get usage metadata from final chunk
            usage_meta = getattr(async_stream, "usage_metadata", None)
            usage = {}
            if usage_meta:
                usage["input_tokens"] = getattr(usage_meta, "prompt_token_count", 0)
                usage["output_tokens"] = getattr(usage_meta, "candidates_token_count", 0)
                usage["total_tokens"] = getattr(usage_meta, "total_token_count", 0)

            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            yield ModelResponse(
                content="",
                usage=usage,
                metadata={
                    "provider": "gemini",
                    "model_id": self.model_id,
                    "latency_ms": latency_ms,
                    "final": True,
                },
            )

        except (ClientError, ServerError) as e:
            raise RuntimeError(f"Gemini streaming failed: {e}") from e
        except ValueError as e:
            if "output text or tool calls" in str(e):
                # Yield a blocked response
                yield ModelResponse(
                    content="(Response blocked by safety filters)",
                    metadata={"blocked": True, "error": str(e)},
                )
                return
            raise RuntimeError(f"Gemini streaming failed: {e}") from e
