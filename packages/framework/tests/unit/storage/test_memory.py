import pytest
from unittest.mock import AsyncMock, MagicMock
from framework.storage.memory import AgentMemory
from framework.storage.base import StorageBackend

@pytest.mark.asyncio
async def test_memory_add_message_queues():
    """Test that adding a message queues it for saving."""
    mock_storage = MagicMock(spec=StorageBackend)
    memory = AgentMemory(mock_storage)
    
    # Mock queue
    memory.queue = AsyncMock()
    
    # Mock get_thread to return True (thread exists)
    memory.threads.get = AsyncMock(return_value=True)
    
    await memory.add_message("thread-1", "user", "hello")
    
    # Verify enqueue called
    memory.queue.enqueue.assert_called_once()
    args = memory.queue.enqueue.call_args[0]
    assert args[0] == memory.messages.add_many # Function
    assert args[1].content == "hello" # Item

@pytest.mark.asyncio
async def test_memory_lifecycle():
    """Test start/stop calls queue start/stop."""
    mock_storage = MagicMock(spec=StorageBackend)
    memory = AgentMemory(mock_storage)
    memory.queue = AsyncMock()
    
    await memory.start()
    memory.queue.start.assert_called_once()
    
    await memory.stop()
    memory.queue.stop.assert_called_once()
