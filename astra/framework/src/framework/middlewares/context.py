"""
Middleware context passed to each middleware.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MiddlewareContext:
    """
    Context object passed to middlewares.

    Provides access to the agent instance and conversation context.

    Attributes:
        agent: Reference to the agent instance
        thread_id: Optional thread/conversation ID
        extra: Additional metadata dict for passing data between middlewares
    """

    agent: Any
    thread_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
