"""
Test thread update and archiving operations.

Database Parts Tested:
- ThreadStore update operations
- Partial updates (title only, metadata only)
- Soft delete (is_archived flag)
- Bulk updates (transaction handling)
- Concurrent updates (race condition handling)

Tests:
- Updating thread title
- Updating thread metadata
- Thread archiving (soft delete)
- Bulk thread updates
- Concurrent thread updates
"""

import asyncio
import os
from uuid import uuid4

from framework.storage.databases.libsql import LibSQLStorage
from framework.storage.models import Thread
from framework.storage.stores.thread import ThreadStore


async def test_update_thread_title():
    """
    Test updating a thread's title.

    Example:
      Initial: "Untitled"
      Updated: "Q&A Session"
    """
    print("\n=== Test: Update Thread Title ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_update_title.db")
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

    await storage.disconnect()
    os.remove("./test_update_title.db")


async def test_update_thread_metadata():
    """
    Test updating thread metadata.

    Example:
      Add user_id, tags, and preferences to metadata
    """
    print("\n=== Test: Update Thread Metadata ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_update_meta.db")
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

    await storage.disconnect()
    os.remove("./test_update_meta.db")


async def test_archive_thread():
    """
    Test archiving threads (soft delete).

    Example:
      Mark old conversation as archived
      is_archived: False -> True
    """
    print("\n=== Test: Archive Thread ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_archive.db")
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

    await storage.disconnect()
    os.remove("./test_archive.db")


async def test_bulk_thread_updates():
    """
    Test updating multiple threads.

    Example:
      Archive all threads older than 30 days
      Update metadata for batch of threads
    """
    print("\n=== Test: Bulk Thread Updates ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_bulk_update.db")
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

    await storage.disconnect()
    os.remove("./test_bulk_update.db")


async def test_concurrent_thread_updates():
    """
    Test concurrent updates to different threads.

    Example:
      Multiple users renaming their conversations simultaneously
    """
    print("\n=== Test: Concurrent Thread Updates ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_concurrent.db")
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

    await storage.disconnect()
    os.remove("./test_concurrent.db")


async def main():
    print("=" * 60)
    print("Thread Operations Test Suite")
    print("=" * 60)

    await test_update_thread_title()
    await test_update_thread_metadata()
    await test_archive_thread()
    await test_bulk_thread_updates()
    await test_concurrent_thread_updates()

    print("\n" + "=" * 60)
    print("PASS: All thread operation tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
