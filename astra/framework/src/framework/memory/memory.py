"""
Memory module for Astra Framework.

Provides unified Memory class for conversation history management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from framework.storage.memory import AgentStorage


class Memory:
    """
    Unified memory class for conversation history management.

    Example:
        ```python
        agent = Agent(
            memory=Memory(num_history_responses=10),
            ...
        )
        ```
    """

    def __init__(
        self,
        *,
        add_history_to_messages: bool = True,
        num_history_responses: int = 5,
    ):
        """
        Initialize memory.

        Args:
            add_history_to_messages: Whether to add chat history to model messages
            num_history_responses: Number of recent conversation turns to keep
        """
        self.add_history_to_messages = add_history_to_messages
        self.num_history_responses = num_history_responses

    async def get_context(
        self,
        thread_id: str,
        storage: AgentStorage,
    ) -> list[dict[str, Any]]:
        """
        Get recent conversation context for the current turn.

        Args:
            thread_id: Thread ID to load context from
            storage: AgentStorage instance for storage access

        Returns:
            List of message dicts in format: [{"role": "user", "content": "..."}]
            Returns empty list if add_history_to_messages is False
        """
        if not self.add_history_to_messages:
            return []

        # Simple message limiting using num_history_responses
        # Load num_history_responses * 2 to account for user/assistant pairs
        message_limit = self.num_history_responses * 2

        # Load messages from storage
        recent_messages = await storage.get_history(thread_id, limit=message_limit)

        context = []
        for msg in recent_messages:
            msg_dict = storage._message_to_dict(msg)
            context.append(msg_dict)

        return context

    def __repr__(self) -> str:
        return (
            f"Memory(add_history={self.add_history_to_messages}, "
            f"num_responses={self.num_history_responses})"
        )
