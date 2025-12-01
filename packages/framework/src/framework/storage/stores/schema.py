from sqlalchemy import Table, select, update

from framework.storage.base import StorageBackend


class SchemaVersion:
    """Represents a schema version record (not a Pydantic model, just a data class)."""

    def __init__(self, table_name: str, version: str):
        self.table_name = table_name
        self.version = version


class SchemaStore:
    """
    Manages database schema versions and migrations.
    """

    def __init__(self, storage: StorageBackend, versions_table: Table):
        self.storage = storage
        self.versions_table = versions_table

    async def get_latest_schema_version(self, table_name: str) -> str | None:
        """Get the current version of a table's schema."""
        stmt = select(self.versions_table.c.version).where(
            self.versions_table.c.table_name == table_name
        )
        row = await self.storage.fetch_one(stmt)
        if row:
            return row["version"]
        return None

    async def upsert_schema_version(self, table_name: str, version: str) -> None:
        """Update or insert the schema version for a table."""
        # Check if exists
        current = await self.get_latest_schema_version(table_name)

        if current is None:
            # Insert
            stmt = self.versions_table.insert().values(table_name=table_name, version=version)
            await self.storage.execute(stmt)
        else:
            # Update
            stmt = (
                update(self.versions_table)
                .where(self.versions_table.c.table_name == table_name)
                .values(version=version)
            )
            await self.storage.execute(stmt)

    async def check_schema_version(self, table_name: str, expected_version: str) -> bool:
        """
        Check if the table schema matches the expected version.
        Returns True if match, False otherwise.
        """
        current = await self.get_latest_schema_version(table_name)
        return current == expected_version
