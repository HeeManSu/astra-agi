"""
Google Gemini Model Implementation for Astra Framework.

This module provides the Gemini class for interacting with Google's Gemini AI models.
It handles:
- Converting messages between Astra format and Gemini SDK format
- Preparing tool schemas for function calling
- Parsing responses (both regular and streaming)
- Error handling with safety filters

Supported models:
- gemini-1.5-flash, gemini-1.5-pro
- gemini-2.0-flash-exp
- gemini-2.5-flash (latest)

Example usage:
    from framework.models.google import Gemini

    model = Gemini("gemini-2.5-flash")
    response = await model.invoke([
        {"role": "user", "content": "Hello!"}
    ])
    print(response.content)
"""

# IMPORTS

from collections.abc import AsyncIterator
import json
import os
import time
from typing import Any, ClassVar
import uuid

from dotenv import load_dotenv
from framework.models.base import Model, ModelResponse


# Load environment variables from .env file
load_dotenv()


# Import Gemini SDK with helpful error message if not installed
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


# HELPER FUNCTIONS - Schema Utilities
# These functions clean up tool parameter schemas before sending to Gemini API.
# Gemini doesn't accept certain JSON Schema fields like "$schema".


def _sanitize_schema_recursive(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively remove unsupported fields from a JSON schema.

    Gemini API doesn't accept the "$schema" field that's common in JSON Schema.
    This function removes it from the schema and all nested schemas.

    Args:
        schema: A JSON schema dictionary (may contain nested schemas)

    Returns:
        Cleaned schema without "$schema" fields

    Example:
        >>> schema = {"$schema": "...", "type": "object", "properties": {"x": {"$schema": "..."}}}
        >>> _sanitize_schema_recursive(schema)
        {"type": "object", "properties": {"x": {}}}
    """
    if not schema:
        return {}

    # Remove $schema from current level
    sanitized = {key: value for key, value in schema.items() if key != "$schema"}

    # Recursively clean nested schemas in "properties" (for object types)
    # Example: {"properties": {"name": {"type": "string", "$schema": "..."}}}
    if "properties" in sanitized and isinstance(sanitized["properties"], dict):
        sanitized["properties"] = {
            prop_name: _sanitize_schema_recursive(prop_schema)
            if isinstance(prop_schema, dict)
            else prop_schema
            for prop_name, prop_schema in sanitized["properties"].items()
        }

    # Recursively clean nested schemas in "items" (for array types)
    # Example: {"type": "array", "items": {"type": "string", "$schema": "..."}}
    if "items" in sanitized and isinstance(sanitized["items"], dict):
        sanitized["items"] = _sanitize_schema_recursive(sanitized["items"])

    return sanitized


def sanitize_tool_parameters(params: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize tool parameters for Gemini API compatibility.

    This is the main entry point for cleaning tool schemas.
    It removes fields that Gemini doesn't accept.

    Args:
        params: Tool parameter schema (JSON Schema format)

    Returns:
        Cleaned schema ready for Gemini API

    Example:
        >>> tool_params = {"$schema": "http://json-schema.org/...", "type": "object"}
        >>> sanitize_tool_parameters(tool_params)
        {"type": "object"}
    """
    return _sanitize_schema_recursive(params)


# HELPER FUNCTIONS - Message Conversion
# These functions convert messages from Astra's format to Gemini SDK's format.
#
# Astra message format:
#   {"role": "user", "content": "Hello"}
#   {"role": "assistant", "content": "Hi!", "tool_calls": [...]}
#   {"role": "tool", "name": "calculator", "content": "42"}
#
# Gemini SDK format:
#   Content(role="user", parts=[Part.from_text("Hello")])
#   Content(role="model", parts=[Part.from_text("Hi!"), Part.from_function_call(...)])


def _convert_user_message(msg: dict[str, Any]) -> list[Part]:
    """
    Convert a user message to Gemini Part objects.

    User messages are simple - just text content.

    Args:
        msg: Message dict with "content" field

    Returns:
        List of Gemini Part objects (usually just one text part)

    Example:
        >>> _convert_user_message({"role": "user", "content": "What's 2+2?"})
        [Part.from_text("What's 2+2?")]
    """
    parts: list[Part] = []
    content = msg.get("content", "")

    if content:
        parts.append(Part.from_text(text=content))

    return parts


def _convert_assistant_message(msg: dict[str, Any]) -> list[Part]:
    """
    Convert an assistant message to Gemini Part objects.

    Assistant messages can have:
    - Text content (the model's response)
    - Tool calls (function calls the model wants to make)

    Args:
        msg: Message dict with "content" and optional "tool_calls" fields

    Returns:
        List of Gemini Part objects (text + function calls)

    Example:
        >>> msg = {
        ...     "role": "assistant",
        ...     "content": "Let me calculate...",
        ...     "tool_calls": [{"name": "add", "arguments": {"a": 2, "b": 2}}],
        ... }
        >>> parts = _convert_assistant_message(msg)
        # Returns: [Part.from_text("Let me calculate..."), Part.from_function_call("add", {...})]
    """
    parts: list[Part] = []

    # Add text content if present
    content = msg.get("content", "")
    if content:
        parts.append(Part.from_text(text=content))

    # Add function calls if present
    # Tool calls format: [{"name": "tool_name", "arguments": {...}}, ...]
    tool_calls = msg.get("tool_calls", [])
    for tool_call in tool_calls:
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("arguments", {})

        if tool_name:
            parts.append(Part.from_function_call(name=tool_name, args=tool_args))

    return parts


def _convert_tool_result_message(msg: dict[str, Any]) -> list[Part]:
    """
    Convert a tool result message to Gemini Part objects.

    After a tool is executed, the result is sent back to the model
    as a "tool" message. Gemini expects this as a function_response.

    Args:
        msg: Message dict with "name" (tool name) and "content" (result)

    Returns:
        List containing a single function_response Part

    Example:
        >>> msg = {"role": "tool", "name": "calculator", "content": "42"}
        >>> _convert_tool_result_message(msg)
        [Part.from_function_response("calculator", {"result": "42"})]
    """
    parts: list[Part] = []

    tool_name = msg.get("name", "")
    tool_content = msg.get("content", "")

    # Try to parse content as JSON (tools often return JSON)
    if isinstance(tool_content, str):
        try:
            tool_content = json.loads(tool_content)
        except (json.JSONDecodeError, TypeError):
            # If it's not valid JSON, keep it as a string
            pass

    # Gemini expects function responses to be dicts
    # Wrap primitive values in a dict
    if not isinstance(tool_content, dict):
        tool_content = {"result": tool_content}

    if tool_name:
        parts.append(Part.from_function_response(name=tool_name, response=tool_content))

    return parts


def convert_messages_to_gemini_content(
    messages: list[dict[str, Any]],
) -> tuple[list[Content], str | None]:
    """
    Convert a list of Astra messages to Gemini SDK Content format.

    This is the main message conversion function. It:
    1. Extracts system messages (used as system_instruction in Gemini)
    2. Converts all other messages to Gemini Content objects

    Args:
        messages: List of Astra format messages

    Returns:
        Tuple of:
        - List of Gemini Content objects
        - System instruction string (or None if no system message)

    Message roles:
        - "system" → Extracted as system_instruction (Gemini handles separately)
        - "user" → Content with role="user"
        - "assistant" → Content with role="model"
        - "tool" → Content with role="user" (tool results go back as user)

    Example:
        >>> messages = [
        ...     {"role": "system", "content": "You are helpful."},
        ...     {"role": "user", "content": "Hello!"},
        ...     {"role": "assistant", "content": "Hi there!"},
        ... ]
        >>> contents, system = convert_messages_to_gemini_content(messages)
        >>> system
        "You are helpful."
        >>> len(contents)
        2  # user and assistant messages
    """
    formatted_messages: list[Content] = []
    system_message: str | None = None

    # Map Astra roles to Gemini roles
    # - "assistant" → "model" (Gemini uses "model" for AI responses)
    # - "tool" → "user" (tool results are sent as user messages in Gemini)
    role_mapping = {
        "assistant": "model",
        "tool": "user",
    }

    for msg in messages:
        role = msg.get("role", "user")

        # Handle system messages separately
        # Gemini uses system_instruction parameter instead of a system message
        if role == "system":
            system_message = msg.get("content", "")
            continue

        # Convert message to Parts based on role
        if role == "assistant":
            message_parts = _convert_assistant_message(msg)
        elif role == "tool":
            message_parts = _convert_tool_result_message(msg)
        else:  # user or unknown roles treated as user
            message_parts = _convert_user_message(msg)

        # Get the Gemini role (map assistant→model, tool→user)
        gemini_role = role_mapping.get(role, role)

        # Create Content object if we have parts
        if message_parts:
            formatted_messages.append(Content(role=gemini_role, parts=message_parts))

    return formatted_messages, system_message


# HELPER FUNCTIONS - Tool Preparation
# These functions prepare tool definitions for the Gemini API.
# Gemini uses a specific format for function declarations.


def prepare_tools_for_gemini(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert Astra tool schemas to Gemini function_declarations format.

    Astra tool format:
        {"name": "add", "description": "Add numbers", "parameters": {...}}

    Gemini expects:
        [{"function_declarations": [{"name": "add", "description": "...", "parameters": {...}}]}]

    Args:
        tools: List of Astra tool schemas

    Returns:
        List of Gemini tool declarations (wrapped in function_declarations)

    Example:
        >>> tools = [{"name": "search", "description": "Search web", "parameters": {...}}]
        >>> prepare_tools_for_gemini(tools)
        [{"function_declarations": [{"name": "search", "description": "...", "parameters": {...}}]}]
    """
    gemini_tools = []

    for tool in tools:
        # Create function declaration for each tool
        function_declaration = {
            "name": tool.get("name", ""),
            "description": tool.get("description", ""),
            "parameters": sanitize_tool_parameters(tool.get("parameters", {})),
        }

        # Gemini wraps each tool in a function_declarations list
        gemini_tools.append({"function_declarations": [function_declaration]})

    return gemini_tools


# HELPER FUNCTIONS - Response Parsing
# These functions parse Gemini API responses into Astra's ModelResponse format.


def parse_response_parts(parts: list | None) -> tuple[str, list[dict[str, Any]]]:
    """
    Parse Gemini response parts into text content and tool calls.

    Gemini responses contain "parts" which can be:
    - Text parts (the model's text response)
    - Function call parts (tools the model wants to call)

    Args:
        parts: List of Gemini Part objects from response

    Returns:
        Tuple of:
        - Combined text content (all text parts joined)
        - List of tool calls in simple format: [{"name": str, "arguments": dict}]

    Example:
        >>> parts = [Part(text="Hello"), Part(function_call={"name": "search", "args": {...}})]
        >>> text, tool_calls = parse_response_parts(parts)
        >>> text
        "Hello"
        >>> tool_calls
        [{"name": "search", "arguments": {...}}]
    """
    content_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []

    if not parts:
        return "", []

    for part in parts:
        # Extract text content
        if hasattr(part, "text") and part.text:
            content_parts.append(part.text)

        # Extract function calls
        # Gemini returns function_call with name and args
        elif hasattr(part, "function_call") and part.function_call:
            tool_name = getattr(part.function_call, "name", "")
            # Skip empty tool names - they cause issues downstream
            if not tool_name:
                continue
            tool_call = {
                "id": f"call_{uuid.uuid4().hex[:8]}",  # Unique ID for tracking
                "name": tool_name,
                "arguments": dict(part.function_call.args or {}),
            }
            tool_calls.append(tool_call)

    # Join all text parts into a single string
    content = "".join(content_parts)

    return content, tool_calls


def parse_usage_metadata(usage_meta: Any) -> dict[str, int]:
    """
    Extract token usage statistics from Gemini response metadata.

    Token usage is important for:
    - Cost tracking (API charges per token)
    - Context window management
    - Debugging/optimization

    Args:
        usage_meta: Gemini usage_metadata object

    Returns:
        Dict with token counts: input_tokens, output_tokens, total_tokens

    Example:
        >>> usage = parse_usage_metadata(response.usage_metadata)
        >>> usage
        {"input_tokens": 50, "output_tokens": 100, "total_tokens": 150}
    """
    if not usage_meta:
        return {}

    return {
        "input_tokens": getattr(usage_meta, "prompt_token_count", 0) or 0,
        "output_tokens": getattr(usage_meta, "candidates_token_count", 0) or 0,
        "total_tokens": getattr(usage_meta, "total_token_count", 0) or 0,
    }


# GEMINI MODEL CLASS


class Gemini(Model):
    """
    Gemini model provider for Astra Framework.

    This class provides a unified interface to Google's Gemini AI models.
    It supports both synchronous (invoke) and streaming (stream) responses,
    as well as tool/function calling.

    Features:
        - All Gemini models (1.5-flash, 2.0-flash, 2.5-flash, etc.)
        - Tool/function calling with automatic schema conversion
        - Streaming responses for real-time output
        - System instructions support
        - Safety filter handling

    Example - Basic usage:
        model = Gemini("gemini-2.5-flash")
        response = await model.invoke([
            {"role": "user", "content": "What is Python?"}
        ])
        print(response.content)

    Example - With tools:
        tools = [{"name": "search", "description": "Search web", "parameters": {...}}]
        response = await model.invoke(messages, tools=tools)
        if response.tool_calls:
            print(f"Model wants to call: {response.tool_calls}")

    Example - Streaming:
        async for chunk in model.stream(messages):
            print(chunk.content, end="", flush=True)

    Tool Call Format:
        Tool calls are returned in simple format for easy processing:
        {"name": "tool_name", "arguments": {"arg1": "value1"}}

    Environment Variables:
        GOOGLE_API_KEY: Your Google AI API key (required if not passed to __init__)
    """

    # List of supported Gemini model IDs
    # Add new models here as Google releases them
    AVAILABLE_MODELS: ClassVar[set[str]] = {
        # Gemini 1.5 series
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-flash-001",
        "gemini-1.5-pro",
        "gemini-1.5-pro-001",
        # Gemini 2.0 series
        "gemini-2.0-flash-exp",
        # Gemini 2.5 series (latest)
        "gemini-2.5-flash",
        # Legacy models
        "gemini-exp-1206",
        "gemini-pro",
        "gemini-1.0-pro",
    }

    def __init__(self, model_id: str, api_key: str | None = None, **kwargs: Any):
        """
        Initialize a Gemini model instance.

        Args:
            model_id: The Gemini model to use (e.g., "gemini-2.5-flash")
            api_key: Optional Google AI API key. If not provided,
                    will use GOOGLE_API_KEY environment variable.
            **kwargs: Additional configuration options

        Raises:
            ValueError: If model_id is not in AVAILABLE_MODELS

        Example:
            # Using environment variable
            model = Gemini("gemini-2.5-flash")

            # Or with explicit API key
            model = Gemini("gemini-2.5-flash", api_key="your-api-key")
        """
        super().__init__(
            model_id=model_id,
            api_key=api_key or os.getenv("GOOGLE_API_KEY"),
            **kwargs,
        )
        # Client is created lazily (on first use) for efficiency
        self._client: GeminiClient | None = None

    def _get_client(self) -> GeminiClient:
        """
        Get or create the Gemini API client.

        Uses lazy initialization - the client is only created when first needed.
        This saves resources if the model is created but not immediately used.

        Returns:
            GeminiClient instance

        Raises:
            ValueError: If no API key is available
        """
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "Missing API key for Gemini. "
                    "Provide api_key parameter or set GOOGLE_API_KEY environment variable."
                )
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _validate_model(self) -> None:
        """
        Validate that the model ID is supported.

        Raises:
            ValueError: If model_id is not in AVAILABLE_MODELS
        """
        if self.model_id not in self.AVAILABLE_MODELS:
            available = ", ".join(sorted(self.AVAILABLE_MODELS))
            raise ValueError(
                f"Unknown Gemini model: '{self.model_id}'. Available models: {available}"
            )

    def _build_config(
        self,
        temperature: float,
        max_tokens: int | None,
        system_message: str | None,
        tools: list[dict[str, Any]] | None,
    ) -> GenerateContentConfig:
        """
        Build the Gemini GenerateContentConfig from parameters.

        This method centralizes config creation for both invoke and stream,
        reducing code duplication.

        Args:
            temperature: Sampling temperature (0.0 = deterministic, 2.0 = creative)
            max_tokens: Maximum number of tokens in the response
            system_message: Optional system instruction for the model
            tools: Optional list of tool schemas

        Returns:
            GenerateContentConfig ready for the Gemini API
        """
        config_dict: dict[str, Any] = {
            "temperature": temperature,
        }

        # Add optional parameters
        if max_tokens:
            config_dict["max_output_tokens"] = max_tokens

        if system_message:
            config_dict["system_instruction"] = system_message

        # Add tools if provided
        if tools:
            config_dict["tools"] = prepare_tools_for_gemini(tools)

        # Create config, filtering out None values
        return GenerateContentConfig(**{k: v for k, v in config_dict.items() if v is not None})

    async def invoke(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """
        Invoke the Gemini model and get a complete response.

        This method sends messages to Gemini and waits for the full response.
        Use this for simple request-response interactions.

        Args:
            messages: List of conversation messages in Astra format
                     [{"role": "user", "content": "Hello"}, ...]
            tools: Optional list of tool schemas for function calling
            temperature: Sampling temperature (0.0-2.0, default 0.7)
                        Lower = more deterministic, higher = more creative
            max_tokens: Maximum output tokens (None = model default)
            response_format: Reserved for future use (structured output)
            **kwargs: Additional arguments (ignored)

        Returns:
            ModelResponse with:
            - content: The model's text response
            - tool_calls: List of tool calls [{"name": str, "arguments": dict}]
            - usage: Token counts {"input_tokens", "output_tokens", "total_tokens"}
            - metadata: Provider info and timing

        Raises:
            ValueError: If model validation fails
            RuntimeError: If the API request fails

        Example:
            response = await model.invoke([
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What's the weather like?"}
            ])

            if response.tool_calls:
                # Model wants to call a tool
                for tool_call in response.tool_calls:
                    print(f"Call {tool_call['name']} with {tool_call['arguments']}")
            else:
                # Regular text response
                print(response.content)
        """
        # Validate model ID
        self._validate_model()
        start_time = time.perf_counter()

        # Convert messages to Gemini format
        formatted_messages, system_message = convert_messages_to_gemini_content(messages)

        # Build configuration
        config = self._build_config(
            temperature=temperature,
            max_tokens=max_tokens,
            system_message=system_message,
            tools=tools,
        )

        # Get client and make API call
        client = self._get_client()

        print("Making API call")

        try:
            response = await client.aio.models.generate_content(
                model=self.model_id,
                contents=formatted_messages,
                config=config,
            )
            print("API call successful")
        except (ClientError, ServerError) as e:
            raise RuntimeError(f"Gemini request failed: {e}") from e
        except (ValueError, Exception) as e:
            # Handle empty response (often due to safety filters or rate limits)
            error_str = str(e)
            if "output text or tool calls" in error_str or "empty" in error_str.lower():
                return ModelResponse(
                    content="(Model returned empty response. This may be due to safety filters or rate limiting. Please try again.)",
                    tool_calls=[],
                    usage={},
                    metadata={
                        "provider": "gemini",
                        "model_id": self.model_id,
                        "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
                        "blocked": True,
                        "error": error_str,
                    },
                )
            raise RuntimeError(f"Gemini request failed: {e}") from e

        # Parse the response
        content = ""
        tool_calls: list[dict[str, Any]] = []

        # Extract parts from the first candidate
        if response.candidates:
            candidate = response.candidates[0]
            parts = getattr(candidate.content, "parts", None)
            content, tool_calls = parse_response_parts(parts)

        # Parse usage metadata
        usage = parse_usage_metadata(getattr(response, "usage_metadata", None))
        print("Usage:", usage)

        # Calculate latency
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Handle empty response
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
        """
        Stream responses from the Gemini model.

        This method returns an async iterator that yields response chunks
        as they arrive from the API. Use this for:
        - Real-time output display (chatbots, CLI tools)
        - Long responses where you want to show progress
        - Reducing perceived latency

        Args:
            messages: List of conversation messages in Astra format
            tools: Optional list of tool schemas for function calling
            temperature: Sampling temperature (0.0-2.0, default 0.7)
            max_tokens: Maximum output tokens
            response_format: Reserved for future use
            **kwargs: Additional arguments (ignored)

        Yields:
            ModelResponse chunks with:
            - content: Text delta for this chunk (may be empty)
            - tool_calls: Tool calls when detected [{"name", "arguments"}]
            - metadata: {"is_stream": True} for chunks, {"final": True} for last
            - usage: Token counts (only on final chunk)

        Raises:
            RuntimeError: If the streaming request fails

        Example - Basic streaming:
            async for chunk in model.stream(messages):
                print(chunk.content, end="", flush=True)
            print()  # Final newline

        Example - With tool call detection:
            async for chunk in model.stream(messages, tools=tools):
                if chunk.tool_calls:
                    print(f"\\nTool call: {chunk.tool_calls}")
                else:
                    print(chunk.content, end="")

                if chunk.metadata.get("final"):
                    print(f"\\nTotal tokens: {chunk.usage.get('total_tokens')}")
        """
        # Validate model ID
        self._validate_model()
        start_time = time.perf_counter()

        # Convert messages to Gemini format
        formatted_messages, system_message = convert_messages_to_gemini_content(messages)

        # Build configuration
        config = self._build_config(
            temperature=temperature,
            max_tokens=max_tokens,
            system_message=system_message,
            tools=tools,
        )

        # Get client
        client = self._get_client()

        try:
            # Start streaming
            async_stream = await client.aio.models.generate_content_stream(
                model=self.model_id,
                contents=formatted_messages,
                config=config,
            )

            # Process each chunk from the stream
            async for chunk in async_stream:
                text = ""
                tool_calls: list[dict[str, Any]] = []

                # Extract content from chunk
                if chunk.candidates and len(chunk.candidates) > 0:
                    candidate = chunk.candidates[0]
                    candidate_content = candidate.content

                    # Get parts from the candidate
                    if candidate_content is not None and candidate_content.parts is not None:
                        for part in candidate_content.parts:
                            # Extract text
                            if hasattr(part, "text") and part.text is not None:
                                text += str(part.text)

                            # Extract function calls
                            # Generate unique ID for tracking through start/result events
                            if hasattr(part, "function_call") and part.function_call is not None:
                                tool_name = getattr(part.function_call, "name", "")
                                # Skip empty tool names - they cause issues
                                if not tool_name:
                                    continue

                                tool_call = {
                                    "id": f"call_{uuid.uuid4().hex[:8]}",  # Unique ID for tracking
                                    "name": tool_name,
                                    "arguments": dict(part.function_call.args or {})
                                    if hasattr(part.function_call, "args")
                                    and part.function_call.args is not None
                                    else {},
                                }
                                # Avoid duplicate tool calls (same name + args)
                                existing_calls = [
                                    (tc["name"], json.dumps(tc["arguments"], sort_keys=True))
                                    for tc in tool_calls
                                ]
                                new_call_key = (
                                    tool_call["name"],
                                    json.dumps(tool_call["arguments"], sort_keys=True),
                                )
                                if new_call_key not in existing_calls:
                                    tool_calls.append(tool_call)

                # Yield chunk if we have content
                # (some chunks might be empty, which is normal)
                if text or tool_calls:
                    yield ModelResponse(
                        content=text,
                        tool_calls=tool_calls if tool_calls else None,
                        metadata={"is_stream": True},
                    )

            # Yield final chunk with usage metadata
            usage_meta = getattr(async_stream, "usage_metadata", None)
            usage = parse_usage_metadata(usage_meta)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

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
            # Handle safety filter blocks
            if "output text or tool calls" in str(e):
                yield ModelResponse(
                    content="(Response blocked by safety filters)",
                    metadata={"blocked": True, "error": str(e)},
                )
                return
            raise RuntimeError(f"Gemini streaming failed: {e}") from e
