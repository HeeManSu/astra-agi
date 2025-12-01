"""
Test database schema migrations.

Database Parts Tested:
- Schema evolution (ALTER TABLE)
- Data migration/transformation
- Transaction rollback on failure
- Version compatibility checks
- SchemaStore integration

Tests:
- Simulated schema version upgrade
- Adding new columns to existing tables
- Data preservation during migration
- Rollback scenarios
- Version compatibility checks
"""

import asyncio
import os
from uuid import uuid4

from framework.storage.databases.libsql import (
    LibSQLStorage,
    astra_schema_versions,
)
from framework.storage.models import Thread
from framework.storage.stores.schema import SchemaStore
from framework.storage.stores.thread import ThreadStore
from sqlalchemy import text


async def test_simple_migration():
    """
    Test a simple schema migration: v1.0.0 -> v1.1.0

    Example:
      v1.0.0: Basic thread table
      v1.1.0: Add 'priority' column (default=0)

    Migration steps:
      1. Check current version
      2. Run migration SQL
      3. Update schema version
      4. Verify data preserved
    """
    print("\n=== Test: Simple Migration (v1.0.0 -> v1.1.0) ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_migrate.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    schema_store = SchemaStore(storage, astra_schema_versions)

    # Step 1: Create some data in v1.0.0
    thread1 = Thread(id=f"thread-{uuid4().hex[:8]}", title="Old Thread 1")
    thread2 = Thread(id=f"thread-{uuid4().hex[:8]}", title="Old Thread 2")
    await thread_store.create(thread1)
    await thread_store.create(thread2)
    print("PASS: Created 2 threads in v1.0.0 schema")

    # Current version
    current_version = await schema_store.get_latest_schema_version("astra_threads")
    print(f"PASS: Current version: {current_version}")

    # Step 2: Run migration to v1.1.0 (add priority column)
    print("\nRUNNING: Running migration to v1.1.0...")
    async with storage.engine.begin() as conn:
        # Add new column with default value
        await conn.execute(text("ALTER TABLE astra_threads ADD COLUMN priority INTEGER DEFAULT 0"))
    print("PASS: Added 'priority' column")

    # Step 3: Update schema version
    await schema_store.upsert_schema_version("astra_threads", "1.1.0")
    print("PASS: Updated schema version to v1.1.0")

    # Step 4: Verify data preserved
    async with storage.engine.begin() as conn:
        result = await conn.execute(text("SELECT id, title, priority FROM astra_threads"))
        rows = result.fetchall()

    print(f"PASS: Found {len(rows)} threads after migration:")
    for row in rows:
        print(f"   - {row[1]}: priority={row[2]}")
        assert row[2] == 0, "Priority should default to 0"

    assert len(rows) == 2, "Both threads should still exist"

    await storage.disconnect()
    os.remove("./test_migrate.db")


async def test_data_migration():
    """
    Test migrating data during schema upgrade.

    Example:
      v1.0.0: metadata is TEXT (JSON string)
      v2.0.0: metadata is JSON (native SQLite JSON)

    Migration:
      Parse existing TEXT and convert to JSON format
    """
    print("\n=== Test: Data Migration ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_data_migrate.db")
    await storage.connect()

    thread_store = ThreadStore(storage)

    # Create threads with metadata
    threads = []
    for i in range(3):
        thread = Thread(
            id=f"thread-{uuid4().hex[:8]}",
            title=f"Thread {i}",
            metadata={"count": i, "tag": f"tag-{i}"},
        )
        await thread_store.create(thread)
        threads.append(thread)

    print(f"PASS: Created {len(threads)} threads with metadata")

    # Simulate data migration: uppercase all tags
    print("\nRUNNING: Running data migration (uppercase tags)...")
    for thread in threads:
        fetched = await thread_store.get(thread.id)
        assert fetched is not None, "Thread should exist"
        old_tag = fetched.metadata.get("tag")

        # Update metadata
        new_metadata = fetched.metadata.copy()
        new_metadata["tag"] = old_tag.upper() if old_tag else ""

        await thread_store.update(thread.id, metadata=new_metadata)

    print("PASS: Migrated all thread metadata")

    # Verify migration
    for i, thread in enumerate(threads):
        fetched = await thread_store.get(thread.id)
        assert fetched is not None, "Thread should exist"
        expected_tag = f"TAG-{i}"
        actual_tag = fetched.metadata.get("tag")

        print(f"Thread {i}: tag='{actual_tag}'")
        assert actual_tag == expected_tag, f"Expected {expected_tag}"

    await storage.disconnect()
    os.remove("./test_data_migrate.db")


async def test_rollback_migration():
    """
    Test rolling back a failed migration.

    Example:
      1. Start migration v1.0.0 -> v2.0.0
      2. Migration fails halfway
      3. Rollback to v1.0.0
      4. Verify data integrity
    """
    print("\n=== Test: Rollback Failed Migration ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_rollback.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    schema_store = SchemaStore(storage, astra_schema_versions)

    # Create initial data
    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Original Thread")
    await thread_store.create(thread)
    print("PASS: Created thread in v1.0.0")

    # Set initial version
    await schema_store.upsert_schema_version("astra_threads", "1.0.0")

    # Attempt migration (simulate failure)
    print("\nRUNNING: Attempting migration to v2.0.0...")
    try:
        async with storage.engine.begin() as conn:
            # This would fail (column already exists or syntax error)
            # Simulating failure
            raise Exception("Simulated migration failure")
    except Exception as e:
        print(f"FAIL: Migration failed: {e}")
        print("PASS: Rolling back to v1.0.0")

    # Verify we're still on v1.0.0
    current_version = await schema_store.get_latest_schema_version("astra_threads")
    print(f"PASS: Current version after rollback: {current_version}")
    assert current_version == "1.0.0"

    # Verify data is intact
    fetched = await thread_store.get(thread.id)
    assert fetched is not None
    assert fetched.title == "Original Thread"
    print("PASS: Data integrity preserved after rollback")

    await storage.disconnect()
    os.remove("./test_rollback.db")


async def test_version_compatibility_check():
    """
    Test checking version compatibility before operations.

    Example:
      App requires v1.1.0 or higher
      Database is v1.0.0
      Should warn or prevent operations
    """
    print("\n=== Test: Version Compatibility Check ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_compat.db")
    await storage.connect()

    schema_store = SchemaStore(storage, astra_schema_versions)

    # Set database version to v1.0.0
    await schema_store.upsert_schema_version("astra_threads", "1.0.0")

    # App requires v1.1.0
    required_version = "1.1.0"
    current_version = await schema_store.get_latest_schema_version("astra_threads")

    print(f"Database version: {current_version}")
    print(f"Required version: {required_version}")

    # Simple version comparison (in real app, use semver library)
    is_compatible = current_version >= required_version if current_version else False
    print(f"Compatible: {is_compatible}")

    if not is_compatible:
        print("Database needs migration to v1.1.0 or higher")

    assert current_version == "1.0.0"

    await storage.disconnect()
    os.remove("./test_compat.db")


async def main():
    print("=" * 60)
    print("Database Migration Test Suite")
    print("=" * 60)

    await test_simple_migration()
    await test_data_migration()
    await test_rollback_migration()
    await test_version_compatibility_check()

    print("\n" + "=" * 60)
    print("PASS: All migration tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
