"""
Base model class for Astra Framework.
Provides abstract base class for all model providers.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class ModelResponse:
    """Standard unified model response wrapper"""

    def __init__(
        self,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        usage: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls or []
        self.usage = usage or {}
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "tool_calls": self.tool_calls,
            "usage": self.usage,
            "metadata": self.metadata,
        }


class Model(ABC):
    """
    Abstract base class for all model providers.
    """

    def __init__(self, model_id: str, api_key: str | None = None, **kwargs: Any):
        self.model_id = model_id
        self.api_key = api_key
        self._config = kwargs

        # Cached once. no repeated splitting
        module = self.__class__.__module__
        if "." in module:
            self.provider = module.split(".")[-1]
        else:
            self.provider = "unknown"

    @abstractmethod
    async def invoke(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Synchronous model invocation"""
        raise NotImplementedError

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ModelResponse]:
        """Streaming model invocation"""
        raise NotImplementedError

    def __repr__(self) -> str:
        api = self.api_key
        key_repr = f"****{api[-4:]}" if api and len(api) > 4 else None
        return f"{self.__class__.__name__}(id='{self.model_id}', provider='{self.provider}', key='{key_repr}')"
