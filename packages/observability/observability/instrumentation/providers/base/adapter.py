from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable, Iterable, Iterator
from typing import Any

from observability.instrumentation.core.operations import OperationSpec
from observability.instrumentation.models.llm import LLMRequest, LLMResponse, TokenUsage
from observability.instrumentation.models.observation import Observation


class ProviderAdapter(ABC):
    name: str

    @abstractmethod
    def parse_request(
        self,
        operation: OperationSpec,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        truncate_limit: int,
    ) -> LLMRequest:
        raise NotImplementedError

    @abstractmethod
    def parse_response(
        self,
        operation: OperationSpec,
        response: Any,
        truncate_limit: int,
    ) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def build_request_attributes(
        self,
        operation: OperationSpec,
        request: LLMRequest,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_response_attributes(
        self,
        operation: OperationSpec,
        response: LLMResponse,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_usage_attributes(
        self,
        operation: OperationSpec,
        usage: TokenUsage | None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def to_observation(
        self,
        operation: OperationSpec,
        request: LLMRequest,
        response: LLMResponse,
        metadata: dict[str, Any],
    ) -> Observation | None:
        """
        Convert the normalized request/response to the Observation model.
        """
        raise NotImplementedError

    def instrument_stream(
        self,
        operation: OperationSpec,
        request: LLMRequest,
        response: Any,
        instrumentation_callback: Callable[[LLMResponse], None],
        truncate_limit: int,
    ) -> Any:
        """
        Instrument a streaming response.
        
        Args:
            operation: The operation being performed.
            request: The parsed request.
            response: The response returned by the LLM provider (e.g., iterator, dict).
            instrumentation_callback: Callback to execute when stream finishes.
                                      Receives the final LLMResponse.
            truncate_limit: Max chars to record.
            
        Returns:
            The response object to return to the user.
            This might be a generator, or a dict containing a wrapped generator.
        """
        # Default implementation assumes response is an iterator
        return self._wrap_iterator(operation, request, response, instrumentation_callback, truncate_limit)

    def _wrap_iterator(
        self,
        operation: OperationSpec,
        request: LLMRequest,
        iterator: Iterator[Any],
        instrumentation_callback: Callable[[LLMResponse], None],
        truncate_limit: int,
    ) -> Iterator[Any]:
        state = self.init_stream_state(operation, request)
        try:
            for chunk in iterator:
                self.accumulate_stream_chunk(operation, request, state, chunk)
                yield chunk
        finally:
            response_model, _ = self.finalize_stream(operation, state, truncate_limit, request)
            instrumentation_callback(response_model)

    def instrument_async_stream(
        self,
        operation: OperationSpec,
        request: LLMRequest,
        response: Any,
        instrumentation_callback: Callable[[LLMResponse], None],
        truncate_limit: int,
    ) -> Any:
        """
        Instrument an async streaming response.
        """
        return self._wrap_async_iterator(operation, request, response, instrumentation_callback, truncate_limit)

    async def _wrap_async_iterator(
        self,
        operation: OperationSpec,
        request: LLMRequest,
        iterator: AsyncIterator[Any],
        instrumentation_callback: Callable[[LLMResponse], None],
        truncate_limit: int,
    ) -> AsyncIterator[Any]:
        state = self.init_stream_state(operation, request)
        try:
            async for chunk in iterator:
                self.accumulate_stream_chunk(operation, request, state, chunk)
                yield chunk
        finally:
            response_model, _ = self.finalize_stream(operation, state, truncate_limit, request)
            instrumentation_callback(response_model)

    def init_stream_state(self, operation: OperationSpec, request: LLMRequest) -> dict[str, Any]:
        return {}

    def accumulate_stream_chunk(
        self,
        operation: OperationSpec,
        request: LLMRequest,
        state: dict[str, Any],
        chunk: Any,
    ) -> None:
        pass

    def finalize_stream(
        self,
        operation: OperationSpec,
        state: dict[str, Any],
        truncate_limit: int,
        request: LLMRequest | None = None,
    ) -> tuple[LLMResponse, Iterable[Any] | None]:
        response = LLMResponse()
        return response, None

    def calculate_cost(
        self,
        operation: OperationSpec,
        request: LLMRequest | None,
        response: LLMResponse | None,
    ) -> dict[str, Any]:
        """
        Calculate cost for the operation.
        """
        return {}
