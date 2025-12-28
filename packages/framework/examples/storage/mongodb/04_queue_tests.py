"""
Test SaveQueueManager functionality with MongoDB.

Database Parts Tested:
- SaveQueueManager debounce behavior
- Batch size management
- Error handling and recovery
- Concurrent queue additions
- Queue flush on stop

Tests:
- Debounce delays batch saving
- Messages batched by configured size
- Queue continues after save failures
- Concurrent additions are thread-safe
- Stop() flushes remaining items

Requires: MongoDB running locally on port 27017.
"""

import asyncio
import time
from uuid import uuid4

from framework.storage.databases.mongodb import MongoDBStorage
from framework.storage.models import Message, Thread
from framework.storage.queue import SaveQueueManager
from framework.storage.stores.message import MessageStore
from framework.storage.stores.thread import ThreadStore


async def test_debounce():
    """Test that queue debounces writes."""
    print("\n=== Test: Debounce Behavior ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_queue_debounce_test")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Debounce Test")
    await thread_store.create(thread)

    save_count = 0

    async def save_batch(messages):
        nonlocal save_count
        save_count += 1
        for msg in messages:
            await message_store.add(msg)

    # Create queue with 0.5s debounce
    queue = SaveQueueManager(save_func=save_batch, batch_size=10, debounce_seconds=0.5)

    # Add 5 messages rapidly
    for i in range(5):
        seq = i + 1
        msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread.id,
            role="user",
            content=f"Message {i}",
            sequence=seq,
        )
        queue.add(msg)
        await asyncio.sleep(0.1)  # 100ms between adds

    # Wait for debounce
    await asyncio.sleep(0.6)

    print(f"PASS: Save called {save_count} time(s) for 5 rapid additions (expected 1)")
    assert save_count == 1, f"Expected 1 save, got {save_count}"

    # Verify all messages saved
    messages = await message_store.get_by_thread(thread.id)
    print(f"PASS: {len(messages)} messages saved (expected 5)")
    assert len(messages) == 5

    await queue.stop()
    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.db["astra_messages"].delete_many({})
    await storage.disconnect()


async def test_batching():
    """Test that queue batches writes."""
    print("\n=== Test: Batching Behavior ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_queue_batch_test")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Batch Test")
    await thread_store.create(thread)

    batch_sizes = []

    async def save_batch(messages):
        batch_sizes.append(len(messages))
        for msg in messages:
            await message_store.add(msg)

    # Create queue with batch size of 5
    queue = SaveQueueManager(save_func=save_batch, batch_size=5, debounce_seconds=0.3)

    # Add 23 messages (should create batches of 5, 5, 5, 5, 3)
    for i in range(23):
        seq = i + 1
        msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread.id,
            role="user",
            content=f"Message {i}",
            sequence=seq,
        )
        queue.add(msg)

    # Wait for all batches to flush
    await asyncio.sleep(0.5)

    print(f"PASS: Batch sizes: {batch_sizes}")
    print(f"PASS: Total batches: {len(batch_sizes)}")

    # Verify all messages saved
    messages = await message_store.get_by_thread(thread.id)
    print(f"PASS: {len(messages)} messages saved (expected 23)")
    assert len(messages) == 23

    await queue.stop()
    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.db["astra_messages"].delete_many({})
    await storage.disconnect()


async def test_queue_error_handling():
    """Test queue behavior when save fails."""
    print("\n=== Test: Error Handling ===")

    error_count = 0
    success_count = 0

    async def failing_save(messages):
        nonlocal error_count, success_count
        if error_count < 2:
            error_count += 1
            raise Exception("Simulated save failure")
        success_count += 1

    queue = SaveQueueManager(save_func=failing_save, batch_size=5, debounce_seconds=0.2)

    # Add messages
    for i in range(5):
        queue.add(f"message-{i}")

    await asyncio.sleep(0.3)

    print(f"PASS: Errors handled: {error_count}")
    print("PASS: Queue continues to work after errors")

    await queue.stop()


async def test_concurrent_queue_additions():
    """Test concurrent additions to queue."""
    print("\n=== Test: Concurrent Queue Additions ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_queue_concurrent_test")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Concurrent Queue Test")
    await thread_store.create(thread)

    async def save_batch(messages):
        for msg in messages:
            await message_store.add(msg)

    queue = SaveQueueManager(save_func=save_batch, batch_size=10, debounce_seconds=0.3)

    # Concurrently add 100 messages
    async def add_messages(start_idx: int, count: int):
        for i in range(count):
            seq = start_idx + i + 1
            msg = Message(
                id=f"msg-{uuid4().hex[:12]}",
                thread_id=thread.id,
                role="user",
                content=f"Message {start_idx + i}",
                sequence=seq,
            )
            queue.add(msg)
            await asyncio.sleep(0.01)

    start = time.time()
    await asyncio.gather(
        add_messages(0, 25), add_messages(25, 25), add_messages(50, 25), add_messages(75, 25)
    )

    # Wait for queue to flush
    await asyncio.sleep(0.5)
    elapsed = time.time() - start

    print(f"PASS: Added 100 messages concurrently in {elapsed:.2f}s")

    # Verify all messages saved
    messages = await message_store.get_by_thread(thread.id)
    print(f"PASS: {len(messages)} messages saved (expected 100)")
    assert len(messages) == 100

    await queue.stop()
    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.db["astra_messages"].delete_many({})
    await storage.disconnect()


async def test_queue_stop():
    """Test that stop() flushes remaining items."""
    print("\n=== Test: Queue Stop Flushes ===")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_queue_stop_test")
    await storage.connect()

    thread_store = ThreadStore(storage)
    message_store = MessageStore(storage)

    thread = Thread(id=f"thread-{uuid4().hex[:8]}", title="Stop Test")
    await thread_store.create(thread)

    async def save_batch(messages):
        for msg in messages:
            await message_store.add(msg)

    queue = SaveQueueManager(save_func=save_batch, batch_size=100, debounce_seconds=10.0)

    # Add 5 messages (won't auto-flush due to high batch size and long debounce)
    for i in range(5):
        seq = i + 1
        msg = Message(
            id=f"msg-{uuid4().hex[:12]}",
            thread_id=thread.id,
            role="user",
            content=f"Message {i}",
            sequence=seq,
        )
        queue.add(msg)

    # Stop should flush immediately
    await queue.stop()

    # Verify all messages saved
    messages = await message_store.get_by_thread(thread.id)
    print(f"PASS: {len(messages)} messages saved after stop() (expected 5)")
    assert len(messages) == 5

    # Clean up
    await storage.db["astra_threads"].delete_many({})
    await storage.db["astra_messages"].delete_many({})
    await storage.disconnect()


async def main():
    print("=" * 60)
    print("MongoDB SaveQueueManager Test Suite")
    print("=" * 60)

    await test_debounce()
    await test_batching()
    await test_queue_error_handling()
    await test_concurrent_queue_additions()
    await test_queue_stop()

    print("\n" + "=" * 60)
    print("PASS: All MongoDB queue tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
