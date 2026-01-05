from collections.abc import Mapping
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from framework.storage.base import StorageBackend


class MongoDBStorage(StorageBackend):
    """
    MongoDB-backed implementation of Storage using motor.

    Example:
        storage = MongoDBStorage(
            url="mongodb://localhost:27017",
            db_name="astra"
        )
        await storage.connect()
    """

    def __init__(self, url: str, db_name: str = "astra_db"):
        self.url = url
        self.db_name = db_name
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None
        self._initialized: bool = False

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Get the database instance"""
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db

    async def connect(self) -> None:
        """Connect to the database"""
        if self._initialized:
            return

        self._client = AsyncIOMotorClient(self.url)
        self._db = self._client[self.db_name]

        # Test connection
        try:
            await self._client.admin.command("ping")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to MongoDB: {e}") from e

        await self.create_tables()
        self._initialized = True

    async def disconnect(self) -> None:
        """Close the MongoDB client"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._initialized = False

    def _convert_id_filter(self, filter_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Convert 'id' field to '_id' in filter dictionaries for MongoDB queries.

        MongoDB uses _id as primary key, but stores use 'id' in their queries.
        This helper ensures queries work correctly.
        """
        if not filter_dict:
            return filter_dict

        converted = dict(filter_dict)
        if "id" in converted and "_id" not in converted:
            converted["_id"] = converted.pop("id")
        return converted

    async def create_tables(self) -> None:
        """Initialize collections and indexes. In MongoDB, 'tables' are collections."""

        if self._db is None:
            return

        # astra_threads indexes
        threads_collection = self._db["astra_threads"]
        await threads_collection.create_index("id", unique=True)
        await threads_collection.create_index("resource_id")
        await threads_collection.create_index("created_at")
        await threads_collection.create_index("is_archived")
        await threads_collection.create_index("deleted_at")

        # astra_messages indexes
        message_collection = self._db["astra_messages"]
        await message_collection.create_index("id", unique=True)
        await message_collection.create_index("thread_id")
        await message_collection.create_index([("thread_id", 1), ("sequence", 1)])
        await message_collection.create_index("created_at")
        await message_collection.create_index("deleted_at")

        # astra_facts indexes (for LTM/PersistentFacts)
        facts_collection = self._db["astra_facts"]
        await facts_collection.create_index("id", unique=True)
        await facts_collection.create_index([("key", 1), ("scope", 1), ("scope_id", 1)])
        await facts_collection.create_index([("scope", 1), ("scope_id", 1)])
        await facts_collection.create_index("created_at")
        await facts_collection.create_index("deleted_at")
        await facts_collection.create_index("expires_at")

        # astra_team_auth indexes (for playground auth)
        auth_collection = self._db["astra_team_auth"]
        await auth_collection.create_index("id", unique=True)
        await auth_collection.create_index("email", unique=True)
        await auth_collection.create_index("deleted_at")

    async def execute(self, query: Mapping[str, Any], params: dict[str, Any] | None = None) -> None:
        """
        Execute a write operation.
        For MongoDB, 'query' is expected to be a dictionary with:
        {
            "collection": "collection_name"
            "action": "insert_one" | "update_one" | "delete_one" | "insert_many" | "update_many" | "delete_many"
        }

        Returns:
            None (operation result is not returned, matching StorageBackend interface)
        """
        if not self._initialized:
            await self.connect()

        collection_name = query.get("collection")
        action = query.get("action")
        filter_doc = query.get("filter", {})

        if not collection_name or not action:
            raise ValueError("Query must specify 'collection' and 'action'")

        collection = self.db[collection_name]

        if action == "insert_one":
            await collection.insert_one(query.get("document", {}))

        elif action == "insert_many":
            await collection.insert_many(query.get("documents", []))

        elif action == "update_one":
            await collection.update_one(
                filter_doc, query.get("update", {}), upsert=query.get("upsert", False)
            )

        elif action == "update_many":
            await collection.update_many(
                filter_doc, query.get("update", {}), upsert=query.get("upsert", False)
            )

        elif action == "delete_one":
            await collection.delete_one(filter_doc)

        elif action == "delete_many":
            await collection.delete_many(filter_doc)

        else:
            raise ValueError(f"Invalid action: {action}")

    async def fetch_all(
        self, query: Mapping[str, Any], params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch all documents matching the query.
        For MongoDB, 'query' is expected to be a dictionary with:
        {
            "collection": "collection_name"
            "filter": {...},
            "sort": [("field", 1), ...],
            "limit": int,
            "skip": int
        }
        """
        if not self._initialized:
            await self.connect()

        collection_name = query.get("collection")
        if not collection_name:
            raise ValueError("Query must specify 'collection'")

        collection = self.db[collection_name]

        filter_doc = query.get("filter", {})
        cursor = collection.find(filter_doc)

        if "sort" in query:
            cursor = cursor.sort(query["sort"])
        if "skip" in query:
            cursor = cursor.skip(query["skip"])
        if "limit" in query:
            cursor = cursor.limit(query["limit"])

        return await cursor.to_list(length=None)

    async def fetch_one(
        self, query: Mapping[str, Any], params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """
        Fetch a single document matching the query.
        For MongoDB, 'query' is expected to be a dictionary with:
        {
            "collection": "collection_name"
            "filter": {...},
        }
        """
        if not self._initialized:
            await self.connect()

        collection_name = query.get("collection")
        if not collection_name:
            raise ValueError("Query must specify 'collection'")

        if not collection_name.startswith("astra_"):
            collection_name = f"astra_{collection_name}"

        collection = self.db[collection_name]
        filter_doc = query.get("filter", {})

        return await collection.find_one(filter_doc)

    def build_insert_query(self, collection: str, data: dict[str, Any]) -> Any:
        """
        Build MongoDB insert query for a single document.

        Args:
            collection: Collection name
            data: Document data as dict

        Returns:
            MongoDB query dict with collection, action, and document
        """
        return {
            "collection": collection,
            "action": "insert_one",
            "document": data,
        }

    def build_insert_many_query(self, collection: str, data: list[dict[str, Any]]) -> Any:
        """
        Build MongoDB bulk insert query for multiple documents.

        Args:
            collection: Collection name
            data: List of document data dicts

        Returns:
            MongoDB query dict with collection, action, and documents
        """
        return {
            "collection": collection,
            "action": "insert_many",
            "documents": data,
        }

    def build_select_query(
        self,
        collection: str,
        filter_dict: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Any:
        """
        Build MongoDB find query with filters, sorting, and pagination.

        Automatically filters out soft-deleted records (deleted_at is null or doesn't exist).

        Args:
            collection: Collection name
            filter_dict: Filter conditions {field: value}
            sort: Sort order [(field, direction)] where direction is 1 (asc) or -1 (desc)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            MongoDB query dict
        """
        # Exclude soft-deleted records
        base_filter = {"$or": [{"deleted_at": None}, {"deleted_at": {"$exists": False}}]}

        # convert id to _id for MongoDB
        if filter_dict:
            converted_filter = self._convert_id_filter(filter_dict)
            base_filter = {"$and": [base_filter, converted_filter]}

        query: dict[str, Any] = {
            "collection": collection,
            "filter": base_filter,
        }
        if sort:
            query["sort"] = sort
        if limit is not None:
            query["limit"] = limit
        if offset is not None:
            query["skip"] = offset
        return query

    def build_update_query(
        self,
        collection: str,
        filter_dict: dict[str, Any],
        update_data: dict[str, Any],
        update_many: bool = False,
    ) -> Any:
        """
        Build MongoDB update query.

        Args:
            collection: Collection name
            filter_dict: Filter conditions {field: value}
            update_data: Fields to update {field: new_value}
            update_many: If True, update all matching documents (default: False)

        Returns:
            MongoDB query dict with collection, action, filter, and update
        """
        # convert id to _id
        converted_filter = self._convert_id_filter(filter_dict)
        return {
            "collection": collection,
            "action": "update_many" if update_many else "update_one",
            "filter": converted_filter,
            "update": {"$set": update_data},
        }

    def build_delete_query(self, collection: str, filter_dict: dict[str, Any]) -> Any:
        """
        Build MongoDB delete query.

        Args:
            collection: Collection name
            filter_dict: Filter conditions {field: value}

        Returns:
            MongoDB query dict with collection, action, and filter
        """
        # convert id to _id
        converted_filter = self._convert_id_filter(filter_dict)
        return {
            "collection": collection,
            "action": "delete_one",
            "filter": converted_filter,
        }

    async def get_max_value(self, collection: str, field: str, filter_dict: dict[str, Any]) -> int:
        """
        Get maximum value of a field using MongoDB find and sort.

        Args:
            collection: Collection name
            field: Field name to get max value of
            filter_dict: Filter conditions {field: value}

        Returns:
            Maximum value as int (0 if no records found)
        """
        if not self._initialized:
            await self.connect()

        # convert id to _id
        converted_filter = self._convert_id_filter(filter_dict)
        coll = self.db[collection]
        cursor = coll.find(converted_filter).sort(field, -1).limit(1)
        doc = await cursor.to_list(length=1)
        if doc and len(doc) > 0:
            return int(doc[0].get(field, 0))
        return 0

    async def table_exists(self, table_name: str) -> bool:
        """
        Check if a collection exists in the MongoDB database.

        Args:
            table_name: Name of the collection to check

        Returns:
            True if the collection exists, False otherwise
        """
        if not self._initialized:
            await self.connect()

        collection_names = await self.db.list_collection_names()
        return table_name in collection_names
