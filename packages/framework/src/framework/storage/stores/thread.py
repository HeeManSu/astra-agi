"""
ThreadStore - domain store for conversation threads.

Provides high-level CRUD operations over the astra_threads table.
"""

from datetime import datetime, timezone

from framework.storage.base import StorageBackend
from framework.storage.models import Thread
from framework.storage.stores.base import BaseStore


class ThreadStore(BaseStore[Thread]):
    """
    ThreadStore manages astra_threads records.

    Methods:
    - create(Thread) -> Thread
    - get(thread_id) -> Thread | None
    - soft_delete(thread_id) -> None

    Automatically filters out soft-deleted records.
    """

    def __init__(self, storage: StorageBackend) -> None:
        super().__init__(storage=storage, model_cls=Thread, collection_name="astra_threads")

    async def create(self, thread: Thread) -> Thread:
        """
        Insert a new thread row.
        Note: DB-level defaults (created_at/updated_at) are handled by the database.

        Args:
            thread: Thread object to create

        Returns:
            Created Thread object
        """
        data = thread.model_dump(exclude_unset=True)
        query = self.storage.build_insert_query(self.collection_name, self._prepare_document(data))
        await self.storage.execute(query)
        return thread

    async def get(self, thread_id: str) -> Thread | None:
        """
        Fetch a single thread by ID.

        Args:
            thread_id: Thread identifier

        Returns:
            Thread object or None if not found
        """
        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict={"id": thread_id},
            limit=1,
        )
        row = await self.storage.fetch_one(query)
        if row is None:
            return None
        return self._row_to_model(row)

    async def soft_delete(self, thread_id: str) -> None:
        """
        Soft delete a thread by setting deleted_at timestamp.

        Args:
            thread_id: Thread identifier to soft delete
        """
        query = self.storage.build_update_query(
            collection=self.collection_name,
            filter_dict={"id": thread_id, "deleted_at": None},  # Only update if not already deleted
            update_data={"deleted_at": datetime.now(timezone.utc)},
        )
        await self.storage.execute(query)

    async def delete(self, thread_id: str) -> None:
        """
        Hard delete a thread (permanent deletion).

        Note: This will cascade delete associated messages if foreign key
        constraints are set with ON DELETE CASCADE.

        Args:
            thread_id: Thread identifier to delete
        """
        query = self.storage.build_delete_query(
            collection=self.collection_name,
            filter_dict={"id": thread_id},
        )
        await self.storage.execute(query)

    async def update(
        self,
        thread_id: str,
        title: str | None = None,
        metadata: dict | None = None,
        is_archived: bool | None = None,
    ) -> Thread | None:
        """
        Update thread fields.

        Args:
            thread_id: Thread identifier to update
            title: New title (optional)
            metadata: New metadata dict (optional)
            is_archived: New archived status (optional)

        Returns:
            Updated Thread object or None if not found
        """
        # Build update data from non-None args
        update_data: dict = {"updated_at": datetime.now(timezone.utc)}
        if title is not None:
            update_data["title"] = title
        if metadata is not None:
            update_data["metadata"] = metadata
        if is_archived is not None:
            update_data["is_archived"] = is_archived

        query = self.storage.build_update_query(
            collection=self.collection_name,
            filter_dict={"id": thread_id},
            update_data=update_data,
        )
        await self.storage.execute(query)

        # Return updated thread
        return await self.get(thread_id)
