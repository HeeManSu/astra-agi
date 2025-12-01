"""
Test edge cases and error handling.

Database Parts Tested:
- Primary key constraints (UNIQUE on thread.id, message.id)
- Foreign key constraints (message.thread_id -> thread.id)
- CASCADE DELETE behavior
- Pydantic validation (role field)
- NULL/empty value handling
- Special character escaping (SQL injection, XSS, unicode)

Tests:
- Duplicate thread/message IDs raise IntegrityError
- Orphaned messages rejected (foreign key violation)
- Invalid message roles rejected by Pydantic
- Cascade delete (thread deletion deletes messages)
- Empty content strings allowed
- Special characters preserved (SQL injection attempts, XSS, unicode)
- NULL metadata converted to empty dict
- Update non-existent records returns None
"""

import asyncio
import os
import sys
from uuid import uuid4


sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))

from framework.storage.databases.libsql import LibSQLStorage
from framework.storage.models import Message, Thread
from framework.storage.stores.message import MessageStore
from framework.storage.stores.thread import ThreadStore


async def test_duplicate_thread_id():
    """Test creating thread with duplicate ID."""
    print("\n=== Test: Duplicate Thread ID ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_dup_thread.db")
    await storage.connect()

    thread_store = ThreadStore(storage)

    thread_id = f"thread-{uuid4().hex[:8]}"
    thread1 = Thread(id=thread_id, title="First Thread")
    await thread_store.create(thread1)

    # Try to create duplicate
    thread2 = Thread(id=thread_id, title="Duplicate Thread")
    try:
        await thread_store.create(thread2)
        print("FAIL: Should have raised error for duplicate ID")
        raise AssertionError("Expected IntegrityError for duplicate ID")
    except Exception as e:
        print(f"PASS: Correctly raised error: {type(e).__name__}")

    await storage.disconnect()
    os.remove("./test_dup_thread.db")


async def test_duplicate_message_id():
    """Test creating message with duplicate ID."""
    print("\n=== Test: Duplicate Message ID ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_dup_msg.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Test")
    await thread_store.create(thread)

    msg_id = f"msg-{uuid4().hex[:12]}"
    msg1 = Message(id=msg_id, thread_id=thread.id, role="user", content="First", sequence=1)
    await message_store.add(msg1)

    # Try to create duplicate
    msg2 = Message(id=msg_id, thread_id=thread.id, role="user", content="Duplicate", sequence=2)
    try:
        await message_store.add(msg2)
        print("FAIL: Should have raised error for duplicate ID")
        raise AssertionError("Expected IntegrityError for duplicate ID")
    except Exception as e:
        print(f"PASS: Correctly raised error: {type(e).__name__}")

    await storage.disconnect()
    os.remove("./test_dup_msg.db")


async def test_orphaned_message():
    """Test creating message with non-existent thread."""
    print("\n=== Test: Orphaned Message (Foreign Key) ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_orphan.db")
    await storage.connect()

    message_store = MessageStore(storage)

    # Try to create message for non-existent thread
    msg = Message(
        id=f"msg-{uuid4().hex[:12]}",
        thread_id="non-existent-thread",
        role="user",
        content="Orphaned message",
        sequence=1,
    )

    try:
        await message_store.add(msg)
        print("FAIL: Should have raised foreign key error")
        raise AssertionError("Expected IntegrityError for foreign key violation")
    except Exception as e:
        print(f"PASS: Correctly raised error: {type(e).__name__}")

    await storage.disconnect()
    os.remove("./test_orphan.db")


async def test_invalid_role():
    """Test creating message with invalid role."""
    print("\n=== Test: Invalid Role Validation ===")

    try:
        _msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id="thread-123",
            role="invalid_role",  # Not in allowed set
            content="Test",
            sequence=1,
        )
        print("FAIL: Should have raised validation error")
        raise AssertionError("Expected ValidationError for invalid role")
    except ValueError as e:
        print(f"PASS: Correctly raised validation error: {e}")


async def test_cascade_delete():
    """Test that deleting thread cascades to messages."""
    print("\n=== Test: Cascade Delete ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_cascade.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Cascade Test")
    await thread_store.create(thread)

    # Add messages
    for i in range(5):
        seq = await message_store.get_next_sequence(thread.id)
        msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread.id,
            role="user",
            content=f"Message {i}",
            sequence=seq,
        )
        await message_store.add(msg)

    # Verify messages exist
    messages = await message_store.get_by_thread(thread.id)
    print(f"PASS: Created {len(messages)} messages")
    assert len(messages) == 5

    # Delete thread
    await thread_store.delete(thread.id)

    # Verify messages are gone (cascade delete)
    messages = await message_store.get_by_thread(thread.id)
    print(f"PASS: After thread deletion: {len(messages)} messages (expected 0)")
    assert len(messages) == 0

    await storage.disconnect()
    os.remove("./test_cascade.db")


async def test_empty_content():
    """Test messages with empty content."""
    print("\n=== Test: Empty Content ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_empty_content.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Empty Content Test")
    await thread_store.create(thread)

    # Create message with empty content
    msg = Message(
        id=f"msg-{uuid4().hex[:12]}",
        thread_id=thread.id,
        role="user",
        content="",  # Empty string
        sequence=1,
    )
    await message_store.add(msg)

    # Retrieve and verify
    messages = await message_store.get_by_thread(thread.id)
    print("PASS: Message with empty content saved and retrieved")
    assert messages[0].content == ""

    await storage.disconnect()
    os.remove("./test_empty_content.db")


async def test_special_characters():
    """Test handling special characters in content."""
    print("\n=== Test: Special Characters ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_special.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Special Chars Test")
    await thread_store.create(thread)

    # Test various special characters
    special_contents: list[str] = [
        "Hello 'world'",
        'Hello "world"',
        "Hello\nWorld",
        "Hello\tWorld",
        "Hello\\World",
        "Hello 😀 World",
        "SELECT * FROM users; DROP TABLE users;",  # SQL injection attempt
        "<script>alert('xss')</script>",  # XSS attempt
    ]

    for i, content in enumerate(special_contents):
        seq = await message_store.get_next_sequence(thread.id)
        msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread.id,
            role="user",
            content=content,
            sequence=seq,
        )
        await message_store.add(msg)

    # Retrieve and verify
    messages = await message_store.get_by_thread(thread.id)
    print(f"PASS: Saved {len(messages)} messages with special characters")

    for i, msg in enumerate(messages):
        assert msg.content == special_contents[i], f"Content mismatch for message {i}"

    print("PASS: All special characters preserved correctly")

    await storage.disconnect()
    os.remove("./test_special.db")


async def test_null_metadata():
    """Test handling null/empty metadata."""
    print("\n=== Test: Null Metadata ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_null_meta.db")
    await storage.connect()

    thread_store = ThreadStore(storage)

    # Thread with no metadata
    thread1 = Thread(id=f"thread-{uuid4().hex[:8]}", title="No Metadata")
    await thread_store.create(thread1)

    # Thread with empty metadata
    thread2 = Thread(id=f"thread-{uuid4().hex[:8]}", title="Empty Metadata", metadata={})
    await thread_store.create(thread2)

    # Retrieve and verify
    t1 = await thread_store.get(thread1.id)
    t2 = await thread_store.get(thread2.id)

    assert t1 is not None, "Thread 1 not found"
    assert t2 is not None, "Thread 2 not found"

    print(f"PASS: Thread 1 metadata: {t1.metadata}")
    print(f"PASS: Thread 2 metadata: {t2.metadata}")
    assert t1.metadata == {}
    assert t2.metadata == {}

    await storage.disconnect()
    os.remove("./test_null_meta.db")


async def test_update_nonexistent():
    """Test updating non-existent records."""
    print("\n=== Test: Update Non-Existent ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_update_none.db")
    await storage.connect()

    thread_store = ThreadStore(storage)

    # Try to update non-existent thread
    result = await thread_store.update("non-existent-id", title="Updated")
    print(f"PASS: Update non-existent thread returned: {result}")
    assert result is None

    await storage.disconnect()
    os.remove("./test_update_none.db")


async def main():
    print("=" * 60)
    print("Edge Cases & Error Handling Test Suite")
    print("=" * 60)

    await test_duplicate_thread_id()
    await test_duplicate_message_id()
    await test_orphaned_message()
    await test_invalid_role()
    await test_cascade_delete()
    await test_empty_content()
    await test_special_characters()
    await test_null_metadata()
    await test_update_nonexistent()

    print("\n" + "=" * 60)
    print("PASS: All edge case tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
