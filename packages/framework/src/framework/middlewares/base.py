"""
Base classes for middlewares.
"""

from abc import ABC, abstractmethod
from typing import Any

from framework.middlewares.context import MiddlewareContext


class InputMiddleware(ABC):
    """
    Base class for input middlewares.

    Input middlewares run before the LLM is called and can:
    - Validate input
    - Transform messages
    - Add context
    - Enforce rules
    """

    @abstractmethod
    async def process(
        self, messages: list[dict[str, Any]], context: MiddlewareContext
    ) -> list[dict[str, Any]]:
        """
        Process input messages before LLM call.

        Args:
            messages: List of message dicts with 'role' and 'content'
            context: Middleware context with agent and thread info

        Returns:
            Modified messages list
        """


class OutputMiddleware(ABC):
    """
    Base class for output middlewares.

    Output middlewares run after the LLM generates output and can:
    - Validate output
    - Apply guardrails
    - Moderate content
    - Format output
    """

    @abstractmethod
    async def process(self, response: Any, context: MiddlewareContext) -> Any:
        """
        Process final output after LLM call.

        Args:
            response: LLM output (usually a string or ModelResponse)
            context: Middleware context with agent and thread info

        Returns:
            Modified response
        """
