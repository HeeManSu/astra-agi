"""
ThreadStore - domain store for conversation threads.

Provides high-level CRUD operations over the astra_threads table.
"""

from sqlalchemy import select

from framework.storage.base import StorageBackend
from framework.storage.databases.libsql import astra_threads
from framework.storage.models import Thread
from framework.storage.stores.base import BaseStore


class ThreadStore(BaseStore[Thread]):
    """
    ThreadStore manages astra_threads records.

    Methods:
    - create(Thread) -> Thread
    - get(thread_id) -> Thread | None
    """

    def __init__(self, storage: StorageBackend) -> None:
        super().__init__(storage=storage, model_cls=Thread)
        self.table = astra_threads

    async def create(self, thread: Thread) -> Thread:
        """
        Insert a new thread row.

        Note: DB-level defaults (created_at/updated_at) are handled by the database.
        """
        data = thread.model_dump(exclude_unset=True)
        stmt = astra_threads.insert().values(**data)
        await self.storage.execute(stmt)
        return thread

    async def get(self, thread_id: str) -> Thread | None:
        """Fetch a single thread by ID."""
        stmt = select(astra_threads).where(astra_threads.c.id == thread_id)
        row = await self.storage.fetch_one(stmt)
        if row is None:
            return None
        return self._row_to_model(row)

    async def get_all(self, limit: int = 20, offset: int = 0) -> list[Thread]:
        """Fetch all threads with pagination."""
        stmt = select(self.table).limit(limit).offset(offset)
        rows = await self.storage.fetch_all(stmt)
        return [self._row_to_model(row) for row in rows]

    async def update(self, thread_id: str, **kwargs) -> Thread | None:
        """Update a thread."""
        if not kwargs:
            return await self.get(thread_id)

        stmt = astra_threads.update().where(astra_threads.c.id == thread_id).values(**kwargs)
        await self.storage.execute(stmt)
        return await self.get(thread_id)

    async def delete(self, thread_id: str) -> None:
        """Delete a thread."""
        stmt = astra_threads.delete().where(astra_threads.c.id == thread_id)
        await self.storage.execute(stmt)
