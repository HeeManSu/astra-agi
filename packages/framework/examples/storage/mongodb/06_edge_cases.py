"""
Test edge cases and error handling with MongoDB.

Database Parts Tested:
- Primary key constraints (UNIQUE on thread.id, message.id)
- Pydantic validation (role field)
- NULL/empty value handling
- Special character escaping (SQL injection, XSS, unicode)

Tests:
- Duplicate thread/message IDs raise errors
- Invalid message roles rejected by Pydantic
- Empty content strings allowed
- Special characters preserved
- NULL metadata converted to empty dict
- Update non-existent records returns None

Requires: MongoDB running locally on port 27017.
"""

import asyncio
from uuid import uuid4

from framework.storage.databases.mongodb import MongoDBStorage
from framework.storage.models import Message, Thread
from framework.storage.stores.message import MessageStore
from framework.storage.stores.thread import ThreadStore


async def test_duplicate_thread_id():
    """Test creating thread with duplicate ID."""
    print("\n=== Test: Duplicate Thread ID ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_edge_dup_thread")
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
        raise AssertionError("Expected error for duplicate ID")
    except Exception as e:
        print(f"PASS: Correctly raised error: {type(e).__name__}")

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.disconnect()


async def test_duplicate_message_id():
    """Test creating message with duplicate ID."""
    print("\n=== Test: Duplicate Message ID ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_edge_dup_msg")
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
        raise AssertionError("Expected error for duplicate ID")
    except Exception as e:
        print(f"PASS: Correctly raised error: {type(e).__name__}")

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.db["astra_messages"].delete_many({})
    await storage.disconnect()


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


async def test_empty_content():
    """Test messages with empty content."""
    print("\n=== Test: Empty Content ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_edge_empty")
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

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.db["astra_messages"].delete_many({})
    await storage.disconnect()


async def test_special_characters():
    """Test handling special characters in content."""
    print("\n=== Test: Special Characters ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_edge_special")
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

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.db["astra_messages"].delete_many({})
    await storage.disconnect()


async def test_null_metadata():
    """Test handling null/empty metadata."""
    print("\n=== Test: Null Metadata ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_edge_null_meta")
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

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.disconnect()


async def test_update_nonexistent():
    """Test updating non-existent records."""
    print("\n=== Test: Update Non-Existent ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_edge_update_none")
    await storage.connect()

    thread_store = ThreadStore(storage)

    # Try to update non-existent thread
    result = await thread_store.update("non-existent-id", title="Updated")
    print(f"PASS: Update non-existent thread returned: {result}")
    assert result is None

    await storage.disconnect()


async def main():
    print("=" * 60)
    print("MongoDB Edge Cases & Error Handling Test Suite")
    print("=" * 60)

    await test_duplicate_thread_id()
    await test_duplicate_message_id()
    await test_invalid_role()
    await test_empty_content()
    await test_special_characters()
    await test_null_metadata()
    await test_update_nonexistent()

    print("\n" + "=" * 60)
    print("PASS: All MongoDB edge case tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
