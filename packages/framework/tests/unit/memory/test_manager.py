"""
Unit tests for MemoryManager (pure logic without LLM calls).

Tests message limiting, filtering, and windowing logic.
"""

from unittest.mock import AsyncMock, MagicMock

from framework.memory.manager import MemoryManager
from framework.memory.memory import AgentMemory
import pytest


@pytest.mark.unit
class TestMemoryManagerMessageLimiting:
    """Tests for message count limiting."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock model."""
        return MagicMock()

    @pytest.fixture
    def memory_config(self):
        """Create default memory config."""
        return AgentMemory(window_size=5, include_system_messages=True)

    @pytest.fixture
    def manager(self, memory_config, mock_model):
        """Create MemoryManager instance."""
        return MemoryManager(memory_config, mock_model)

    def test_apply_message_limiting_within_limit(self, manager):
        """Test message limiting when messages are within limit."""
        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
        ]
        result = manager._apply_message_limiting(messages, limit=5)
        assert len(result) == 3
        assert result == messages

    def test_apply_message_limiting_exceeds_limit(self, manager):
        """Test message limiting when messages exceed limit."""
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(10)]
        result = manager._apply_message_limiting(messages, limit=5)
        assert len(result) == 5
        # Should keep newest messages
        assert result == messages[-5:]

    def test_apply_message_limiting_excludes_system_messages(self, manager):
        """Test message limiting excludes system messages from count."""
        manager.memory.include_system_messages = False
        messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Message 3"},
        ]
        result = manager._apply_message_limiting(messages, limit=2)
        # Should keep all system messages + 2 non-system messages
        assert len(result) == 3  # 1 system + 2 non-system
        assert result[0]["role"] == "system"
        assert result[-1]["content"] == "Message 3"

    def test_apply_message_limiting_includes_system_messages(self, manager):
        """Test message limiting includes system messages in count."""
        manager.memory.include_system_messages = True
        messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
        ]
        result = manager._apply_message_limiting(messages, limit=3)
        # Should count all messages including system
        assert len(result) == 3
        assert result == messages[-3:]

    def test_apply_message_limiting_empty_list(self, manager):
        """Test message limiting with empty list."""
        result = manager._apply_message_limiting([], limit=5)
        assert result == []

    def test_apply_message_limiting_exact_limit(self, manager):
        """Test message limiting with exact limit."""
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(5)]
        result = manager._apply_message_limiting(messages, limit=5)
        assert len(result) == 5
        assert result == messages


@pytest.mark.unit
class TestMemoryManagerFiltering:
    """Tests for message filtering logic."""

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
    async def test_get_context_excludes_tool_calls(self, mock_model, mock_storage):
        """Test that tool calls are excluded when include_tool_calls is False."""
        memory_config = AgentMemory(include_tool_calls=False, window_size=10)
        manager = MemoryManager(memory_config, mock_model)

        # Mock storage to return messages including tool calls
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "tool", "content": "Tool result"},
            {"role": "user", "content": "Thanks"},
        ]
        mock_storage.get_history = AsyncMock(return_value=messages)

        context = await manager.get_context("thread_1", mock_storage)

        # Tool messages should be filtered out
        tool_messages = [msg for msg in context if msg.get("role") == "tool"]
        assert len(tool_messages) == 0

    @pytest.mark.asyncio
    async def test_get_context_includes_tool_calls(self, mock_model, mock_storage):
        """Test that tool calls are included when include_tool_calls is True."""
        memory_config = AgentMemory(include_tool_calls=True, window_size=10)
        manager = MemoryManager(memory_config, mock_model)

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "tool", "content": "Tool result"},
        ]
        mock_storage.get_history = AsyncMock(return_value=messages)

        context = await manager.get_context("thread_1", mock_storage)

        # Tool messages should be included
        tool_messages = [msg for msg in context if msg.get("role") == "tool"]
        assert len(tool_messages) == 1

    @pytest.mark.asyncio
    async def test_get_context_disabled_history(self, mock_model, mock_storage):
        """Test that get_context returns empty when add_history_to_messages is False."""
        memory_config = AgentMemory(add_history_to_messages=False)
        manager = MemoryManager(memory_config, mock_model)

        context = await manager.get_context("thread_1", mock_storage)
        assert context == []


@pytest.mark.unit
class TestMemoryManagerWindowSize:
    """Tests for window size calculation."""

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
    async def test_window_size_from_config(self, mock_model, mock_storage):
        """Test that window_size from config is used."""
        memory_config = AgentMemory(window_size=15)
        manager = MemoryManager(memory_config, mock_model)

        mock_storage.get_history = AsyncMock(return_value=[])

        await manager.get_context("thread_1", mock_storage)

        # Should request 2x limit for token-aware trimming buffer
        mock_storage.get_history.assert_called_once()
        call_args = mock_storage.get_history.call_args
        assert call_args[1]["limit"] == 30  # 15 * 2

    @pytest.mark.asyncio
    async def test_window_size_fallback_to_num_history_responses(self, mock_model, mock_storage):
        """Test fallback to num_history_responses when window_size is default."""
        memory_config = AgentMemory(window_size=20, num_history_responses=8)
        manager = MemoryManager(memory_config, mock_model)

        mock_storage.get_history = AsyncMock(return_value=[])

        await manager.get_context("thread_1", mock_storage)

        # Should use window_size (20), not num_history_responses
        call_args = mock_storage.get_history.call_args
        assert call_args[1]["limit"] == 40  # 20 * 2

    @pytest.mark.asyncio
    async def test_window_size_custom_num_history_responses(self, mock_model, mock_storage):
        """Test custom num_history_responses calculation."""
        memory_config = AgentMemory(window_size=20, num_history_responses=12)
        manager = MemoryManager(memory_config, mock_model)

        # When window_size is default (20) and num_history_responses is custom,
        # it should use num_history_responses * 2
        memory_config.window_size = 20
        memory_config.num_history_responses = 12

        mock_storage.get_history = AsyncMock(return_value=[])

        await manager.get_context("thread_1", mock_storage)

        # Should use num_history_responses * 2 calculation
        call_args = mock_storage.get_history.call_args
        # Since window_size is 20 (default) and num_history_responses is 12,
        # it should use 12 * 2 = 24
        assert call_args[1]["limit"] == 24  # 12 * 2
