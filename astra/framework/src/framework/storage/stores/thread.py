"""
ThreadStore - domain store for conversation threads.

Provides high-level CRUD operations over the astra_threads table.
"""

from datetime import datetime, timezone
from uuid import uuid4

from framework.storage.base import StorageBackend
from framework.storage.databases.mongodb import MongoDBStorage
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

    def _get_id_field(self) -> str:
        """Return the ID field name based on storage backend."""
        if isinstance(self._storage, MongoDBStorage):
            return "_id"
        return "id"

    async def create(self, thread: Thread) -> Thread:
        """
        Insert a new thread row.

        For MongoDB: Let database generate _id (ObjectId)
        For SQL: Generate id if not provided

        Args:
            thread: Thread object to create

        Returns:
            Created Thread object with id populated
        """
        data = thread.model_dump(exclude_unset=True)

        # For SQL backends, generate id if not provided
        if not isinstance(self._storage, MongoDBStorage):
            if "id" not in data or data.get("id") is None:
                data["id"] = f"thread-{uuid4().hex[:10]}"

        doc = self._prepare_document(data)
        result = await self.storage.execute(
            self.storage.build_insert_query(self.collection_name, doc)
        )

        # For MongoDB, get the inserted _id and return updated thread
        if isinstance(self._storage, MongoDBStorage) and result:
            data["id"] = str(result.inserted_id)

        return Thread(**data)

    async def get(self, thread_id: str) -> Thread | None:
        """
        Fetch a single thread by ID.

        Args:
            thread_id: Thread identifier

        Returns:
            Thread object or None if not found
        """
        id_field = self._get_id_field()

        # For MongoDB, need to convert string to ObjectId for _id queries
        if isinstance(self._storage, MongoDBStorage):
            from bson import ObjectId

            try:
                filter_dict = {id_field: ObjectId(thread_id)}
            except Exception:
                # If thread_id is not a valid ObjectId, try as string (legacy data)
                filter_dict = {id_field: thread_id}
        else:
            filter_dict = {id_field: thread_id}

        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
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
        id_field = self._get_id_field()

        if isinstance(self._storage, MongoDBStorage):
            from bson import ObjectId

            try:
                filter_dict = {id_field: ObjectId(thread_id), "deleted_at": None}
            except Exception:
                filter_dict = {id_field: thread_id, "deleted_at": None}
        else:
            filter_dict = {id_field: thread_id, "deleted_at": None}

        query = self.storage.build_update_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
            update_data={"deleted_at": datetime.now(timezone.utc)},
        )
        await self.storage.execute(query)

    async def delete(self, thread_id: str) -> None:
        """
        Hard delete a thread (permanent deletion).

        Args:
            thread_id: Thread identifier to delete
        """
        id_field = self._get_id_field()

        if isinstance(self._storage, MongoDBStorage):
            from bson import ObjectId

            try:
                filter_dict = {id_field: ObjectId(thread_id)}
            except Exception:
                filter_dict = {id_field: thread_id}
        else:
            filter_dict = {id_field: thread_id}

        query = self.storage.build_delete_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
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
        id_field = self._get_id_field()

        if isinstance(self._storage, MongoDBStorage):
            from bson import ObjectId

            try:
                filter_dict = {id_field: ObjectId(thread_id)}
            except Exception:
                filter_dict = {id_field: thread_id}
        else:
            filter_dict = {id_field: thread_id}

        update_data: dict = {"updated_at": datetime.now(timezone.utc)}
        if title is not None:
            update_data["title"] = title
        if metadata is not None:
            update_data["metadata"] = metadata
        if is_archived is not None:
            update_data["is_archived"] = is_archived

        query = self.storage.build_update_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
            update_data=update_data,
        )
        await self.storage.execute(query)

        return await self.get(thread_id)
