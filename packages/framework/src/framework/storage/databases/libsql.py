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
    event,
    func,
    text,
)
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.sql.schema import ForeignKey

from framework.storage.base import StorageBackend


metadata = MetaData()

astra_threads = Table(
    "astra_threads",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("resource_id", String(64), nullable=True, index=True),
    Column("title", String(255), nullable=True),
    Column("metadata", JSON, nullable=True),
    Column("is_archived", Boolean, nullable=False, server_default="0"),
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
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    # Indexes for common query patterns
    Index("idx_messages_thread_sequence", "thread_id", "sequence"),
    Index("idx_messages_thread_role", "thread_id", "role"),
    Index("idx_messages_created_at", "created_at"),
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
        # Delegate to connect() which handles table creation and version tracking
        await self.connect()

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
        # Auto-connect if not initialized
        if not self._initialized:
            await self.connect()

        async with self.engine.begin() as conn:
            result = await conn.execute(statement, params or {})
            rowcount = getattr(result, "rowcount", None)
            return int(rowcount) if rowcount is not None else -1

    async def execute_in_transaction(
        self, statements: list[Executable], params: list[Mapping[str, Any] | None] | None = None
    ) -> list[int]:
        """
        Execute multiple statements in a single transaction.

        Args:
            statements: List of SQLAlchemy Core statements
            params: Optional list of parameter mappings (one per statement)

        Returns:
            List of row counts for each statement

        Note: SQLite/LibSQL supports transactions, so this ensures atomicity.
        """
        param_list: list[Mapping[str, Any] | None] = (
            params if params is not None else [None] * len(statements)
        )

        results = []
        async with self.engine.begin() as conn:
            for stmt, param in zip(statements, param_list, strict=True):
                result = await conn.execute(stmt, param or {})
                rowcount = getattr(result, "rowcount", None)
                results.append(int(rowcount) if rowcount is not None else -1)
        return results

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

    async def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise
        """
        # Auto-connect if not initialized
        if not self._initialized:
            await self.connect()

        async with self.engine.connect() as conn:
            stmt = text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :table_name")
            result = await conn.execute(stmt, {"table_name": table_name})
            return result.scalar() is not None
