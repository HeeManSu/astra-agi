"""
Remote HuggingFace model provider for Astra Framework.

This client connects to a remote HuggingFace model API server (see remote_model_server/main.py)
running on another machine (e.g., laptop with GPU).

Use Case:
- Run remote_model_server on laptop with GPU
- Use this client on your development machine (Mac)
- No need to install heavy ML dependencies on dev machine

Example:
    # On laptop: Run remote_model_server/main.py
    # On Mac:
    from framework.models.huggingface.remote import HuggingFaceRemote

    model = HuggingFaceRemote("http://192.168.1.100:8001")
    response = await model.invoke([{"role": "user", "content": "Hello!"}])
"""

from collections.abc import AsyncIterator
import json
import logging
from typing import Any

import httpx

from framework.models.base import Model, ModelResponse


logger = logging.getLogger(__name__)


class HuggingFaceRemote(Model):
    """
    Remote HuggingFace model provider that connects to a remote API server.

    The remote server should be running remote_model_server/main.py on another machine.

    Args:
        base_url: Base URL of the remote model server (e.g., "http://192.168.1.100:8001")
        timeout: Request timeout in seconds. Defaults to 300 (5 minutes) for model inference.
        **kwargs: Additional arguments (ignored, kept for compatibility)
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 300.0,
        **kwargs: Any,
    ):
        super().__init__(model_id=base_url, api_key="remote", **kwargs)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _format_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Convert Astra tool definitions to HuggingFace format.

        This ensures tools are properly formatted before sending to the remote server.
        The server will also format them, but this provides client-side validation.

        Astra format:
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": {...}
            }
        }

        HuggingFace format (for apply_chat_template):
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": {...}
            }
        }

        The formats are compatible, but we normalize for safety.
        """
        hf_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                hf_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": func.get("name", ""),
                            "description": func.get("description", ""),
                            "parameters": func.get("parameters", {}),
                        },
                    }
                )
            else:
                # Pass through other tool types
                hf_tools.append(tool)
        return hf_tools

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def _close_client(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def invoke(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """
        Invoke the remote model and return complete response.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            response_format: Optional response format specification
            **kwargs: Additional arguments passed to the remote server

        Returns:
            ModelResponse with content, tool_calls, usage, and metadata
        """
        client = self._get_client()

        hf_tools = self._format_tools(tools) if tools else None

        payload = {
            "messages": messages,
            "temperature": temperature,
        }

        if hf_tools:
            payload["tools"] = hf_tools
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if response_format:
            payload["response_format"] = response_format
        if kwargs:
            payload.update(kwargs)

        try:
            response = await client.post("/v1/invoke", json=payload)
            response.raise_for_status()

            data = response.json()
            return ModelResponse(
                content=data.get("content", ""),
                tool_calls=data.get("tool_calls"),
                usage=data.get("usage"),
                metadata={
                    **data.get("metadata", {}),
                    "provider": "huggingface-remote",
                    "base_url": self.base_url,
                },
            )
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"HTTP error from remote server: {error_detail}")
            raise RuntimeError(f"Remote model server error: {error_detail}") from e
        except httpx.RequestError as e:
            logger.error(f"Request error connecting to remote server: {e}")
            raise RuntimeError(
                f"Failed to connect to remote model server at {self.base_url}. "
                "Is the server running?"
            ) from e

    async def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ModelResponse]:
        """
        Stream responses from the remote model token by token.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            response_format: Optional response format specification
            **kwargs: Additional arguments passed to the remote server

        Yields:
            ModelResponse chunks with incremental content
        """
        client = self._get_client()

        hf_tools = self._format_tools(tools) if tools else None

        payload = {
            "messages": messages,
            "temperature": temperature,
        }

        if hf_tools:
            payload["tools"] = hf_tools
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if response_format:
            payload["response_format"] = response_format
        if kwargs:
            payload.update(kwargs)

        try:
            async with client.stream("POST", "/v1/stream", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # Parse SSE format: "data: {...}"
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        try:
                            data = json.loads(data_str)

                            # Check for error
                            if "error" in data:
                                raise RuntimeError(f"Remote server error: {data['error']}")

                            yield ModelResponse(
                                content=data.get("content", ""),
                                tool_calls=data.get("tool_calls"),
                                usage=data.get("usage"),
                                metadata={
                                    **data.get("metadata", {}),
                                    "provider": "huggingface-remote",
                                    "base_url": self.base_url,
                                },
                            )
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse SSE data: {data_str[:100]}...")
                            continue
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"HTTP error from remote server: {error_detail}")
            raise RuntimeError(f"Remote model server error: {error_detail}") from e
        except httpx.RequestError as e:
            logger.error(f"Request error connecting to remote server: {e}")
            raise RuntimeError(
                f"Failed to connect to remote model server at {self.base_url}. "
                "Is the server running?"
            ) from e

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client."""
        await self._close_client()

    def __del__(self):
        """Cleanup on deletion."""
        if self._client is not None:
            logger.warning(
                "HuggingFaceRemote client not properly closed. "
                "Use async context manager or call _close_client() explicitly."
            )
