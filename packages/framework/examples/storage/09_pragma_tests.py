"""
Test foreign key pragma enforcement.

Database Parts Tested:
- SQLite PRAGMA foreign_keys=ON
- IntegrityError handling
- Cascade delete behavior (ON DELETE CASCADE)
- Cross-table referential integrity

Tests:
- Verify PRAGMA foreign_keys is enabled
- Test orphaned message rejection
- Test cascade delete behavior
- Test referential integrity enforcement
"""

import asyncio
import os
from uuid import uuid4

from framework.storage.databases.libsql import LibSQLStorage
from framework.storage.models import Message, Thread
from framework.storage.stores.message import MessageStore
from framework.storage.stores.thread import ThreadStore
from sqlalchemy.exc import IntegrityError


async def test_pragma_enabled():
    """
    Test that PRAGMA foreign_keys is ON.

    Example:
      Query SQLite: PRAGMA foreign_keys
      Should return: 1 (enabled)
    """
    print("\n=== Test: PRAGMA Foreign Keys Enabled ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_pragma.db")
    await storage.connect()

    # Check pragma directly
    from sqlalchemy import text

    async with storage.engine.begin() as conn:
        result = await conn.execute(text("PRAGMA foreign_keys"))
        pragma_value = result.scalar()

    print(f"PASS: PRAGMA foreign_keys = {pragma_value}")
    assert pragma_value == 1, "Foreign keys should be enabled (1)"

    await storage.disconnect()
    os.remove("./test_pragma.db")


async def test_orphaned_message_rejected():
    """
    Test that messages for non-existent threads are rejected.

    Example:
      Try to insert message for 'thread-999' (doesn't exist)
      Should raise: IntegrityError (FOREIGN KEY constraint failed)
    """
    print("\n=== Test: Orphaned Message Rejected ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_orphan.db")
    await storage.connect()

    message_store = MessageStore(storage)

    # Try to create message for non-existent thread
    msg = Message(
        id=f"msg-{uuid4().hex[:12]}",
        thread_id="thread-nonexistent",  # This thread doesn't exist!
        role="user",
        content="This should fail",
        sequence=1,
    )

    try:
        await message_store.add(msg)
        print("FAIL: Should have raised IntegrityError")
        assert False, "Expected IntegrityError"
    except IntegrityError:
        print("PASS: Correctly rejected orphaned message")
        print("   Error: FOREIGN KEY constraint failed")

    await storage.disconnect()
    os.remove("./test_orphan.db")


async def test_cascade_delete_verified():
    """
    Test that deleting thread cascades to messages.

    Example:
      1. Create thread with 3 messages
      2. Delete thread
      3. Verify all 3 messages are deleted automatically
    """
    print("\n=== Test: Cascade Delete Verified ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_cascade.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    # Create thread
    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Test Cascade")
    await thread_store.create(thread)

    # Add messages
    for i in range(3):
        seq = await message_store.get_next_sequence(thread.id)
        msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread.id,
            role="user",
            content=f"Message {i}",
            sequence=seq,
        )
        await message_store.add(msg)

    print("PASS: Created thread with 3 messages")

    # Verify messages exist
    messages_before = await message_store.get_by_thread(thread.id)
    assert len(messages_before) == 3

    # Delete thread
    await thread_store.delete(thread.id)
    print("PASS: Deleted thread")

    # Verify messages are gone (CASCADE DELETE worked)
    messages_after = await message_store.get_by_thread(thread.id)
    print(f"PASS: Messages after delete: {len(messages_after)} (expected 0)")
    assert len(messages_after) == 0, "Messages should be deleted via cascade"

    await storage.disconnect()
    os.remove("./test_cascade.db")


async def test_referential_integrity():
    """
    Test referential integrity across multiple operations.

    Example:
      1. Create thread A
      2. Add message to thread A (should work)
      3. Try to add message to thread B (doesn't exist, should fail)
      4. Delete thread A
      5. Try to query messages for thread A (should be empty)
    """
    print("\n=== Test: Referential Integrity ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_integrity.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    # Step 1: Create thread A
    thread_a = Thread(id=f"thread-{uuid4().hex[:8]}", title="Thread A")
    await thread_store.create(thread_a)
    print("PASS: Created thread A")

    # Step 2: Add message to thread A (should work)
    seq = await message_store.get_next_sequence(thread_a.id)
    msg_a = Message(
        id=f"msg-{uuid4().hex[:12]}",
        thread_id=thread_a.id,
        role="user",
        content="Valid message",
        sequence=seq,
    )
    await message_store.add(msg_a)
    print("PASS: Added message to thread A")

    # Step 3: Try to add message to non-existent thread B
    msg_b = Message(
        id=f"msg-{uuid4().hex[:12]}",
        thread_id="thread-nonexistent-b",
        role="user",
        content="Invalid message",
        sequence=1,
    )

    try:
        await message_store.add(msg_b)
        assert False, "Should have failed"
    except IntegrityError:
        print("PASS: Correctly rejected message for non-existent thread B")

    # Step 4: Delete thread A
    await thread_store.delete(thread_a.id)
    print("PASS: Deleted thread A")

    # Step 5: Verify messages for thread A are gone
    messages = await message_store.get_by_thread(thread_a.id)
    print(f"PASS: Messages for deleted thread: {len(messages)} (expected 0)")
    assert len(messages) == 0

    await storage.disconnect()
    os.remove("./test_integrity.db")


async def main():
    print("=" * 60)
    print("Foreign Key PRAGMA Enforcement Test Suite")
    print("=" * 60)

    await test_pragma_enabled()
    await test_orphaned_message_rejected()
    await test_cascade_delete_verified()
    await test_referential_integrity()

    print("\n" + "=" * 60)
    print("PASS: All pragma tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
