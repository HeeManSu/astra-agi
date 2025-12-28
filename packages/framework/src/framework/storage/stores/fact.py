"""FactStore - domain store for persistent facts.

Provides operations for managing persistent facts.
Database-agnostic implementation that works with any storage backend.
"""

from datetime import datetime, timezone
from typing import Any

from framework.storage.base import StorageBackend
from framework.storage.models import Fact, MemoryScope
from framework.storage.stores.base import BaseStore


class FactStore(BaseStore[Fact]):
    """
    FactStore manages astra_facts records.

    Methods:
    - add(fact) -> Fact
    - get(key, scope, scope_id) -> Fact | None
    - get_all(scope, scope_id) -> list[Fact]
    - update(fact) -> Fact
    - delete(key, scope, scope_id) -> None
    - search(query, scope, scope_id) -> list[Fact]

    Automatically filters out soft-deleted records.
    """

    def __init__(self, storage: StorageBackend) -> None:
        super().__init__(storage=storage, model_cls=Fact, collection_name="astra_facts")

    async def add(self, fact: Fact) -> Fact:
        """
        Add a new fact to the store.

        Args:
            fact: Fact object to insert

        Returns:
            The inserted Fact object
        """
        # Dump all fields to ensure they are present in DB (important for filters like deleted_at IS NULL)
        data = fact.model_dump()
        prepared_data = self._prepare_document(data)
        query = self.storage.build_insert_query(self.collection_name, prepared_data)
        await self.storage.execute(query)
        return fact

    async def get(
        self,
        key: str,
        scope: MemoryScope,
        scope_id: str | None = None,
    ) -> Fact | None:
        """
        Retrieve a fact by key, scope, and scope_id.

        Args:
            key: Fact key
            scope: Memory scope
            scope_id: Scope identifier (user_id, session_id, etc.)

        Returns:
            Fact if found, None otherwise
        """
        filter_dict: dict[str, Any] = {
            "key": key,
            "scope": scope.value,
            "deleted_at": None,
        }
        if scope_id:
            filter_dict["scope_id"] = scope_id

        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
            limit=1,
        )
        row = await self.storage.fetch_one(query)
        return self._row_to_model(row) if row else None

    async def get_all(
        self,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
        limit: int | None = None,
        order_by: str = "created_at",
        order_direction: int = -1,
    ) -> list[Fact]:
        """
        Get all facts for a scope.

        Args:
            scope: Memory scope (if None, gets all scopes)
            scope_id: Scope identifier (if None, gets all scope_ids)
            limit: Maximum number of facts to return (None = all)
            order_by: Field to sort by (default: "created_at")
            order_direction: Sort direction (1 = ascending, -1 = descending)

        Returns:
            List of Fact objects
        """
        filter_dict: dict[str, Any] = {"deleted_at": None}
        if scope:
            filter_dict["scope"] = scope.value
        if scope_id:
            filter_dict["scope_id"] = scope_id

        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
            sort=[(order_by, order_direction)],
            limit=limit,
        )
        rows = await self.storage.fetch_all(query)
        return [self._row_to_model(row) for row in rows]

    async def clear_all(
        self,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
    ) -> int:
        """
        Clear all facts for a scope (soft delete).

        Args:
            scope: Memory scope (if None, clears all scopes)
            scope_id: Scope identifier (if None, clears all scope_ids)

        Returns:
            Number of facts deleted
        """
        filter_dict: dict[str, Any] = {"deleted_at": None}
        if scope:
            filter_dict["scope"] = scope.value
        if scope_id:
            filter_dict["scope_id"] = scope_id

        # Get count before deletion
        count_query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
        )
        rows = await self.storage.fetch_all(count_query)
        count = len(rows)

        # Soft delete all matching facts
        update_query = self.storage.build_update_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
            update_data={"deleted_at": datetime.now(timezone.utc)},
            update_many=True,  # Important: update ALL matching documents
        )
        await self.storage.execute(update_query)

        return count

    async def update(self, fact: Fact) -> Fact:
        """
        Update an existing fact.

        Args:
            fact: Fact object with updated values

        Returns:
            The updated Fact
        """
        fact.updated_at = datetime.now(timezone.utc)
        # Dump all fields (except fixed ones) to ensure modified fields are included
        data = fact.model_dump(exclude={"id", "created_at"})

        filter_dict: dict[str, Any] = {
            "id": fact.id,
            "deleted_at": None,
        }

        query = self.storage.build_update_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
            update_data=data,
        )
        await self.storage.execute(query)
        return fact

    async def delete(
        self,
        key: str,
        scope: MemoryScope,
        scope_id: str | None = None,
    ) -> bool:
        """
        Soft delete a fact.

        Args:
            key: Fact key
            scope: Memory scope
            scope_id: Scope identifier

        Returns:
            True if deleted, False if not found
        """
        filter_dict: dict[str, Any] = {
            "key": key,
            "scope": scope.value,
            "deleted_at": None,
        }
        if scope_id:
            filter_dict["scope_id"] = scope_id

        query = self.storage.build_update_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
            update_data={"deleted_at": datetime.now(timezone.utc)},
        )
        await self.storage.execute(query)
        return True

    async def search(
        self,
        query: str,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
        limit: int = 10,
    ) -> list[Fact]:
        """
        Search facts by keyword (searches in key, value, tags).

        Args:
            query: Search query string
            scope: Memory scope (if None, searches all scopes)
            scope_id: Scope identifier (if None, searches all scope_ids)
            limit: Maximum number of results

        Returns:
            List of matching Fact objects
        """
        # For now, simple keyword search in key and tags
        # TODO: Implement full-text search for value field
        filter_dict: dict[str, Any] = {"deleted_at": None}
        if scope:
            filter_dict["scope"] = scope.value
        if scope_id:
            filter_dict["scope_id"] = scope_id

        # Get all facts and filter by query (simple implementation)
        # In production, use database full-text search
        all_facts = await self.get_all(scope=scope, scope_id=scope_id)
        query_lower = query.lower()

        matching = []
        for fact in all_facts:
            if query_lower in fact.key.lower() or any(
                query_lower in tag.lower() for tag in fact.tags
            ):
                matching.append(fact)
                if len(matching) >= limit:
                    break

        return matching
