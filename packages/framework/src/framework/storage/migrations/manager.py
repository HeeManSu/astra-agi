"""
Migration Manager for Astra Storage.

Handles schema versioning and migration execution.
"""

from collections.abc import Callable
from typing import Any

from sqlalchemy import select

from framework.storage.base import StorageBackend
from framework.storage.databases.libsql import astra_schema_versions
from framework.storage.stores.schema import SchemaStore


class Migration:
    """Represents a single migration."""

    def __init__(
        self,
        version: str,
        description: str,
        up: Callable[[StorageBackend], Any],
        down: Callable[[StorageBackend], Any] | None = None,
    ):
        """
        Initialize a migration.

        Args:
            version: Version string (e.g., "1.0.0", "1.1.0")
            description: Human-readable description
            up: Async function to apply migration
            down: Optional async function to rollback migration
        """
        self.version = version
        self.description = description
        self.up = up
        self.down = down


class MigrationManager:
    """
    Manages schema migrations for Astra storage.

    Tracks applied migrations and executes pending ones.
    """

    def __init__(self, storage: StorageBackend):
        """
        Initialize migration manager.

        Args:
            storage: Storage backend instance
        """
        self.storage = storage
        self.schema_store = SchemaStore(storage, astra_schema_versions)
        self._migrations: list[Migration] = []

    def register(self, migration: Migration) -> None:
        """Register a migration."""
        self._migrations.append(migration)
        # Sort by version
        self._migrations.sort(key=lambda m: self._version_key(m.version))

    def _version_key(self, version: str) -> tuple[int, ...]:
        """Convert version string to tuple for comparison."""
        return tuple(int(x) for x in version.split("."))

    async def get_applied_versions(self) -> list[str]:
        """Get list of applied migration versions."""
        stmt = (
            select(astra_schema_versions.c.version)
            .where(astra_schema_versions.c.table_name == "__migrations__")
            .order_by(astra_schema_versions.c.version)
        )
        rows = await self.storage.fetch_all(stmt)
        return [row["version"] for row in rows]

    async def get_pending_migrations(self) -> list[Migration]:
        """Get list of migrations that haven't been applied yet."""
        applied = await self.get_applied_versions()
        return [m for m in self._migrations if m.version not in applied]

    async def migrate(self, target_version: str | None = None) -> None:
        """
        Apply pending migrations.

        Args:
            target_version: Optional target version to migrate to.
                          If None, applies all pending migrations.
        """
        pending = await self.get_pending_migrations()

        if target_version:
            target_key = self._version_key(target_version)
            pending = [m for m in pending if self._version_key(m.version) <= target_key]

        if not pending:
            return

        for migration in pending:
            try:
                # Apply migration
                await migration.up(self.storage)

                # Record migration
                await self.schema_store.upsert_schema_version("__migrations__", migration.version)

            except Exception as e:
                raise RuntimeError(
                    f"Migration {migration.version} failed: {migration.description}"
                ) from e

    async def rollback(self, target_version: str) -> None:
        """
        Rollback migrations to a target version.

        Args:
            target_version: Version to rollback to
        """
        applied = await self.get_applied_versions()
        target_key = self._version_key(target_version)

        # Get migrations to rollback (in reverse order)
        to_rollback = [
            m
            for m in reversed(self._migrations)
            if m.version in applied and self._version_key(m.version) > target_key
        ]

        for migration in to_rollback:
            if migration.down is None:
                raise RuntimeError(f"Migration {migration.version} has no rollback function")

            try:
                await migration.down(self.storage)
                # Remove migration record
                from sqlalchemy import delete

                await self.storage.execute(
                    delete(astra_schema_versions).where(
                        astra_schema_versions.c.table_name == "__migrations__",
                        astra_schema_versions.c.version == migration.version,
                    )
                )
            except Exception as e:
                raise RuntimeError(
                    f"Rollback {migration.version} failed: {migration.description}"
                ) from e
