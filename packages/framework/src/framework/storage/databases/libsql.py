from collections.abc import Mapping
from typing import Any

from sqlalchemy import (
    INTEGER,
    JSON,
    TEXT,
    Boolean,
    Column,
    DateTime,
    Executable,
    Index,
    MetaData,
    Select,
    String,
    Table,
    delete,
    event,
    func,
    select,
    text,
    update,
)
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.sql.schema import ForeignKey

from framework.storage.base import StorageBackend


metadata = MetaData()

astra_threads = Table(
    "astra_threads",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("agent_name", String(255), nullable=True, index=True),
    Column("resource_id", String(64), nullable=True, index=True),
    Column("title", String(255), nullable=True),
    Column("message_count", INTEGER, server_default="0"),
    Column("metadata", JSON, nullable=True),
    Column("is_archived", Boolean, nullable=False, server_default="0"),
    Column("deleted_at", DateTime(timezone=True), nullable=True, index=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
    # Indexes for common query patterns
    Index("idx_threads_created_at", "created_at"),
    Index("idx_threads_is_archived", "is_archived"),
    Index("idx_threads_deleted_at", "deleted_at"),
    Index("idx_threads_resource_id_created", "resource_id", "created_at"),
)

astra_messages = Table(
    "astra_messages",
    metadata,
    Column("id", String(64), primary_key=True),
    Column(
        "thread_id",
        String(64),
        ForeignKey("astra_threads.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    ),
    Column("role", String(32), nullable=False),  # "user", "assistant", "system", "tool"
    Column("content", TEXT, nullable=False),
    Column("metadata", JSON, nullable=True),
    Column("sequence", INTEGER, nullable=False),  # ordering within thread
    Column("deleted_at", DateTime(timezone=True), nullable=True, index=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    # Indexes for common query patterns
    Index("idx_messages_thread_sequence", "thread_id", "sequence"),
    Index("idx_messages_thread_role", "thread_id", "role"),
    Index("idx_messages_created_at", "created_at"),
    Index("idx_messages_deleted_at", "deleted_at"),
)

astra_facts = Table(
    "astra_facts",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("key", String(255), nullable=False),
    Column("value", JSON, nullable=False),
    Column("scope", String(32), nullable=False),  # "user", "session", "agent", "global"
    Column("scope_id", String(64), nullable=True),  # user_id, session_id, agent_id, etc.
    Column("schema_type", String(128), nullable=True),  # Optional schema name
    Column("tags", JSON, nullable=True),  # Array of tags
    Column("metadata", JSON, nullable=True),  # Additional metadata
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Column("expires_at", DateTime(timezone=True), nullable=True),
    Column("deleted_at", DateTime(timezone=True), nullable=True, index=True),
    # Indexes for common query patterns
    Index("idx_facts_key_scope", "key", "scope", "scope_id"),
    Index("idx_facts_scope", "scope", "scope_id"),
    Index("idx_facts_created_at", "created_at"),
    Index("idx_facts_deleted_at", "deleted_at"),
)

astra_team_auth = Table(
    "astra_team_auth",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("email", String(255), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Column("deleted_at", DateTime(timezone=True), nullable=True),
)


class LibSQLStorage(StorageBackend):
    """
    LibSQL-backed implementation of Storage.

    Uses SQLAlchemy async engine + a LibSQL/SQLite URL.

    Example:
        storage = LibSQLStorage(
            url="sqlite+aiosqlite:///./astra.db",
            echo=False,
        )
        await storage.connect()
    """

    def __init__(self, url: str, echo: bool = False):
        """
        Args:
          url: SQLAlchemy async DB URL (sqlite+aiosqlite, libsql+aiosqlite, etc.)
          echo: Whether to echo SQL statements (debug only)
        """

        self.url = url
        self.echo = echo

        self._engine: AsyncEngine | None = None
        self._initialized: bool = False  # tables created ?

    @property
    def engine(self) -> AsyncEngine:
        """Lazy-initialize the async engine."""
        if self._engine is None:
            self._engine = create_async_engine(
                self.url,
                echo=self.echo,
                future=True,
            )

            # Enable foreign keys for ALL connections (not just during table creation)
            @event.listens_for(self._engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        return self._engine

    async def connect(self) -> None:
        """
        Ensure the engine is created, test connection, and auto-create tables.

        Tables are created automatically if they don't exist.
        This does not hold a persistent connection; it just validates DB access.
        """

        # Trigger engine creation
        _ = self.engine

        if self._initialized:
            return

        async with self.engine.begin() as conn:
            # Enable foreign key constraints for SQLite
            await conn.execute(text("PRAGMA foreign_keys = ON"))

            # Create tables if they don't exist
            await conn.run_sync(metadata.create_all)

        self._initialized = True

    async def disconnect(self) -> None:
        """Dispose the engine and reset initialization flag."""

        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._initialized = False

    async def create_tables(self) -> None:
        """
        Create all required tables if they do not exist.

        Uses SQLAlchemy metadata to create astra_threads & astra_messages.
        Safe to call multiple times (idempotent).
        """

        if self._initialized:
            return

        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

        self._initialized = True

    async def execute(
        self, statement: Executable, params: Mapping[str, Any] | None = None
    ) -> int | None:
        """
        Execute a write operation (INSERT/UPDATE/DELETE).

        Args:
           statement: SQLAlchemy Core statement (insert/update/delete/text)
           params: Optional parameter mapping

        Returns:
            Number of rows affected (if available), otherwise -1.
        """
        if not self._initialized:
            await self.connect()

        async with self.engine.begin() as conn:
            result = await conn.execute(statement, params or {})
            rowcount = getattr(result, "rowcount", None)
            return int(rowcount) if rowcount is not None else -1

    async def fetch_all(
        self,
        statement: Select,
        params: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a SELECT and return all rows as list[dict].

        Args:
            statement: SQLAlchemy Select or text-based select
            params: Optional parameter mapping

        Returns:
            List of dict rows, keys = column names
        """
        # Auto-connect if not initialized
        if not self._initialized:
            await self.connect()

        async with self.engine.connect() as conn:
            result = await conn.execute(statement, params or {})
            rows = result.mappings().all()
            return [dict(row) for row in rows]

    async def fetch_one(
        self,
        statement: Select,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Execute a SELECT and return first row (or None).

        Args:
            statement: SQLAlchemy Select or text-based select
            params: Optional parameter mapping

        Returns:
            Single row as dict, or None if no result.
        """
        # Auto-connect if not initialized
        if not self._initialized:
            await self.connect()

        async with self.engine.connect() as conn:
            result = await conn.execute(statement, params or {})
            row = result.mappings().first()
            return dict(row) if row is not None else None

    def _get_table(self, collection_name: str) -> Table:
        """
        Get SQLAlchemy table for collection name.

        Maps collection names to SQLAlchemy Table objects.
        """
        if collection_name == "astra_threads":
            return astra_threads
        elif collection_name == "astra_messages":
            return astra_messages
        elif collection_name == "astra_facts":
            return astra_facts
        elif collection_name == "astra_team_auth":
            return astra_team_auth
        raise ValueError(f"Unknown collection: {collection_name}")

    def build_insert_query(self, collection: str, data: dict[str, Any]) -> Any:
        """
        Build SQL insert query for a single document.

        Args:
            collection: Collection/table name
            data: Document data as dict

        Returns:
            SQLAlchemy insert statement
        """
        table = self._get_table(collection)
        return table.insert().values(**data)

    def build_insert_many_query(self, collection: str, data: list[dict[str, Any]]) -> Any:
        """
        Build SQL bulk insert query for multiple documents.

        Args:
            collection: Collection/table name
            data: List of document data dicts

        Returns:
            SQLAlchemy bulk insert statement
        """
        table = self._get_table(collection)
        return table.insert().values(data)

    def build_select_query(
        self,
        collection: str,
        filter_dict: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Any:
        """
        Build SQL select query with filters, sorting, and pagination.

        Args:
            collection: Collection/table name
            filter_dict: Filter conditions {field: value}
            sort: Sort order [(field, direction)] where direction is 1 (asc) or -1 (desc)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            SQLAlchemy select statement
        """
        table = self._get_table(collection)
        stmt = select(table)

        # Soft-deleted records are filtered out
        stmt = stmt.where(table.c.deleted_at.is_(None))

        # Apply filters
        if filter_dict:
            for key, value in filter_dict.items():
                stmt = stmt.where(table.c[key] == value)

        if sort:
            for field, direction in sort:
                if direction == -1:
                    stmt = stmt.order_by(table.c[field].desc())
                else:
                    stmt = stmt.order_by(table.c[field].asc())

        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None and offset > 0:
            stmt = stmt.offset(offset)

        return stmt

    def build_update_query(
        self,
        collection: str,
        filter_dict: dict[str, Any],
        update_data: dict[str, Any],
        update_many: bool = False,  # Ignored for SQL - always updates all matching rows
    ) -> Any:
        """
        Build SQL update query.

        Args:
            collection: Collection/table name
            filter_dict: Filter conditions {field: value}
            update_data: Fields to update {field: new_value}
            update_many: Ignored for SQL (always updates all matching rows)

        Returns:
            SQLAlchemy update statement
        """
        table = self._get_table(collection)
        stmt = update(table).values(**update_data)

        for key, value in filter_dict.items():
            stmt = stmt.where(table.c[key] == value)

        return stmt

    def build_delete_query(self, collection: str, filter_dict: dict[str, Any]) -> Any:
        """
        Build SQL delete query.

        Args:
            collection: Collection/table name
            filter_dict: Filter conditions {field: value}

        Returns:
            SQLAlchemy delete statement
        """
        table = self._get_table(collection)
        stmt = delete(table)

        for key, value in filter_dict.items():
            stmt = stmt.where(table.c[key] == value)

        return stmt

    async def get_max_value(self, collection: str, field: str, filter_dict: dict[str, Any]) -> int:
        """
        Get maximum value of a field using SQL MAX aggregation.

        Args:
            collection: Collection/table name
            field: Field name to get max value of
            filter_dict: Filter conditions {field: value}

        Returns:
            Maximum value as int (0 if no records found)
        """
        table = self._get_table(collection)
        stmt = select(func.max(table.c[field]).label("max_seq"))

        for key, value in filter_dict.items():
            stmt = stmt.where(table.c[key] == value)

        row = await self.fetch_one(stmt)
        return int(row["max_seq"]) if row and row.get("max_seq") is not None else 0

    async def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the SQLite database.

        Args:
            table_name: Name of the table to check

        Returns:
            True if the table exists, False otherwise
        """
        if not self._initialized:
            await self.connect()

        async with self.engine.connect() as conn:
            result = await conn.execute(
                text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            )
            row = result.fetchone()
            return row is not None
