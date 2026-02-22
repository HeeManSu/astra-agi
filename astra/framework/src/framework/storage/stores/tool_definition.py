"""
ToolDefinitionStore - stores individual tool definitions.

Each tool is stored as a separate row, enabling:
- UI editing
- LLM enrichment
- Filtering/searching
- Independent updates

Collection: astra_tool_definitions
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from framework.storage.base import StorageBackend
from framework.storage.databases.mongodb import MongoDBStorage
from framework.storage.models import ToolDefinition
from framework.storage.stores.base import BaseStore


class ToolDefinitionStore(BaseStore[ToolDefinition]):
    """
    Store for individual tool definitions.

    Methods:
    - get_by_name(name, source) -> ToolDefinition | None
    - get_by_source(source) -> list[ToolDefinition]
    - save(definition) -> ToolDefinition
    - update(id, **fields) -> ToolDefinition | None
    - delete_by_source(source) -> None
    """

    def __init__(self, storage: StorageBackend) -> None:
        super().__init__(
            storage=storage,
            model_cls=ToolDefinition,
            collection_name="astra_tool_definitions",
        )

    def _get_id_field(self) -> str:
        """Return the ID field name based on storage backend."""
        if isinstance(self._storage, MongoDBStorage):
            return "_id"
        return "id"

    async def get_by_name(
        self,
        name: str,
    ) -> ToolDefinition | None:
        """
        Get a tool definition by name and source.

        Args:
            name: Tool name (e.g., "get_stock_price")

        Returns:
            ToolDefinition or None if not found
        """
        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict={"slug": name},
            limit=1,
        )
        row = await self.storage.fetch_one(query)
        if row is None:
            return None
        return self._row_to_model(row)

    async def get_by_source(self, source: str) -> list[ToolDefinition]:
        """
        Get all tool definitions for a source.

        Args:
            source: Source identifier

        Returns:
            List of ToolDefinition objects
        """
        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict={"source": source},
            sort=[("slug", 1)],
        )
        rows = await self.storage.fetch_all(query)
        return [self._row_to_model(row) for row in rows]

    async def get_all(self, limit: int = 100) -> list[ToolDefinition]:
        """
        Get all tool definitions.

        Args:
            limit: Maximum number to return

        Returns:
            List of ToolDefinition objects
        """
        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict={},
            sort=[("source", 1), ("slug", 1)],
            limit=limit,
        )
        rows = await self.storage.fetch_all(query)
        return [self._row_to_model(row) for row in rows]

    async def get_active_tools(self, source: str | None = None) -> list[ToolDefinition]:
        """
        Get active tool definitions, optionally filtered by source.

        Args:
            source: Optional source filter

        Returns:
            List of active ToolDefinition objects
        """
        filter_dict: dict[str, Any] = {"is_active": True}
        if source:
            filter_dict["source"] = source

        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
            sort=[("source", 1), ("slug", 1)],
        )
        rows = await self.storage.fetch_all(query)
        return [self._row_to_model(row) for row in rows]

    async def save(self, definition: ToolDefinition) -> ToolDefinition:
        """
        Save a tool definition (upsert by name + source).

        Args:
            definition: ToolDefinition to save

        Returns:
            Saved ToolDefinition with id populated
        """
        # Check if exists
        existing = await self.get_by_name(definition.slug)

        if existing:
            # Update existing
            return await self.update(
                existing.id,  # type: ignore
                name=definition.name,
                description=definition.description,
                input_schema=definition.input_schema,
                output_schema=definition.output_schema,
                example=definition.example,
                hash=definition.hash,
                is_improved=definition.is_improved,
                improved_by=definition.improved_by,
                version=definition.version,
            )  # type: ignore

        # Insert new
        data = definition.model_dump(exclude_unset=True)

        # For SQL backends, generate id if not provided
        if not isinstance(self._storage, MongoDBStorage):
            if "id" not in data or data.get("id") is None:
                data["id"] = f"tool-{uuid4().hex[:10]}"

        doc = self._prepare_document(data)
        result = await self.storage.execute(
            self.storage.build_insert_query(self.collection_name, doc)
        )

        # For MongoDB, get the inserted _id
        if isinstance(self._storage, MongoDBStorage) and result:
            data["id"] = str(result.inserted_id)

        return ToolDefinition(**data)

    async def update(
        self,
        definition_id: str,
        **fields,
    ) -> ToolDefinition | None:
        """
        Update tool definition fields.

        Args:
            definition_id: Tool definition ID
            **fields: Fields to update

        Returns:
            Updated ToolDefinition or None if not found
        """
        id_field = self._get_id_field()

        if isinstance(self._storage, MongoDBStorage):
            from bson import ObjectId

            try:
                filter_dict = {id_field: ObjectId(definition_id)}
            except Exception:
                filter_dict = {id_field: definition_id}
        else:
            filter_dict = {id_field: definition_id}

        update_data = {"updated_at": datetime.now(timezone.utc), **fields}

        query = self.storage.build_update_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
            update_data=update_data,
        )
        await self.storage.execute(query)

        # Return updated record
        return await self._get_by_id(definition_id)

    async def _get_by_id(self, definition_id: str) -> ToolDefinition | None:
        """Get by ID."""
        id_field = self._get_id_field()

        if isinstance(self._storage, MongoDBStorage):
            from bson import ObjectId

            try:
                filter_dict = {id_field: ObjectId(definition_id)}
            except Exception:
                filter_dict = {id_field: definition_id}
        else:
            filter_dict = {id_field: definition_id}

        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
            limit=1,
        )
        row = await self.storage.fetch_one(query)
        if row is None:
            return None
        return self._row_to_model(row)

    async def delete_by_source(self, source: str) -> int:
        """
        Delete all tool definitions for a source.

        Args:
            source: Source identifier

        Returns:
            Number of deleted records
        """
        # For MongoDB, we need delete_many (build custom query)
        if isinstance(self._storage, MongoDBStorage):
            query = {
                "collection": self.collection_name,
                "action": "delete_many",
                "filter": {"source": source},
            }
        else:
            query = self.storage.build_delete_query(
                collection=self.collection_name,
                filter_dict={"source": source},
            )

        result = await self.storage.execute(query)

        if hasattr(result, "deleted_count"):
            return result.deleted_count
        return 0

    async def delete(self, definition_id: str) -> None:
        """
        Delete a single tool definition.

        Args:
            definition_id: Tool definition ID
        """
        id_field = self._get_id_field()

        if isinstance(self._storage, MongoDBStorage):
            from bson import ObjectId

            try:
                filter_dict = {id_field: ObjectId(definition_id)}
            except Exception:
                filter_dict = {id_field: definition_id}
        else:
            filter_dict = {id_field: definition_id}

        query = self.storage.build_delete_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
        )
        await self.storage.execute(query)

    async def get_by_slugs(self, slugs: list[str]) -> dict[str, ToolDefinition]:
        """
        Get multiple tool definitions by slugs.

        Args:
            slugs: List of slugs to fetch

        Returns:
            Dict mapping slug to ToolDefinition
        """
        if not slugs:
            return {}

        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict={"slug": {"$in": slugs}},
        )
        rows = await self.storage.fetch_all(query)
        definitions = [self._row_to_model(row) for row in rows]
        return {definition.slug: definition for definition in definitions}

    async def get_by_sources(self, sources: list[str]) -> list[ToolDefinition]:
        """
        Get all tool definitions for multiple sources.

        Args:
            sources: List of source identifiers (e.g., ["mcp:filesystem", "mcp:brave_search"])

        Returns:
            List of ToolDefinition objects
        """
        if not sources:
            return []

        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict={"source": {"$in": sources}},
            sort=[("slug", 1)],
        )
        rows = await self.storage.fetch_all(query)
        return [self._row_to_model(row) for row in rows]

    async def save_many(self, definitions: list[ToolDefinition]) -> list[ToolDefinition]:
        """
        Save multiple tool definitions.

        Args:
            definitions: List of ToolDefinition to save

        Returns:
            List of saved ToolDefinitions
        """
        if not definitions:
            return []

        # Use slug as identity for batch upsert behavior.
        by_slug: dict[str, ToolDefinition] = {}
        for definition in definitions:
            by_slug[definition.slug] = definition

        unique_definitions = list(by_slug.values())
        slugs = [definition.slug for definition in unique_definitions]
        existing_by_slug = await self.get_by_slugs(slugs)

        saved_by_slug: dict[str, ToolDefinition] = {}
        insert_rows: list[dict[str, Any]] = []
        insert_slugs: list[str] = []

        for definition in unique_definitions:
            existing = existing_by_slug.get(definition.slug)
            if existing:
                updated = await self.update(
                    existing.id,  # type: ignore[arg-type]
                    name=definition.name,
                    description=definition.description,
                    input_schema=definition.input_schema,
                    output_schema=definition.output_schema,
                    required_fields=definition.required_fields,
                    example=definition.example,
                    hash=definition.hash,
                    is_improved=definition.is_improved,
                    improved_by=definition.improved_by,
                    version=definition.version,
                    is_active=definition.is_active,
                )
                if updated is not None:
                    saved_by_slug[definition.slug] = updated
                continue

            data = definition.model_dump(exclude_unset=True)
            if not isinstance(self._storage, MongoDBStorage):
                if "id" not in data or data.get("id") is None:
                    data["id"] = f"tool-{uuid4().hex[:10]}"

            insert_rows.append(data)
            insert_slugs.append(definition.slug)

        if insert_rows:
            prepared_rows = [self._prepare_document(row) for row in insert_rows]
            result = await self.storage.execute(
                self.storage.build_insert_many_query(self.collection_name, prepared_rows)
            )

            if isinstance(self._storage, MongoDBStorage) and result:
                for idx, inserted_id in enumerate(result.inserted_ids):
                    insert_rows[idx]["id"] = str(inserted_id)

            for slug, row in zip(insert_slugs, insert_rows, strict=False):
                saved_by_slug[slug] = ToolDefinition(**row)

        return [saved_by_slug[definition.slug] for definition in definitions if definition.slug in saved_by_slug]

    async def get_hashes_by_slugs(self, slugs: list[str]) -> dict[str, str]:
        """
        Get hashes for multiple tool slugs.

        Args:
            slugs: List of slugs

        Returns:
            Dict mapping slug to hash
        """
        if not slugs:
            return {}

        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict={"slug": {"$in": slugs}},
        )
        rows = await self.storage.fetch_all(query)
        # Return object with minimal fields needed for sync check
        results = {}
        for row in rows:
            # Handle diff backend return types
            slug = row.get("slug") if isinstance(row, dict) else row.slug
            hash_val = row.get("hash") if isinstance(row, dict) else row.hash
            results[slug] = hash_val
        return results
