"""
AWS Bedrock model implementation for Astra Framework.
Supports all Bedrock chat models via the AWS Bedrock Converse API.

All functionality is integrated into this single class with larger,
well-commented methods rather than many small utility functions.
"""

import base64
from collections.abc import AsyncIterator
import json
import os
import time
from typing import Any, ClassVar
from urllib.parse import quote

from dotenv import load_dotenv
import httpx

from framework.models.aws.bedrock_errors import (
    BedrockAPIError,
    BedrockAuthenticationError,
    parse_bedrock_error,
)
from framework.models.aws.bedrock_types import (
    BEDROCK_DEFAULT_REGION,
    BEDROCK_DOCUMENT_MIME_TYPES,
    BEDROCK_IMAGE_MIME_TYPES,
    BEDROCK_SUPPORTED_MODELS,
)
from framework.models.base import Model, ModelResponse


load_dotenv()

# aioboto3 for async SigV4 signing
try:
    import aioboto3  # type: ignore[import-untyped]  # noqa: F401
    from botocore.auth import SigV4Auth  # type: ignore[import-untyped]
    from botocore.awsrequest import AWSRequest  # type: ignore[import-untyped]
    from botocore.credentials import Credentials  # type: ignore[import-untyped]

    AIOBOTO3_AVAILABLE = True
except ImportError:
    AIOBOTO3_AVAILABLE = False
    # Type stubs for when aioboto3 is not available
    SigV4Auth = None  # type: ignore[assignment,misc]
    AWSRequest = None  # type: ignore[assignment,misc]
    Credentials = None  # type: ignore[assignment,misc]


class Bedrock(Model):
    """
    AWS Bedrock model provider for Astra.

    Supports multiple authentication methods:
    - AWS SigV4 (default, using AWS credentials)
    - Bearer token (using AWS_BEARER_TOKEN_BEDROCK)

    Supports all Bedrock chat models including:
    - Anthropic (Claude models)
    - Meta (Llama models)
    - Mistral models
    - Cohere models
    - Amazon Nova models

    Example:
        model = Bedrock("anthropic.claude-sonnet-4-5-20250929-v1:0")
        response = await model.invoke([{"role": "user", "content": "Hello!"}])
    """

    AVAILABLE_MODELS: ClassVar[set[str]] = BEDROCK_SUPPORTED_MODELS

    def __init__(
        self,
        model_id: str,
        api_key: str | None = None,
        aws_region: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize Bedrock model.

        Args:
            model_id: Bedrock model identifier (e.g., "anthropic.claude-sonnet-4-5-20250929-v1:0")
            api_key: Optional Bearer token (alternative to SigV4, takes precedence)
            aws_region: AWS region (defaults to AWS_REGION env var)
            aws_access_key_id: AWS access key (defaults to AWS_ACCESS_KEY_ID env var)
            aws_secret_access_key: AWS secret key (defaults to AWS_SECRET_ACCESS_KEY env var)
            aws_session_token: AWS session token (optional, defaults to AWS_SESSION_TOKEN env var)
            base_url: Custom base URL (optional, defaults to bedrock-runtime.{region}.amazonaws.com)
        """
        super().__init__(model_id=model_id, api_key=api_key, **kwargs)

        # Load credentials from environment or constructor args
        # Bearer token takes precedence if provided
        self.api_key = api_key or os.getenv("AWS_BEARER_TOKEN_BEDROCK")
        self.aws_region = aws_region or os.getenv("AWS_REGION") or BEDROCK_DEFAULT_REGION
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_session_token = aws_session_token or os.getenv("AWS_SESSION_TOKEN")
        self.base_url = base_url

        # Request parameters (can be overridden per request)
        self.max_tokens = kwargs.get("max_tokens")
        self.temperature = kwargs.get("temperature")
        self.top_p = kwargs.get("top_p")
        self.top_k = kwargs.get("top_k")
        self.stop_sequences = kwargs.get("stop_sequences")

        # Internal HTTP client (lazy initialization)
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client for making requests.

        Returns:
            httpx.AsyncClient instance
        """
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    def _get_base_url(self) -> str:
        """
        Build base URL for Bedrock API from region.

        Returns:
            Base URL string (e.g., "https://bedrock-runtime.us-east-1.amazonaws.com")
        """
        if self.base_url:
            return self.base_url.rstrip("/")
        return f"https://bedrock-runtime.{self.aws_region}.amazonaws.com"

    async def _sign_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | str,
    ) -> dict[str, str]:
        """
        Sign request with AWS SigV4 or add Bearer token.

        Authentication logic is integrated here - no separate auth handler class.
        Bearer token takes precedence if provided, otherwise uses SigV4.

        All authentication logic in one place with detailed comments explaining:
        - How Bearer token authentication works (simple Authorization header)
        - How SigV4 signing works (AWS signature version 4)
        - Credential loading and validation
        - Header construction

        Args:
            method: HTTP method (should be "POST" for Bedrock)
            url: Full request URL
            headers: Request headers dictionary
            body: Request body as bytes or string

        Returns:
            Updated headers dictionary with authentication

        Raises:
            BedrockAuthenticationError: If credentials are missing or invalid
        """
        # Step 1: Check for Bearer token first (takes precedence)
        # Bearer token authentication is simpler - just add Authorization header
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            return headers

        # Step 2: Use SigV4 signing (requires AWS credentials)
        # SigV4 is AWS's signature version 4 authentication protocol
        # It requires: access key ID, secret access key, region, and service name
        if not AIOBOTO3_AVAILABLE:
            raise BedrockAuthenticationError(
                "aioboto3 is required for SigV4 authentication. Install using: pip install aioboto3"
            )

        # Validate that we have required credentials for SigV4
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise BedrockAuthenticationError(
                "AWS credentials required for SigV4 authentication. "
                "Provide aws_access_key_id and aws_secret_access_key, "
                "or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables, "
                "or use Bearer token authentication with AWS_BEARER_TOKEN_BEDROCK."
            )

        # Step 3: Create AWS credentials object
        # Credentials object is used by botocore's SigV4Auth signer
        if Credentials is None:
            raise BedrockAuthenticationError("botocore.Credentials not available")
        credentials = Credentials(
            access_key=self.aws_access_key_id,
            secret_key=self.aws_secret_access_key,
            token=self.aws_session_token,
        )

        # Step 4: Create AWS request object
        # AWSRequest is botocore's request object that SigV4Auth can sign
        # We need to convert our httpx-style request to AWS format
        if AWSRequest is None:
            raise BedrockAuthenticationError("botocore.AWSRequest not available")
        body_bytes = body if isinstance(body, bytes) else body.encode("utf-8")

        aws_request = AWSRequest(
            method=method,
            url=url,
            data=body_bytes,
            headers=headers,
        )

        # Step 5: Sign the request with SigV4
        # SigV4Auth signs the request by adding Authorization header with signature
        # The signature is computed from: method, URL, headers, body, credentials, region, service
        if SigV4Auth is None:
            raise BedrockAuthenticationError("botocore.SigV4Auth not available")
        signer = SigV4Auth(credentials, "bedrock", self.aws_region)
        signer.add_auth(aws_request)

        # Step 6: Return signed headers
        # The AWSRequest object now has the signed headers
        return dict(aws_request.headers)

    async def _prepare_messages_and_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]] | None, dict[str, Any] | None]:
        """
        Comprehensive method that prepares both messages and tools for Bedrock API.

        This single method handles:
        - Converting Astra messages to Bedrock format (all message types)
        - Extracting and formatting system messages
        - Handling user messages with text, images, documents
        - Handling assistant messages with text and tool calls
        - Handling tool result messages
        - Formatting tools to Bedrock toolSpec format
        - Handling tool choice configuration

        Args:
            messages: List of Astra framework messages (dicts with role and content)
            tools: Optional list of tool definitions (dicts with name, description, parameters)
            tool_choice: Optional tool choice configuration (string or dict)

        Returns:
            Tuple of (bedrock_messages, system_messages, tool_config)
            - bedrock_messages: List of Bedrock-formatted messages
            - system_messages: List of system message content blocks (or None)
            - tool_config: Tool configuration dict (or None)
        """
        bedrock_messages: list[dict[str, Any]] = []
        system_blocks: list[dict[str, Any]] = []
        tool_config: dict[str, Any] | None = None

        # Process each message and convert to Bedrock format
        # Bedrock expects messages in a specific format:
        # - System messages go in separate 'system' array with content blocks
        # - User/assistant messages have 'role' and 'content' array
        # - Content blocks can be: text, image, document, toolResult, toolUse
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            # Step 1: Handle system messages
            # System messages are extracted separately and sent in 'system' field
            # Bedrock supports multiple system content blocks
            if role == "system":
                # System messages are simple text blocks
                system_blocks.append(
                    {"text": content if isinstance(content, str) else str(content)}
                )
                continue

            # Step 2: Handle user messages
            # User messages can contain: text, images, documents
            # Content can be a string or a list of content parts
            if role == "user":
                user_content: list[dict[str, Any]] = []

                # Handle string content (simple text)
                if isinstance(content, str):
                    user_content.append({"text": content})
                # Handle list content (multimodal)
                elif isinstance(content, list):
                    for part in content:
                        # Text part
                        if isinstance(part, str):
                            user_content.append({"text": part})
                        # Dict part (could be image, document, etc.)
                        elif isinstance(part, dict):
                            part_type = part.get("type")
                            # Image part
                            if part_type == "image" or "image" in part:
                                image_data = part.get("image") or part.get("data")
                                image_mime = (
                                    part.get("mime_type") or part.get("mediaType") or "image/png"
                                )
                                # Convert image to base64 if needed
                                if isinstance(image_data, str):
                                    # Assume base64 if it's a string
                                    image_bytes = (
                                        base64.b64decode(image_data)
                                        if not image_data.startswith("data:")
                                        else base64.b64decode(image_data.split(",")[1])
                                    )
                                else:
                                    image_bytes = image_data
                                # Ensure image_bytes is bytes
                                if not isinstance(image_bytes, bytes):
                                    raise ValueError("Image data must be bytes or base64 string")
                                # Type assertion for type checker
                                assert isinstance(image_bytes, bytes), "image_bytes must be bytes"
                                # Get format from MIME type
                                image_format = BEDROCK_IMAGE_MIME_TYPES.get(image_mime, "png")
                                user_content.append(
                                    {
                                        "image": {
                                            "format": image_format,
                                            "source": {
                                                "bytes": base64.b64encode(image_bytes).decode(
                                                    "utf-8"
                                                )
                                            },
                                        }
                                    }
                                )
                            # Document part
                            elif part_type == "file" or "file" in part or "document" in part:
                                file_data = (
                                    part.get("file") or part.get("data") or part.get("document")
                                )
                                file_mime = (
                                    part.get("mime_type")
                                    or part.get("mediaType")
                                    or "application/pdf"
                                )
                                file_name = part.get("name") or part.get("filename") or "document"
                                # Convert document to base64 if needed
                                if isinstance(file_data, str):
                                    doc_bytes = (
                                        base64.b64decode(file_data)
                                        if not file_data.startswith("data:")
                                        else base64.b64decode(file_data.split(",")[1])
                                    )
                                else:
                                    doc_bytes = file_data
                                # Ensure doc_bytes is bytes
                                if not isinstance(doc_bytes, bytes):
                                    raise ValueError("Document data must be bytes or base64 string")
                                # Type assertion for type checker
                                assert isinstance(doc_bytes, bytes), "doc_bytes must be bytes"
                                # Get format from MIME type
                                doc_format = BEDROCK_DOCUMENT_MIME_TYPES.get(file_mime, "pdf")
                                user_content.append(
                                    {
                                        "document": {
                                            "format": doc_format,
                                            "name": file_name,
                                            "source": {
                                                "bytes": base64.b64encode(doc_bytes).decode("utf-8")
                                            },
                                        }
                                    }
                                )
                            # Text part in dict format
                            else:
                                text_content = part.get("text") or str(part)
                                user_content.append({"text": text_content})
                else:
                    # Fallback: convert to string
                    user_content.append({"text": str(content)})

                if user_content:
                    bedrock_messages.append({"role": "user", "content": user_content})

            # Step 3: Handle assistant messages
            # Assistant messages can contain: text, tool calls
            elif role == "assistant":
                assistant_content: list[dict[str, Any]] = []

                # Handle string content
                if isinstance(content, str) and content:
                    assistant_content.append({"text": content})

                # Handle tool calls
                # Tool calls are stored in message.tool_calls
                # Support both formats:
                # 1. OpenAI format: {"id": "...", "function": {"name": "...", "arguments": "..."}}
                # 2. Simplified format: {"id": "...", "name": "...", "arguments": {...}}
                tool_calls = message.get("tool_calls", [])
                if tool_calls:
                    for tool_call in tool_calls:
                        # Extract tool ID (required for Bedrock)
                        tool_id = tool_call.get("id") or tool_call.get("tool_call_id")

                        # Handle both OpenAI format and simplified format
                        if "function" in tool_call:
                            # OpenAI format: {"id": "...", "function": {"name": "...", "arguments": "..."}}
                            func = tool_call.get("function", {})
                            tool_name = func.get("name")
                            tool_args_str = func.get("arguments", "{}")

                            # Parse arguments (should be JSON string in OpenAI format)
                            try:
                                tool_args = (
                                    json.loads(tool_args_str)
                                    if isinstance(tool_args_str, str)
                                    else tool_args_str
                                )
                            except json.JSONDecodeError:
                                tool_args = {}
                        else:
                            # Simplified format: {"id": "...", "name": "...", "arguments": {...}}
                            tool_name = tool_call.get("name")
                            tool_args = tool_call.get("arguments", {})
                            # Arguments might already be a dict, or could be a string
                            if isinstance(tool_args, str):
                                try:
                                    tool_args = json.loads(tool_args)
                                except json.JSONDecodeError:
                                    tool_args = {}

                        # Only add tool use if we have both ID and name
                        if tool_name and tool_id:
                            assistant_content.append(
                                {
                                    "toolUse": {
                                        "toolUseId": tool_id,
                                        "name": tool_name,
                                        "input": tool_args,
                                    }
                                }
                            )

                if assistant_content:
                    bedrock_messages.append({"role": "assistant", "content": assistant_content})

            # Step 4: Handle tool result messages
            # Tool results are responses from tool calls
            # Format: {"role": "tool", "content": "...", "tool_call_id": "..."}
            elif role == "tool":
                tool_call_id = message.get("tool_call_id") or message.get("toolCallId")
                tool_content = content if isinstance(content, str) else str(content)

                # Try to parse tool content as JSON if it's a string
                try:
                    tool_result = (
                        json.loads(tool_content) if isinstance(tool_content, str) else tool_content
                    )
                except json.JSONDecodeError:
                    # If not JSON, wrap in a result object
                    tool_result = {"result": tool_content}

                # Tool results are sent as user messages with toolResult content blocks
                if tool_call_id:
                    bedrock_messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "toolResult": {
                                        "toolUseId": tool_call_id,
                                        "content": [{"json": tool_result}],
                                    }
                                }
                            ],
                        }
                    )

        # Step 5: Format tools if provided
        # Bedrock expects tools in toolSpec format:
        # {
        #   "toolSpec": {
        #     "name": "...",
        #     "description": "...",
        #     "inputSchema": {"json": {...}}  # JSON Schema
        #   }
        # }
        if tools:
            bedrock_tools: list[dict[str, Any]] = []

            for tool in tools:
                # Extract tool information
                # Tools can be in OpenAI format: {"type": "function", "function": {...}}
                # Or direct format: {"name": "...", "description": "...", "parameters": {...}}
                if tool.get("type") == "function":
                    func = tool.get("function", {})
                    tool_name = func.get("name", "")
                    tool_description = func.get("description", "")
                    tool_parameters = func.get("parameters", {})
                else:
                    tool_name = tool.get("name", "")
                    tool_description = tool.get("description", "")
                    tool_parameters = tool.get("parameters", {})

                if not tool_name:
                    continue

                # Format parameters (JSON Schema)
                # Bedrock expects inputSchema with json field containing the schema
                input_schema = (
                    tool_parameters.copy()
                    if tool_parameters
                    else {"type": "object", "properties": {}}
                )

                # Ensure required field exists
                if "required" not in input_schema:
                    input_schema["required"] = []

                # Build tool spec
                tool_spec: dict[str, Any] = {
                    "toolSpec": {
                        "name": tool_name,
                        "inputSchema": {"json": input_schema},
                    }
                }

                # Add description if provided
                if tool_description:
                    tool_spec["toolSpec"]["description"] = tool_description

                bedrock_tools.append(tool_spec)

            # Build tool configuration
            tool_config = {"tools": bedrock_tools}

            # Handle tool choice
            # Bedrock supports: "auto", {"tool": {"name": "..."}}, {"any": {}}
            if tool_choice:
                if isinstance(tool_choice, str):
                    if tool_choice == "auto":
                        tool_config["toolChoice"] = {"auto": {}}
                    elif tool_choice == "required":
                        # If required but no specific tool, use "any"
                        tool_config["toolChoice"] = {"any": {}}
                elif isinstance(tool_choice, dict):
                    # Direct tool choice dict
                    tool_config["toolChoice"] = tool_choice

        # Return system messages (None if empty) and tool config (None if no tools)
        system_messages = system_blocks if system_blocks else None
        return bedrock_messages, system_messages, tool_config

    def _parse_response(self, response: dict[str, Any]) -> ModelResponse:
        """
        Parse non-streaming response from Bedrock API.

        Comprehensive response parser - handles all response types:
        - Text content extraction
        - Tool call extraction
        - Usage metrics extraction
        - Finish reason extraction

        Args:
            response: Response dictionary from Bedrock API

        Returns:
            ModelResponse with content, tool_calls, usage, and metadata
        """
        # Extract output message
        output = response.get("output", {})
        message = output.get("message", {})
        content_blocks = message.get("content", [])

        # Parse content blocks
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in content_blocks:
            # Text block
            if "text" in block:
                text_parts.append(block["text"])

            # Tool use block
            if "toolUse" in block:
                tool_use = block["toolUse"]
                # Agent expects arguments as a dict, not JSON string
                tool_input = tool_use.get("input", {})
                if isinstance(tool_input, str):
                    # If input is a string, try to parse as JSON
                    try:
                        tool_input = json.loads(tool_input)
                    except json.JSONDecodeError:
                        tool_input = {}
                # Include toolUseId as "id" so agent can match tool results back to calls
                tool_calls.append(
                    {
                        "id": tool_use.get("toolUseId", ""),  # Preserve ID for tool result matching
                        "name": tool_use.get("name", ""),
                        "arguments": tool_input,  # Return as dict, not JSON string
                    }
                )

        # Combine text parts
        content = "".join(text_parts)

        # Extract usage metrics
        usage: dict[str, Any] = {}
        response_usage = response.get("usage", {})
        if response_usage:
            usage["input_tokens"] = response_usage.get("inputTokens", 0)
            usage["output_tokens"] = response_usage.get("outputTokens", 0)
            usage["total_tokens"] = response_usage.get("totalTokens", 0)

        # Extract finish reason
        stop_reason = response.get("stopReason", "stop")

        # Build metadata
        metadata: dict[str, Any] = {
            "provider": "bedrock",
            "model_id": self.model_id,
            "finish_reason": stop_reason,
            "has_tool_calls": bool(tool_calls),
        }

        # Add metrics if available
        metrics = response.get("metrics", {})
        if metrics:
            metadata["latency_ms"] = metrics.get("latencyMs")

        return ModelResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            usage=usage,
            metadata=metadata,
        )

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
        Invoke Bedrock model for non-streaming response.

        This method orchestrates the entire flow:
        1. Validate model_id (inline check)
        2. Prepare messages and tools (calls _prepare_messages_and_tools - handles everything)
        3. Build inference config (inline - maxTokens, temperature, topP, topK, stopSequences)
        4. Build request body (inline - combines system, messages, toolConfig, inferenceConfig)
        5. Sign request (calls _sign_request - handles SigV4 or Bearer token)
        6. Make HTTP POST request to /model/{modelId}/converse
        7. Parse response (calls _parse_response - extracts content, tool_calls, usage, finish reason)
        8. Return ModelResponse

        Args:
            messages: List of messages (dicts with role and content)
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            response_format: Optional response format (not fully supported by Bedrock)
            **kwargs: Additional parameters (top_p, top_k, stop_sequences, etc.)

        Returns:
            ModelResponse with content, tool_calls, usage, and metadata

        Raises:
            BedrockError: If request fails or response is invalid
        """
        start_time = time.perf_counter()

        # Step 1: Validate model_id (optional - allow custom model IDs)
        # Bedrock supports custom model IDs, so we just log a warning
        if self.model_id not in self.AVAILABLE_MODELS:
            # Don't fail - custom model IDs are valid in Bedrock
            pass

        # Step 2: Prepare messages and tools
        # This comprehensive method handles all message conversion and tool formatting
        bedrock_messages, system_messages, tool_config = await self._prepare_messages_and_tools(
            messages, tools, kwargs.get("tool_choice")
        )

        # Step 3: Build inference configuration
        # Bedrock inference config includes: maxTokens, temperature, topP, topK, stopSequences
        # Only include parameters that are not None to avoid API errors
        inference_config: dict[str, Any] = {}

        # Use request-level parameters or fall back to instance-level
        max_tokens = max_tokens or self.max_tokens
        if max_tokens:
            inference_config["maxTokens"] = max_tokens

        temp = kwargs.get("temperature", temperature) or self.temperature
        if temp is not None:
            inference_config["temperature"] = float(temp)

        top_p = kwargs.get("top_p") or self.top_p
        if top_p is not None:
            inference_config["topP"] = float(top_p)

        top_k = kwargs.get("top_k") or self.top_k
        if top_k is not None:
            inference_config["topK"] = int(top_k)

        stop_sequences = kwargs.get("stop_sequences") or self.stop_sequences
        if stop_sequences:
            inference_config["stopSequences"] = stop_sequences

        # Step 4: Build request body
        # Bedrock Converse API expects:
        # {
        #   "system": [...],  # Optional system messages
        #   "messages": [...],  # Required conversation messages
        #   "toolConfig": {...},  # Optional tool configuration
        #   "inferenceConfig": {...},  # Optional inference parameters
        #   "additionalModelRequestFields": {...}  # Optional model-specific fields
        # }
        request_body: dict[str, Any] = {
            "messages": bedrock_messages,
        }

        if system_messages:
            request_body["system"] = system_messages

        if tool_config:
            request_body["toolConfig"] = tool_config

        if inference_config:
            request_body["inferenceConfig"] = inference_config

        # Add any additional model request fields from kwargs
        additional_fields = kwargs.get("additionalModelRequestFields")
        if additional_fields:
            request_body["additionalModelRequestFields"] = additional_fields

        # Step 5: Build request URL and headers
        base_url = self._get_base_url()
        # URL-encode model ID (Bedrock model IDs can contain special characters like colons)
        model_id_encoded = quote(self.model_id, safe="")
        url = f"{base_url}/model/{model_id_encoded}/converse"

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Step 6: Sign request (SigV4 or Bearer token)
        # This integrated method handles all authentication
        body_json = json.dumps(request_body)
        signed_headers = await self._sign_request("POST", url, headers, body_json)

        # Step 7: Make HTTP POST request
        client = self._get_client()
        try:
            response = await client.post(
                url,
                headers=signed_headers,
                content=body_json,
            )
            response.raise_for_status()
            response_data = response.json()
        except httpx.HTTPStatusError as e:
            # Parse error response
            try:
                error_data = e.response.json()
                raise parse_bedrock_error(error_data) from e
            except (ValueError, json.JSONDecodeError):
                raise BedrockAPIError(
                    f"HTTP {e.response.status_code}: {e.response.text}",
                    status_code=e.response.status_code,
                ) from e
        except httpx.RequestError as e:
            raise BedrockAPIError(f"Request failed: {e!s}") from e

        # Step 8: Parse response
        # This comprehensive parser extracts all response data
        model_response = self._parse_response(response_data)

        # Add latency to metadata
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        model_response.metadata["latency_ms"] = latency_ms

        return model_response

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
        Stream Bedrock model responses.

        This method orchestrates the streaming flow:
        1. Validate model_id (inline check)
        2. Prepare messages and tools (calls _prepare_messages_and_tools)
        3. Build inference config (inline)
        4. Build request body (inline)
        5. Sign request (calls _sign_request)
        6. Make HTTP POST request to /model/{modelId}/converse-stream
        7. Stream response chunks (SSE parsing inline with detailed comments)
        8. Parse each chunk incrementally:
           - contentBlockStart → emit text-start or tool-input-start
           - contentBlockDelta → emit text-delta, accumulate tool input, handle reasoning
           - contentBlockStop → emit text-end or tool-call
           - metadata → extract usage metrics
           - messageStop → extract finish reason
        9. Yield ModelResponse for each chunk
        10. Yield final chunk with usage and finish reason

        Args:
            messages: List of messages (dicts with role and content)
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            response_format: Optional response format (not fully supported by Bedrock)
            **kwargs: Additional parameters

        Yields:
            ModelResponse chunks with incremental content

        Raises:
            BedrockError: If request fails or streaming fails
        """
        start_time = time.perf_counter()

        # Steps 1-5: Same preparation as invoke()
        # Prepare messages and tools
        bedrock_messages, system_messages, tool_config = await self._prepare_messages_and_tools(
            messages, tools, kwargs.get("tool_choice")
        )

        # Build inference config
        inference_config: dict[str, Any] = {}
        max_tokens = max_tokens or self.max_tokens
        if max_tokens:
            inference_config["maxTokens"] = max_tokens

        temp = kwargs.get("temperature", temperature) or self.temperature
        if temp is not None:
            inference_config["temperature"] = float(temp)

        top_p = kwargs.get("top_p") or self.top_p
        if top_p is not None:
            inference_config["topP"] = float(top_p)

        top_k = kwargs.get("top_k") or self.top_k
        if top_k is not None:
            inference_config["topK"] = int(top_k)

        stop_sequences = kwargs.get("stop_sequences") or self.stop_sequences
        if stop_sequences:
            inference_config["stopSequences"] = stop_sequences

        # Build request body
        request_body: dict[str, Any] = {"messages": bedrock_messages}
        if system_messages:
            request_body["system"] = system_messages
        if tool_config:
            request_body["toolConfig"] = tool_config
        if inference_config:
            request_body["inferenceConfig"] = inference_config

        additional_fields = kwargs.get("additionalModelRequestFields")
        if additional_fields:
            request_body["additionalModelRequestFields"] = additional_fields

        # Build URL and headers
        base_url = self._get_base_url()
        # URL-encode model ID (Bedrock model IDs can contain special characters like colons)
        model_id_encoded = quote(self.model_id, safe="")
        url = f"{base_url}/model/{model_id_encoded}/converse-stream"

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/x-ndjson",  # Bedrock uses newline-delimited JSON for streaming
        }

        # Sign request
        body_json = json.dumps(request_body)
        signed_headers = await self._sign_request("POST", url, headers, body_json)

        # Step 6: Make streaming request
        # Bedrock uses Server-Sent Events (SSE) format with newline-delimited JSON
        client = self._get_client()

        # Track state across chunks
        current_tool: dict[str, Any] = {}  # Track tool being built
        usage: dict[str, Any] | None = None
        finish_reason: str | None = None
        content_blocks: dict[int, dict[str, Any]] = {}  # Track content blocks by index

        try:
            async with client.stream(
                "POST",
                url,
                headers=signed_headers,
                content=body_json,
            ) as response:
                response.raise_for_status()

                # Step 7-9: Parse chunks incrementally
                # Bedrock streams newline-delimited JSON chunks
                # Each chunk can contain multiple event types
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Handle contentBlockStart event
                    # This indicates the start of a new content block (text or tool)
                    if "contentBlockStart" in chunk:
                        start_data = chunk["contentBlockStart"]
                        block_index = start_data.get("contentBlockIndex", 0)
                        start_info = start_data.get("start", {})

                        # Check if it's a tool use start
                        if "toolUse" in start_info:
                            tool_use = start_info["toolUse"]
                            current_tool = {
                                "id": tool_use.get("toolUseId", ""),
                                "name": tool_use.get("name", ""),
                                "arguments": "",
                            }
                            content_blocks[block_index] = {"type": "tool", "tool": current_tool}
                        else:
                            # Text block start
                            content_blocks[block_index] = {"type": "text", "text": ""}
                            yield ModelResponse(
                                content="",
                                metadata={
                                    "is_stream": True,
                                    "block_index": block_index,
                                    "event": "text-start",
                                },
                            )

                    # Handle contentBlockDelta event
                    # This provides incremental content (text delta, tool input delta, reasoning)
                    elif "contentBlockDelta" in chunk:
                        delta_data = chunk["contentBlockDelta"]
                        block_index = delta_data.get("contentBlockIndex", 0)
                        delta = delta_data.get("delta", {})

                        # Text delta
                        if "text" in delta:
                            text_delta = delta["text"]
                            if block_index in content_blocks:
                                content_blocks[block_index]["text"] = (
                                    content_blocks[block_index].get("text", "") + text_delta
                                )
                            yield ModelResponse(
                                content=text_delta,
                                metadata={
                                    "is_stream": True,
                                    "block_index": block_index,
                                    "event": "text-delta",
                                },
                            )

                        # Tool use delta (accumulating tool input)
                        elif "toolUse" in delta:
                            tool_delta = delta["toolUse"]
                            tool_input_delta = tool_delta.get("input", "")
                            # Ensure tool_input_delta is a string for accumulation
                            if not isinstance(tool_input_delta, str):
                                tool_input_delta = str(tool_input_delta) if tool_input_delta else ""
                            if current_tool:
                                current_tool["arguments"] += tool_input_delta

                        # Reasoning content delta
                        elif "reasoningContent" in delta:
                            reasoning = delta["reasoningContent"]
                            reasoning_text = reasoning.get("text", "")
                            yield ModelResponse(
                                content=reasoning_text,
                                metadata={"is_stream": True, "event": "reasoning-delta"},
                            )

                    # Handle contentBlockStop event
                    # This indicates the end of a content block
                    elif "contentBlockStop" in chunk:
                        stop_data = chunk["contentBlockStop"]
                        block_index = stop_data.get("contentBlockIndex", 0)

                        if block_index in content_blocks:
                            block = content_blocks[block_index]
                            if block.get("type") == "tool" and current_tool:
                                # Tool call complete
                                try:
                                    tool_args = (
                                        json.loads(current_tool["arguments"])
                                        if current_tool["arguments"]
                                        else {}
                                    )
                                except json.JSONDecodeError:
                                    tool_args = {}

                                yield ModelResponse(
                                    content="",
                                    tool_calls=[
                                        {
                                            "name": current_tool["name"],
                                            "arguments": tool_args,  # Return as dict, not JSON string
                                        }
                                    ],
                                    metadata={"is_stream": True, "event": "tool-call"},
                                )
                                current_tool = {}
                            else:
                                # Text block end
                                yield ModelResponse(
                                    content="",
                                    metadata={
                                        "is_stream": True,
                                        "block_index": block_index,
                                        "event": "text-end",
                                    },
                                )

                            del content_blocks[block_index]

                    # Handle metadata event (usage information)
                    elif "metadata" in chunk:
                        metadata_data = chunk["metadata"]
                        if "usage" in metadata_data:
                            usage_data = metadata_data["usage"]
                            usage = {
                                "input_tokens": usage_data.get("inputTokens", 0),
                                "output_tokens": usage_data.get("outputTokens", 0),
                                "total_tokens": usage_data.get("inputTokens", 0)
                                + usage_data.get("outputTokens", 0),
                            }

                    # Handle messageStop event (final message with finish reason)
                    elif "messageStop" in chunk:
                        stop_data = chunk["messageStop"]
                        finish_reason = stop_data.get("stopReason", "stop")

        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                raise parse_bedrock_error(error_data) from e
            except (ValueError, json.JSONDecodeError):
                raise BedrockAPIError(
                    f"HTTP {e.response.status_code}: {e.response.text}",
                    status_code=e.response.status_code,
                ) from e
        except httpx.RequestError as e:
            raise BedrockAPIError(f"Streaming request failed: {e!s}") from e

        # Step 10: Yield final chunk with usage and finish reason
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        yield ModelResponse(
            content="",
            usage=usage or {},
            metadata={
                "provider": "bedrock",
                "model_id": self.model_id,
                "finish_reason": finish_reason or "stop",
                "latency_ms": latency_ms,
                "final": True,
            },
        )
