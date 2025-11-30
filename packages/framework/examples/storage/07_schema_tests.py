"""
Test schema version management.

Database Parts Tested:
- SchemaStore (astra_schema_versions table)
- Upsert operations (INSERT vs UPDATE)
- Version retrieval and checking
- Multi-table version tracking

Tests:
- Schema version upsert (insert or update)
- Schema version retrieval
- Version checking and validation
- Multiple table schema tracking
"""

import asyncio
import os

from framework.storage.databases.libsql import LibSQLStorage, astra_schema_versions
from framework.storage.stores.schema import SchemaStore


async def test_schema_version_upsert():
    """
    Test upserting schema versions (insert or update).

    Example:
      Initial: astra_threads v1.0.0
      Update:  astra_threads v1.1.0
    """
    print("\n=== Test: Schema Version Upsert ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_schema.db")
    await storage.connect()

    schema_store = SchemaStore(storage, astra_schema_versions)

    # Insert initial version
    await schema_store.upsert_schema_version("astra_threads", "1.0.0")
    print("PASS: Inserted astra_threads v1.0.0")

    # Update to new version
    await schema_store.upsert_schema_version("astra_threads", "1.1.0")
    print("PASS: Updated astra_threads to v1.1.0")

    # Verify it was updated (not duplicated)
    version = await schema_store.get_latest_schema_version("astra_threads")
    print(f"PASS: Latest version: {version}")
    assert version == "1.1.0", f"Expected 1.1.0, got {version}"

    await storage.disconnect()
    os.remove("./test_schema.db")


async def test_multiple_table_versions():
    """
    Test tracking versions for multiple tables.

    Example:
      astra_threads  v1.0.0
      astra_messages v1.2.0
      custom_table   v2.0.0
    """
    print("\n=== Test: Multiple Table Versions ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_multi_schema.db")
    await storage.connect()

    schema_store = SchemaStore(storage, astra_schema_versions)

    # Set versions for different tables
    tables_versions = {
        "astra_threads": "1.0.0",
        "astra_messages": "1.2.0",
        "custom_table": "2.0.0",
    }

    for table, version in tables_versions.items():
        await schema_store.upsert_schema_version(table, version)
        print(f"PASS: Set {table} to v{version}")

    # Verify each version
    for table, expected_version in tables_versions.items():
        actual = await schema_store.get_latest_schema_version(table)
        print(f"PASS: {table}: {actual}")
        assert actual == expected_version

    await storage.disconnect()
    os.remove("./test_multi_schema.db")


async def test_check_schema_version():
    """
    Test checking if schema version matches expected.

    Example:
      Check if astra_threads is at v1.0.0
      Returns True if matches, False otherwise
    """
    print("\n=== Test: Check Schema Version ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_check_schema.db")
    await storage.connect()

    schema_store = SchemaStore(storage, astra_schema_versions)

    # Set version
    await schema_store.upsert_schema_version("astra_threads", "1.0.0")

    # Check correct version
    is_correct = await schema_store.check_schema_version("astra_threads", "1.0.0")
    print(f"PASS: Version 1.0.0 matches: {is_correct}")
    assert is_correct is True

    # Check wrong version
    is_wrong = await schema_store.check_schema_version("astra_threads", "2.0.0")
    print(f"PASS: Version 2.0.0 matches: {is_wrong}")
    assert is_wrong is False

    await storage.disconnect()
    os.remove("./test_check_schema.db")


async def test_missing_table_version():
    """
    Test getting version for non-existent table.

    Example:
      Query version for 'unknown_table'
      Should return None (table not tracked)
    """
    print("\n=== Test: Missing Table Version ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_missing.db")
    await storage.connect()

    schema_store = SchemaStore(storage, astra_schema_versions)

    # Try to get version for non-existent table
    version = await schema_store.get_latest_schema_version("unknown_table")
    print(f"PASS: Unknown table version: {version}")
    assert version is None, "Should return None for unknown table"

    await storage.disconnect()
    os.remove("./test_missing.db")


async def main():
    print("=" * 60)
    print("Schema Version Management Test Suite")
    print("=" * 60)

    await test_schema_version_upsert()
    await test_multiple_table_versions()
    await test_check_schema_version()
    await test_missing_table_version()

    print("\n" + "=" * 60)
    print("PASS: All schema tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
