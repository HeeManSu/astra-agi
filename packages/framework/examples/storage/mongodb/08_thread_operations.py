"""
Test thread update and archiving operations with MongoDB.

Database Parts Tested:
- ThreadStore update operations
- Partial updates (title only, metadata only)
- Soft delete (is_archived flag)
- Bulk updates
- Concurrent updates

Tests:
- Updating thread title
- Updating thread metadata
- Thread archiving (soft delete)
- Bulk thread updates
- Concurrent thread updates

Requires: MongoDB running locally on port 27017.
"""

import asyncio
from uuid import uuid4

from framework.storage.databases.mongodb import MongoDBStorage
from framework.storage.models import Thread
from framework.storage.stores.thread import ThreadStore


async def test_update_thread_title():
    """Test updating a thread's title."""
    print("\n=== Test: Update Thread Title ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_thread_title")
    await storage.connect()

    thread_store = ThreadStore(storage)

    # Create thread
    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Untitled")
    await thread_store.create(thread)
    print(f"PASS: Created thread: '{thread.title}'")

    # Update title
    updated = await thread_store.update(thread.id, title="Q&A Session")
    assert updated is not None, "Update should return thread"
    print(f"Updated title to: '{updated.title}'")
    assert updated.title == "Q&A Session"

    # Verify persistence
    fetched = await thread_store.get(thread.id)
    assert fetched is not None
    assert fetched.title == "Q&A Session"

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.disconnect()


async def test_update_thread_metadata():
    """Test updating thread metadata."""
    print("\n=== Test: Update Thread Metadata ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_thread_meta")
    await storage.connect()

    thread_store = ThreadStore(storage)

    # Create thread with initial metadata
    thread = Thread(
        id=f"thread-{uuid4().hex[:8]}",
        title="Test",
        metadata={"version": "1.0"},
    )
    await thread_store.create(thread)
    print(f"PASS: Created with metadata: {thread.metadata}")

    # Update metadata
    new_metadata = {
        "version": "2.0",
        "user_id": "user-123",
        "tags": ["important", "follow-up"],
    }
    updated = await thread_store.update(thread.id, metadata=new_metadata)
    assert updated is not None, "Update should return thread"
    print(f"Updated metadata: {updated.metadata}")

    assert updated.metadata["version"] == "2.0"
    assert updated.metadata["user_id"] == "user-123"
    assert "important" in updated.metadata["tags"]

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.disconnect()


async def test_archive_thread():
    """Test archiving threads (soft delete)."""
    print("\n=== Test: Archive Thread ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_thread_archive")
    await storage.connect()

    thread_store = ThreadStore(storage)

    # Create thread
    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Old Conversation")
    await thread_store.create(thread)
    print(f"PASS: Created thread, is_archived: {thread.is_archived}")
    assert thread.is_archived is False

    # Archive it
    updated = await thread_store.update(thread.id, is_archived=True)
    assert updated is not None, "Update should return thread"
    print(f"Archived thread, is_archived: {updated.is_archived}")
    assert updated.is_archived is True

    # Verify persistence
    fetched = await thread_store.get(thread.id)
    assert fetched is not None
    assert fetched.is_archived is True

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.disconnect()


async def test_bulk_thread_updates():
    """Test updating multiple threads."""
    print("\n=== Test: Bulk Thread Updates ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_thread_bulk")
    await storage.connect()

    thread_store = ThreadStore(storage)

    # Create multiple threads
    thread_ids = []
    for i in range(5):
        thread = Thread(
            id=f"thread-{uuid4().hex[:8]}",
            title=f"Thread {i}",
            is_archived=False,
        )
        await thread_store.create(thread)
        thread_ids.append(thread.id)

    print(f"PASS: Created {len(thread_ids)} threads")

    # Archive all of them
    for tid in thread_ids:
        await thread_store.update(tid, is_archived=True)

    print("PASS: Archived all threads")

    # Verify all are archived
    for tid in thread_ids:
        thread = await thread_store.get(tid)
        assert thread is not None
        assert thread.is_archived is True

    print("All threads confirmed archived")

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.disconnect()


async def test_concurrent_thread_updates():
    """Test concurrent updates to different threads."""
    print("\n=== Test: Concurrent Thread Updates ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_thread_concurrent")
    await storage.connect()

    thread_store = ThreadStore(storage)

    # Create threads
    thread_ids = []
    for i in range(10):
        thread = Thread(id=f"thread-{uuid4().hex[:8]}", title=f"Original {i}")
        await thread_store.create(thread)
        thread_ids.append(thread.id)

    print(f"PASS: Created {len(thread_ids)} threads")

    # Update all concurrently
    async def update_thread(tid, index):
        await thread_store.update(tid, title=f"Updated {index}")

    await asyncio.gather(*[update_thread(tid, i) for i, tid in enumerate(thread_ids)])
    print("PASS: Updated all threads concurrently")

    # Verify updates
    for i, tid in enumerate(thread_ids):
        thread = await thread_store.get(tid)
        assert thread is not None
        assert thread.title == f"Updated {i}"

    print("PASS: All concurrent updates verified")

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.disconnect()


async def main():
    print("=" * 60)
    print("MongoDB Thread Operations Test Suite")
    print("=" * 60)

    await test_update_thread_title()
    await test_update_thread_metadata()
    await test_archive_thread()
    await test_bulk_thread_updates()
    await test_concurrent_thread_updates()

    print("\n" + "=" * 60)
    print("PASS: All MongoDB thread operation tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
