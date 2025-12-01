"""
ThreadStore - domain store for conversation threads.

Provides high-level CRUD operations over the astra_threads table.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import delete, select, update

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
    - update(thread_id, **fields) -> Thread | None
    - delete(thread_id) -> None
    """

    def __init__(self, storage: StorageBackend) -> None:
        super().__init__(storage=storage, table=astra_threads, model_cls=Thread)

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

    async def update(self, thread_id: str, **fields: Any) -> Thread | None:
        """
        Update fields on a thread and return the updated model.

        Example:
            await thread_store.update("thread-1", title="New Title")
        """
        if not fields:
            # Nothing to update
            return await self.get(thread_id)

        stmt = update(astra_threads).where(astra_threads.c.id == thread_id).values(**fields)
        await self.storage.execute(stmt)
        return await self.get(thread_id)

    async def delete(self, thread_id: str) -> None:
        """Delete a thread (messages may be cascade-deleted by FK)."""
        stmt = delete(astra_threads).where(astra_threads.c.id == thread_id)
        await self.storage.execute(stmt)

    async def upsert(self, thread: Thread) -> Thread:
        """
        Insert or update a thread (upsert operation).

        If thread with same ID exists, updates it. Otherwise, creates new one.

        Args:
            thread: Thread object to upsert

        Returns:
            Upserted Thread object
        """
        # Check if thread exists
        existing = await self.get(thread.id)

        if existing:
            # Update existing thread
            update_data = thread.model_dump(exclude_unset=True, exclude={"id", "created_at"})
            update_data["updated_at"] = datetime.now()
            updated = await self.update(thread.id, **update_data)
            if updated is None:
                raise RuntimeError(f"Failed to update thread {thread.id}")
            return updated
        else:
            # Create new thread
            return await self.create(thread)

    async def get_all(
        self,
        resource_id: str | None = None,
        is_archived: bool | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[Thread]:
        """
        Get threads with advanced filtering.

        Args:
            resource_id: Filter by resource_id
            is_archived: Filter by archived status
            date_from: Filter threads created after this date
            date_to: Filter threads created before this date
            limit: Maximum number of threads to return
            offset: Number of threads to skip (for pagination)
            order_by: Column to order by (default: "created_at")
            order_desc: Whether to order descending (default: True)

        Returns:
            List of Thread objects matching the filters
        """
        stmt = select(astra_threads)

        # Apply filters
        if resource_id is not None:
            stmt = stmt.where(astra_threads.c.resource_id == resource_id)

        if is_archived is not None:
            stmt = stmt.where(astra_threads.c.is_archived == is_archived)

        if date_from is not None:
            stmt = stmt.where(astra_threads.c.created_at >= date_from)

        if date_to is not None:
            stmt = stmt.where(astra_threads.c.created_at <= date_to)

        # Apply ordering
        order_column = getattr(astra_threads.c, order_by, astra_threads.c.created_at)
        if order_desc:
            stmt = stmt.order_by(order_column.desc())
        else:
            stmt = stmt.order_by(order_column.asc())

        # Apply pagination
        if offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        rows = await self.storage.fetch_all(stmt)
        return [self._row_to_model(row) for row in rows]
