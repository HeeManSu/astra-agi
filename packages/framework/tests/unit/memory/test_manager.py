"""
Unit tests for MemoryManager (pure logic without LLM calls).

Tests message limiting, filtering, and windowing logic.
"""

from unittest.mock import AsyncMock, MagicMock

from framework.memory.manager import MemoryManager
from framework.memory.memory import AgentMemory
import pytest


@pytest.mark.unit
class TestMemoryManagerBasicV1:
    """Tests for basic V1 MemoryManager functionality."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock model."""
        return MagicMock()

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage."""
        storage = AsyncMock()
        storage._message_to_dict = lambda msg: {
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
        }
        return storage

    @pytest.mark.asyncio
    async def test_get_context_disabled_history(self, mock_model, mock_storage):
        """Test that get_context returns empty when add_history_to_messages is False."""
        memory_config = AgentMemory(add_history_to_messages=False)
        manager = MemoryManager(memory_config, mock_model)

        context = await manager.get_context("thread_1", mock_storage)
        assert context == []

    @pytest.mark.asyncio
    async def test_get_context_uses_num_history_responses(self, mock_model, mock_storage):
        """Test that get_context uses num_history_responses * 2 for message limit."""
        memory_config = AgentMemory(num_history_responses=5)
        manager = MemoryManager(memory_config, mock_model)

        mock_storage.get_history = AsyncMock(return_value=[])

        await manager.get_context("thread_1", mock_storage)

        # Should request num_history_responses * 2 = 10 messages
        mock_storage.get_history.assert_called_once()
        call_args = mock_storage.get_history.call_args
        assert call_args[1]["limit"] == 10  # 5 * 2

    @pytest.mark.asyncio
    async def test_get_context_loads_messages(self, mock_model, mock_storage):
        """Test that get_context loads messages from storage."""
        memory_config = AgentMemory(num_history_responses=5)
        manager = MemoryManager(memory_config, mock_model)

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"},
        ]
        mock_storage.get_history = AsyncMock(return_value=messages)

        context = await manager.get_context("thread_1", mock_storage)

        assert len(context) == 3
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"


# @TODO: Himanshu. Disabled for now and will be enabled later with proper testing.
# Advanced AgentMemory features (window_size, include_tool_calls, etc.) are disabled for V1.
#
# class TestMemoryManagerMessageLimiting:
#     """Tests for message count limiting."""
#     ...
#
# class TestMemoryManagerFiltering:
#     """Tests for message filtering logic."""
#     ...
#
# class TestMemoryManagerWindowSize:
#     """Tests for window size calculation."""
#     ...
