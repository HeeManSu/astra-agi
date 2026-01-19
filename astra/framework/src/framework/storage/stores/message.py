"""
MessageStore - domain store for conversation messages.

Provides operations scoped to per-thread messages.
Database-agnostic implementation that works with any storage backend.
"""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from framework.storage.base import StorageBackend
from framework.storage.databases.mongodb import MongoDBStorage
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
        self._sequence_lock = asyncio.Lock()

    def _get_id_field(self) -> str:
        """Return the ID field name based on storage backend."""
        if isinstance(self._storage, MongoDBStorage):
            return "_id"
        return "id"

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
            sort=[("sequence", -1)],
            limit=limit,
        )
        rows = await self.storage.fetch_all(query)
        return [self._row_to_model(row) for row in reversed(rows)]

    async def add(self, message: Message) -> Message:
        """
        Add a single message to the store.

        Args:
            message: Message object to insert

        Returns:
            The inserted Message object with id populated
        """
        data = message.model_dump(exclude_unset=True)

        # For SQL backends, generate id if not provided
        if not isinstance(self._storage, MongoDBStorage):
            if "id" not in data or data.get("id") is None:
                data["id"] = f"msg-{uuid4().hex[:12]}"

        prepared_data = self._prepare_document(data)
        result = await self.storage.execute(
            self.storage.build_insert_query(self.collection_name, prepared_data)
        )

        # For MongoDB, get the inserted _id
        if isinstance(self._storage, MongoDBStorage) and result:
            data["id"] = str(result.inserted_id)

        return Message(**data)

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
            sort=[("sequence", 1)],
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
        id_field = self._get_id_field()

        if isinstance(self._storage, MongoDBStorage):
            from bson import ObjectId

            try:
                filter_dict = {id_field: ObjectId(message_id), "deleted_at": None}
            except Exception:
                filter_dict = {id_field: message_id, "deleted_at": None}
        else:
            filter_dict = {id_field: message_id, "deleted_at": None}

        query = self.storage.build_update_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
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

        Args:
            messages: List of Message objects to insert

        Returns:
            List of inserted Message objects with ids populated
        """
        if not messages:
            return []

        bulk_data = []
        for msg in messages:
            data = msg.model_dump(exclude_unset=True)

            # For SQL backends, generate id if not provided
            if not isinstance(self._storage, MongoDBStorage):
                if "id" not in data or data.get("id") is None:
                    data["id"] = f"msg-{uuid4().hex[:12]}"

            bulk_data.append(data)

        prepared_data = [self._prepare_document(doc) for doc in bulk_data]
        result = await self.storage.execute(
            self.storage.build_insert_many_query(self.collection_name, prepared_data)
        )

        # For MongoDB, get inserted ids
        if isinstance(self._storage, MongoDBStorage) and result:
            for i, inserted_id in enumerate(result.inserted_ids):
                bulk_data[i]["id"] = str(inserted_id)

        return [Message(**data) for data in bulk_data]
