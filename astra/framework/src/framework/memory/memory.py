"""
Memory module for Astra Framework.

Provides unified Memory class for conversation history management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from framework.storage.client import StorageClient


class Memory:
    """
    Unified memory class for conversation history management.

    Memory is responsible only for:
    - deciding *whether* history is included
    - deciding *how much* history is included

    It does NOT manage storage or persistence logic.

    Example:
        ```python
        agent = Agent(
            memory=Memory(num_history_turns=10),
            ...
        )
        ```
    """

    def __init__(
        self,
        *,
        add_history_to_messages: bool = True,
        num_history_turns: int = 5,
    ):
        """
        Initialize memory.

        Args:
            add_history_to_messages: Whether to include chat history in model input
            num_history_turns: Number of recent user-assistant turns to include
        """
        self.add_history_to_messages = add_history_to_messages
        self.num_history_turns = num_history_turns

    async def get_context(
        self,
        thread_id: str,
        storage: StorageClient,
    ) -> list[dict[str, Any]]:
        """
        Load recent conversation context.

        Args:
            thread_id: Thread identifier
            storage: Storage client implementation

        Returns:
            A list of message dictionaries ordered from oldest → newest.
            Returns an empty list if history is disabled.
        """
        if not self.add_history_to_messages:
            return []

        # Each turn = user + assistant
        message_limit = self.num_history_turns * 2

        return await storage.get_history_as_messages(
            thread_id,
            limit=message_limit,
        )

    def __repr__(self) -> str:
        return (
            f"Memory(add_history={self.add_history_to_messages}, "
            f"num_turns={self.num_history_turns})"
        )
