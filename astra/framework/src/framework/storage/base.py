from abc import abstractmethod
from typing import Any


class StorageBackend:
    """
    Abstract base class for storage backends.

    Provides a database-agnostic interface for AI agent storage.
    Each storage backend implements query builders to handle database-specific operations.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage backend."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection to the storage backend."""

    @abstractmethod
    async def execute(self, query: Any, params: dict[str, Any] | None = None) -> None:
        """Execute a write operation."""

    @abstractmethod
    async def fetch_all(
        self, query: Any, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all rows."""

    @abstractmethod
    async def fetch_one(
        self, query: Any, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Fetch a single row."""

    @abstractmethod
    async def create_tables(self) -> None:
        """Create the necessary tables if they don't exist."""

    # Query builder methods
    def build_insert_query(self, collection: str, data: dict[str, Any]) -> Any:
        """
        Build insert query for a single document.

        Args:
            collection: Collection/table name
            data: Document data as dict

        Returns:
            Database-specific query object
        """
        raise NotImplementedError("Storage backend must implement build_insert_query")

    def build_insert_many_query(self, collection: str, data: list[dict[str, Any]]) -> Any:
        """
        Build bulk insert query for multiple documents.

        Args:
            collection: Collection/table name
            data: List of document data dicts

        Returns:
            Database-specific query object
        """
        raise NotImplementedError("Storage backend must implement build_insert_many_query")

    def build_select_query(
        self,
        collection: str,
        filter_dict: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Any:
        """
        Build select query.

        Args:
            collection: Collection/table name
            filter_dict: Filter conditions {field: value}
            sort: Sort order [(field, direction)] where direction is 1 (asc) or -1 (desc)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Database-specific query object
        """
        raise NotImplementedError("Storage backend must implement build_select_query")

    def build_update_query(
        self,
        collection: str,
        filter_dict: dict[str, Any],
        update_data: dict[str, Any],
        update_many: bool = False,
    ) -> Any:
        """
        Build update query.

        Args:
            collection: Collection/table name
            filter_dict: Filter conditions {field: value}
            update_data: Fields to update {field: new_value}
            update_many: If True, update all matching rows (default: False)
                        For SQL backends this has no effect (all matching rows are updated).
                        For MongoDB, this uses update_many instead of update_one.

        Returns:
            Database-specific query object
        """
        raise NotImplementedError("Storage backend must implement build_update_query")

    def build_delete_query(self, collection: str, filter_dict: dict[str, Any]) -> Any:
        """
        Build delete query.

        Args:
            collection: Collection/table name
            filter_dict: Filter conditions {field: value}

        Returns:
            Database-specific query object
        """
        raise NotImplementedError("Storage backend must implement build_delete_query")

    async def get_max_value(self, collection: str, field: str, filter_dict: dict[str, Any]) -> int:
        """
        Get maximum value of a field matching filter conditions.

        Each storage backend implements this according to its capabilities.
        Returns 0 if no records found.

        Args:
            collection: Collection/table name
            field: Field name to get max value of
            filter_dict: Filter conditions {field: value}

        Returns:
            Maximum value as int (0 if no records found)
        """
        raise NotImplementedError("Storage backend must implement get_max_value")

    async def table_exists(self, table_name: str) -> bool:
        """
        Check if a table/collection exists in the database.

        Args:
            table_name: Name of the table/collection to check

        Returns:
            True if the table exists, False otherwise
        """
        raise NotImplementedError("Storage backend must implement table_exists")
