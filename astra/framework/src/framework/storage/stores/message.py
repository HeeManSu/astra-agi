"""
MessageStore - domain store for conversation messages.

Provides operations scoped to per-thread messages.
Database-agnostic implementation that works with any storage backend.
"""

import asyncio
from datetime import datetime, timezone

from framework.storage.base import StorageBackend
from framework.storage.models import Message
from framework.storage.stores.base import BaseStore


class MessageStore(BaseStore[Message]):
    """
    MessageStore manages astra_messages records.

    Methods:
    - get_recent(thread_id, limit) -> list[Message]
    - get_next_sequence(thread_id) -> int
    - bulk_add(messages) -> list[Message]
    - soft_delete(message_id) -> None

    Internally, messages are ordered by `sequence`.
    Automatically filters out soft-deleted records.
    """

    def __init__(self, storage: StorageBackend) -> None:
        super().__init__(storage=storage, model_cls=Message, collection_name="astra_messages")
        # Lock for thread-safe sequence generation
        self._sequence_lock = asyncio.Lock()

    async def get_recent(self, thread_id: str, limit: int) -> list[Message]:
        """
        Fetch the most recent N messages, ordered chronologically.

        Args:
            thread_id: Thread identifier
            limit: Number of recent messages to fetch

        Returns:
            List of Message objects in oldest to newest order
        """
        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict={"thread_id": thread_id},
            sort=[("sequence", -1)],  # -1 for descending
            limit=limit,
        )
        rows = await self.storage.fetch_all(query)
        # Reverse to get chronological order (oldest to newest)
        return [self._row_to_model(row) for row in reversed(rows)]

    async def add(self, message: Message) -> Message:
        """
        Add a single message to the store.

        Args:
            message: Message object to insert

        Returns:
            The inserted Message object
        """
        data = message.model_dump(exclude_unset=True)
        prepared_data = self._prepare_document(data)
        query = self.storage.build_insert_query(self.collection_name, prepared_data)
        await self.storage.execute(query)
        return message

    async def get_by_thread(self, thread_id: str, limit: int | None = None) -> list[Message]:
        """
        Get all messages for a thread, ordered by sequence.

        Args:
            thread_id: Thread identifier
            limit: Optional limit on number of messages

        Returns:
            List of Message objects in sequence order (oldest to newest)
        """
        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict={"thread_id": thread_id},
            sort=[("sequence", 1)],  # 1 for ascending
            limit=limit,
        )
        rows = await self.storage.fetch_all(query)
        return [self._row_to_model(row) for row in rows]

    async def soft_delete(self, message_id: str) -> None:
        """
        Soft delete a message by setting deleted_at timestamp.

        Args:
            message_id: Message identifier to soft delete
        """
        query = self.storage.build_update_query(
            collection=self.collection_name,
            filter_dict={
                "id": message_id,
                "deleted_at": None,
            },  # Only update if not already deleted
            update_data={"deleted_at": datetime.now(timezone.utc)},
        )
        await self.storage.execute(query)

    async def get_next_sequence(self, thread_id: str) -> int:
        """
        Get the next sequence number for a message in a thread.

        Uses storage.get_max_value() which handles database-specific logic.
        Thread-safe using asyncio lock.

        Args:
            thread_id: Thread identifier

        Returns:
            Next sequence number (starts at 1)
        """
        async with self._sequence_lock:
            max_seq = await self.storage.get_max_value(
                collection=self.collection_name,
                field="sequence",
                filter_dict={"thread_id": thread_id},
            )
            return max_seq + 1

    async def bulk_add(self, messages: list[Message]) -> list[Message]:
        """
        Bulk insert multiple messages in a single operation.

        This is more efficient than calling add() multiple times.

        Args:
            messages: List of Message objects to insert

        Returns:
            List of inserted Message objects
        """
        if not messages:
            return []

        # Prepare bulk insert data
        bulk_data = [msg.model_dump(exclude_unset=True) for msg in messages]
        prepared_data = [self._prepare_document(doc) for doc in bulk_data]
        query = self.storage.build_insert_many_query(self.collection_name, prepared_data)
        await self.storage.execute(query)
        return messages
