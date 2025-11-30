"""
Test pagination and filtering functionality.

Database Parts Tested:
- MessageStore.get_by_thread with limit parameter
- Sequence-based ordering
- Empty result handling
- Multi-thread data isolation

Tests:
- Message pagination with different limits
- Empty results for new/non-existent threads  
- Limit edge cases (0, >total, None)
- Sequence ordering verification
- Thread isolation (messages don't cross threads)
- Large dataset pagination (1000+ messages)
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


async def test_message_pagination():
    """Test paginating through messages."""
    print("\n=== Test: Message Pagination ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_pagination.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Pagination Test")
    await thread_store.create(thread)

    # Create 50 messages
    for i in range(50):
        seq = await message_store.get_next_sequence(thread.id)
        msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread.id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}",
            sequence=seq,
        )
        await message_store.add(msg)

    # Test pagination with limit
    page1 = await message_store.get_by_thread(thread.id, limit=10)
    print(f"PASS: Page 1: {len(page1)} messages (expected 10)")
    assert len(page1) == 10

    page2 = await message_store.get_by_thread(thread.id, limit=20)
    print(f"PASS: Page 2: {len(page2)} messages (expected 20)")
    assert len(page2) == 20

    # Verify ordering (should be by sequence ascending)
    all_msgs = await message_store.get_by_thread(thread.id)
    sequences = [msg.sequence for msg in all_msgs]
    assert sequences == sorted(sequences), "Messages not ordered by sequence!"
    print("PASS: Messages correctly ordered by sequence")

    await storage.disconnect()
    os.remove("./test_pagination.db")


async def test_empty_results():
    """Test pagination with empty results."""
    print("\n=== Test: Empty Results ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_empty.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Empty Test")
    await thread_store.create(thread)

    # Get messages from empty thread
    messages = await message_store.get_by_thread(thread.id)
    print(f"PASS: Empty thread returned {len(messages)} messages (expected 0)")
    assert len(messages) == 0

    # Get non-existent thread
    messages = await message_store.get_by_thread("non-existent-thread")
    print(f"PASS: Non-existent thread returned {len(messages)} messages (expected 0)")
    assert len(messages) == 0

    await storage.disconnect()
    os.remove("./test_empty.db")


async def test_limit_edge_cases():
    """Test edge cases for limit parameter."""
    print("\n=== Test: Limit Edge Cases ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_limit.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Limit Test")
    await thread_store.create(thread)

    # Create 10 messages
    for i in range(10):
        seq = await message_store.get_next_sequence(thread.id)
        msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread.id,
            role="user",
            content=f"Message {i}",
            sequence=seq,
        )
        await message_store.add(msg)

    # Test limit = 0
    messages = await message_store.get_by_thread(thread.id, limit=0)
    print(f"PASS: Limit=0 returned {len(messages)} messages (expected 0)")
    assert len(messages) == 0

    # Test limit > total
    messages = await message_store.get_by_thread(thread.id, limit=100)
    print(f"PASS: Limit=100 returned {len(messages)} messages (expected 10)")
    assert len(messages) == 10

    # Test limit = None (all)
    messages = await message_store.get_by_thread(thread.id, limit=None)
    print(f"PASS: Limit=None returned {len(messages)} messages (expected 10)")
    assert len(messages) == 10

    await storage.disconnect()
    os.remove("./test_limit.db")


async def test_sequence_ordering():
    """Test that messages are always ordered by sequence."""
    print("\n=== Test: Sequence Ordering ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_ordering.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Ordering Test")
    await thread_store.create(thread)

    # Create messages with explicit sequences (not in order)
    sequences = [5, 1, 3, 2, 4]
    for seq in sequences:
        msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread.id,
            role="user",
            content=f"Message {seq}",
            sequence=seq,
        )
        await message_store.add(msg)

    # Retrieve and verify ordering
    messages = await message_store.get_by_thread(thread.id)
    retrieved_seqs = [msg.sequence for msg in messages]

    print(f"PASS: Retrieved sequences: {retrieved_seqs}")
    print("PASS: Expected: [1, 2, 3, 4, 5]")
    assert retrieved_seqs == [1, 2, 3, 4, 5], "Messages not ordered correctly!"

    await storage.disconnect()
    os.remove("./test_ordering.db")


async def test_multiple_threads():
    """Test pagination across multiple threads."""
    print("\n=== Test: Multiple Threads ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_multi_thread.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    # Create 3 threads with different message counts
    thread_ids = [f"thread-{uuid4().hex[:8]}" for _ in range(3)]
    thread_counts = {
        thread_ids[0]: 10,
        thread_ids[1]: 20,
        thread_ids[2]: 5,
    }

    for thread_id, count in thread_counts.items():
        thread = Thread(id=thread_id, title=f"Thread {thread_id}")
        await thread_store.create(thread)

        for i in range(count):
            seq = await message_store.get_next_sequence(thread_id)
            msg = Message(
                id=f"msg-{uuid4().hex[:12]}",
                thread_id=thread_id,
                role="user",
                content=f"Message {i}",
                sequence=seq,
            )
            await message_store.add(msg)

    # Verify each thread has correct count
    for thread_id, expected_count in thread_counts.items():
        messages = await message_store.get_by_thread(thread_id)
        print(
            f"PASS: Thread {thread_id[:12]}... has {len(messages)} messages (expected {expected_count})"
        )
        assert len(messages) == expected_count

    await storage.disconnect()
    os.remove("./test_multi_thread.db")


async def test_large_pagination():
    """Test pagination with large dataset."""
    print("\n=== Test: Large Pagination ===")

    storage = LibSQLStorage(url="sqlite+aiosqlite:///./test_large_page.db")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Large Pagination Test")
    await thread_store.create(thread)

    # Create 1000 messages
    print("Creating 1000 messages...")
    for i in range(1000):
        seq = await message_store.get_next_sequence(thread.id)
        msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread.id,
            role="user",
            content=f"Message {i}",
            sequence=seq,
        )
        await message_store.add(msg)

    # Test different page sizes
    for page_size in [10, 50, 100, 500]:
        messages = await message_store.get_by_thread(thread.id, limit=page_size)
        print(f"PASS: Retrieved {len(messages)} messages with limit={page_size}")
        assert len(messages) == page_size

    # Get all
    all_messages = await message_store.get_by_thread(thread.id)
    print(f"PASS: Retrieved all {len(all_messages)} messages (expected 1000)")
    assert len(all_messages) == 1000

    await storage.disconnect()
    os.remove("./test_large_page.db")


async def main():
    print("=" * 60)
    print("Pagination & Filtering Test Suite")
    print("=" * 60)

    await test_message_pagination()
    await test_empty_results()
    await test_limit_edge_cases()
    await test_sequence_ordering()
    await test_multiple_threads()
    await test_large_pagination()

    print("\n" + "=" * 60)
    print("PASS: All pagination tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
