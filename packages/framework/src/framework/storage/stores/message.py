"""
MessageStore - domain store for conversation messages.

Provides operations scoped to per-thread messages.
"""

import asyncio

from sqlalchemy import delete, func, select

from framework.storage.base import StorageBackend
from framework.storage.databases.libsql import astra_messages
from framework.storage.models import Message
from framework.storage.stores.base import BaseStore


class MessageStore(BaseStore[Message]):
    """
    MessageStore manages astra_messages records.

    Methods:
    - add(Message) -> Message
    - get_by_thread(thread_id, limit=None) -> list[Message]
    - delete_by_thread(thread_id) -> None

    Internally, messages are ordered by `sequence`.
    """

    def __init__(self, storage: StorageBackend) -> None:
        super().__init__(storage=storage, table=astra_messages, model_cls=Message)
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

    async def get_by_thread(
        self,
        thread_id: str,
        limit: int | None = None,
    ) -> list[Message]:
        """
        Fetch messages for a thread, ordered by sequence ascending.

        Args:
            thread_id: Thread identifier
            limit: Optional limit on number of messages
        """
        stmt = (
            select(astra_messages)
            .where(astra_messages.c.thread_id == thread_id)
            .order_by(astra_messages.c.sequence.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        rows = await self.storage.fetch_all(stmt)
        return [self._row_to_model(row) for row in rows]

    async def delete_by_thread(self, thread_id: str) -> None:
        """Delete all messages for a given thread."""
        stmt = delete(astra_messages).where(astra_messages.c.thread_id == thread_id)
        await self.storage.execute(stmt)

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

        # Prepare bulk insert data
        bulk_data = [msg.model_dump(exclude_unset=True) for msg in messages]

        # Use bulk insert with SQLAlchemy
        stmt = astra_messages.insert().values(bulk_data)

        # Check if storage supports execute_in_transaction
        if hasattr(self.storage, "execute_in_transaction"):
            # For single bulk insert, regular execute is fine
            await self.storage.execute(stmt)
        else:
            # Fallback: execute in transaction if available
            await self.storage.execute(stmt)

        return messages
