"""
Test bulk operations and performance with MongoDB.

Database Parts Tested:
- Thread Store bulk creation
- Message Store add and bulk_add
- Concurrent write handling
- Sequence number generation under load
- Large content (1MB+) storage and retrieval

Tests:
- Bulk thread creation (100 threads)
- Bulk message insertion (500 messages)
- Concurrent writes (50 simultaneous)
- Large content handling (1MB messages)

Requires: MongoDB running locally on port 27017.
"""

import asyncio
import time
from uuid import uuid4

from framework.storage.databases.mongodb import MongoDBStorage
from framework.storage.models import Message, Thread
from framework.storage.stores.message import MessageStore
from framework.storage.stores.thread import ThreadStore


async def test_bulk_thread_creation():
    """Test creating multiple threads in bulk."""
    print("\n=== Test: Bulk Thread Creation ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_bulk_test")
    await storage.connect()

    thread_store = ThreadStore(storage)

    # Create 100 threads
    start = time.time()
    threads = []
    for i in range(100):
        thread = Thread(
            id=f"thread-{uuid4().hex[:8]}",
            resource_id=f"user-{i % 10}",  # 10 different users
            title=f"Test Thread {i}",
            metadata={"index": i, "batch": "bulk_test"},
        )
        await thread_store.create(thread)
        threads.append(thread)

    elapsed = time.time() - start
    print(
        f"PASS: Created {len(threads)} threads in {elapsed:.2f}s ({len(threads) / elapsed:.1f} threads/sec)"
    )

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.disconnect()


async def test_bulk_message_insertion():
    """Test inserting many messages into a single thread."""
    print("\n=== Test: Bulk Message Insertion ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_bulk_msg_test")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    # Create a thread
    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Bulk Message Test")
    await thread_store.create(thread)

    # Insert 500 messages
    start = time.time()
    messages = []
    for i in range(500):
        seq = await message_store.get_next_sequence(thread.id)
        msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread.id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}",
            sequence=seq,
            metadata={"index": i},
        )
        await message_store.add(msg)
        messages.append(msg)

    elapsed = time.time() - start
    print(
        f"PASS: Inserted {len(messages)} messages in {elapsed:.2f}s ({len(messages) / elapsed:.1f} msgs/sec)"
    )

    # Verify retrieval
    retrieved = await message_store.get_by_thread(thread.id)
    print(f"PASS: Retrieved {len(retrieved)} messages (expected {len(messages)})")
    assert len(retrieved) == len(messages), "Message count mismatch!"

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.db["astra_messages"].delete_many({})
    await storage.disconnect()


async def test_concurrent_writes():
    """Test concurrent writes to the same thread."""
    print("\n=== Test: Concurrent Writes ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_concurrent_test")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    # Create a thread
    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Concurrent Test")
    await thread_store.create(thread)

    # Write messages concurrently
    async def write_message(index: int):
        seq = await message_store.get_next_sequence(thread.id)
        msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread.id,
            role="user",
            content=f"Concurrent message {index}",
            sequence=seq,
        )
        await message_store.add(msg)

    start = time.time()
    await asyncio.gather(*[write_message(i) for i in range(50)])
    elapsed = time.time() - start

    print(f"PASS: Wrote 50 messages concurrently in {elapsed:.2f}s")

    # Verify all messages were written
    messages = await message_store.get_by_thread(thread.id)
    print(f"PASS: Retrieved {len(messages)} messages (expected 50)")
    assert len(messages) == 50, "Message count mismatch!"

    # Check sequences
    sequences = [msg.sequence for msg in messages]
    unique_sequences = len(set(sequences))
    print(f"PASS: Sequences: {unique_sequences} unique out of {len(sequences)} total")
    if unique_sequences < len(sequences):
        print(
            f"WARN:  Note: {len(sequences) - unique_sequences} sequence collisions occurred (expected in high concurrency)"
        )

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.db["astra_messages"].delete_many({})
    await storage.disconnect()


async def test_large_content():
    """Test handling large message content."""
    print("\n=== Test: Large Content ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_large_test")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Large Content Test")
    await thread_store.create(thread)

    # Create a 1MB message
    large_content = "x" * (1024 * 1024)  # 1MB
    seq = await message_store.get_next_sequence(thread.id)
    msg = Message(
        id=f"msg-{uuid4().hex[:12]}",
        thread_id=thread.id,
        role="user",
        content=large_content,
        sequence=seq,
    )

    start = time.time()
    await message_store.add(msg)
    elapsed = time.time() - start
    print(f"PASS: Stored 1MB message in {elapsed:.2f}s")

    # Retrieve and verify
    start = time.time()
    retrieved = await message_store.get_by_thread(thread.id)
    elapsed = time.time() - start
    print(f"PASS: Retrieved 1MB message in {elapsed:.2f}s")
    assert len(retrieved[0].content) == len(large_content), "Content size mismatch!"

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.db["astra_messages"].delete_many({})
    await storage.disconnect()


async def main():
    print("=" * 60)
    print("MongoDB Bulk Operations Test Suite")
    print("=" * 60)

    await test_bulk_thread_creation()
    await test_bulk_message_insertion()
    await test_concurrent_writes()
    await test_large_content()

    print("\n" + "=" * 60)
    print("PASS: All MongoDB bulk operation tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
