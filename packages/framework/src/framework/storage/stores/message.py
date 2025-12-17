"""
MessageStore - domain store for conversation messages.

Provides operations scoped to per-thread messages.
"""

import asyncio

from sqlalchemy import func, select

from framework.storage.base import StorageBackend
from framework.storage.databases.libsql import astra_messages
from framework.storage.models import Message
from framework.storage.stores.base import BaseStore


class MessageStore(BaseStore[Message]):
    """
    MessageStore manages astra_messages records.

    Methods:
    - add(Message) -> Message
    - get_recent(thread_id, limit) -> list[Message]
    - get_next_sequence(thread_id) -> int
    - bulk_add(messages) -> list[Message]

    Internally, messages are ordered by `sequence`.
    """

    def __init__(self, storage: StorageBackend) -> None:
        super().__init__(storage=storage, model_cls=Message)
        self.table = astra_messages
        # Lock for thread-safe sequence generation
        self._sequence_lock = asyncio.Lock()

    async def add(self, message: Message) -> Message:
        """
        Insert a new message row.

        Assumes message.sequence is set by caller.
        """
        data = message.model_dump(exclude_unset=True)
        stmt = astra_messages.insert().values(**data)
        await self.storage.execute(stmt)
        return message

    async def get_recent(self, thread_id: str, limit: int) -> list[Message]:
        """
        Fetch the most recent N messages, ordered chronologically.

        Args:
            thread_id: Thread identifier
            limit: Number of recent messages to fetch
        """
        stmt = (
            select(astra_messages)
            .where(astra_messages.c.thread_id == thread_id)
            .order_by(astra_messages.c.sequence.desc())
            .limit(limit)
        )
        rows = await self.storage.fetch_all(stmt)
        # Reverse to get chronological order (oldest to newest)
        return [self._row_to_model(row) for row in reversed(rows)]

    async def get_by_thread(
        self, thread_id: str, limit: int | None = None, offset: int = 0
    ) -> list[Message]:
        """Fetch all messages for a thread."""
        stmt = (
            select(astra_messages)
            .where(astra_messages.c.thread_id == thread_id)
            .order_by(astra_messages.c.sequence)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset > 0:
            stmt = stmt.offset(offset)
        rows = await self.storage.fetch_all(stmt)
        return [self._row_to_model(row) for row in rows]

    async def get_next_sequence(self, thread_id: str) -> int:
        """
        Get the next sequence number for a message in a thread.

        Uses MAX(sequence) + 1, starting from 1 if no messages exist.
        Thread-safe using asyncio lock.
        """
        async with self._sequence_lock:
            stmt = select(func.max(astra_messages.c.sequence).label("max_seq")).where(
                astra_messages.c.thread_id == thread_id
            )
            row = await self.storage.fetch_one(stmt)
            max_seq = row["max_seq"] if row and row["max_seq"] is not None else 0
            return int(max_seq) + 1

    async def bulk_add(self, messages: list[Message]) -> list[Message]:
        """
        Bulk insert multiple messages in a single transaction.

        This is more efficient than calling add() multiple times.

        Args:
            messages: List of Message objects to insert

        Returns:
            List of inserted Message objects
        """
        if not messages:
            return []

        # Prepare bulk insert data and execute in single operation
        bulk_data = [msg.model_dump(exclude_unset=True) for msg in messages]
        stmt = astra_messages.insert().values(bulk_data)
        await self.storage.execute(stmt)
        return messages
