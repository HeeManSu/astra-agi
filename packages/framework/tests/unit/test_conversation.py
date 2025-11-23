import pytest
from unittest.mock import AsyncMock, MagicMock
from framework.agents.conversation import ConversationManager
from framework.storage.models import Message
from datetime import datetime

@pytest.mark.asyncio
async def test_conversation_manager_get_context():
    """Test that ConversationManager loads only recent messages."""
    manager = ConversationManager(max_messages=5)
    
    # Mock memory with 10 messages
    mock_memory = AsyncMock()
    mock_messages = [
        Message(
            id=f"msg-{i}",
            thread_id="thread-1",
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}",
            created_at=datetime.now()
        )
        for i in range(10)
    ]
    mock_memory.get_history = AsyncMock(return_value=mock_messages[:5])  # Only returns 5
    
    # Get context
    context = await manager.get_context("thread-1", mock_memory)
    
    # Verify it requested with limit
    mock_memory.get_history.assert_called_once_with("thread-1", limit=5)
    
    # Verify format
    assert len(context) == 5
    assert all("role" in msg and "content" in msg for msg in context)
    assert context[0]["content"] == "Message 0"

@pytest.mark.asyncio
async def test_conversation_manager_respects_max_messages():
    """Test that max_messages parameter works correctly."""
    manager = ConversationManager(max_messages=3)
    
    mock_memory = AsyncMock()
    mock_messages = [
        Message(
            id=f"msg-{i}",
            thread_id="thread-1",
            role="user",
            content=f"Message {i}",
            created_at=datetime.now()
        )
        for i in range(3)
    ]
    mock_memory.get_history = AsyncMock(return_value=mock_messages)
    
    context = await manager.get_context("thread-1", mock_memory)
    
    # Should request exactly 3 messages
    mock_memory.get_history.assert_called_once_with("thread-1", limit=3)
    assert len(context) == 3
