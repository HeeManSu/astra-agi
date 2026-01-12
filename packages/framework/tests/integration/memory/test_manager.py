"""
Integration tests for MemoryManager with real LLM calls.

Tests summarization, token-aware windowing, and context loading.
"""

from framework.memory.manager import MemoryManager
from framework.memory.memory import AgentMemory
import pytest


@pytest.mark.integration
class TestMemoryManagerContextLoadingV1:
    """Tests for basic context loading with real storage (V1)."""

    @pytest.mark.asyncio
    async def test_get_context_loads_messages(self, hf_model, agent_storage):
        """Test that get_context loads messages from storage."""
        thread_id = "test_thread_1"

        # Add messages to storage
        await agent_storage.add_message(thread_id, "user", "Hello, how are you?")
        await agent_storage.add_message(thread_id, "assistant", "I'm doing well, thank you!")
        await agent_storage.add_message(thread_id, "user", "What is Python?")

        # Wait for queue to flush
        await agent_storage.queue.flush()

        memory_config = AgentMemory(num_history_responses=10)
        manager = MemoryManager(memory_config, hf_model)

        context = await manager.get_context(thread_id, agent_storage)

        assert len(context) == 3
        assert context[0]["role"] == "user"
        assert "Hello" in context[0]["content"] or "hello" in context[0]["content"].lower()
        assert context[1]["role"] == "assistant"
        assert context[2]["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_context_disabled(self, hf_model, agent_storage):
        """Test that get_context returns empty when add_history_to_messages is False."""
        thread_id = "test_thread_disabled"

        await agent_storage.add_message(thread_id, "user", "Hello")
        await agent_storage.queue.flush()

        memory_config = AgentMemory(add_history_to_messages=False)
        manager = MemoryManager(memory_config, hf_model)

        context = await manager.get_context(thread_id, agent_storage)

        assert context == []


# @TODO: Himanshu. Disabled for now and will be enabled later with proper testing.
# Advanced AgentMemory features (window_size, include_tool_calls, token_limit, summarization)
# are disabled for V1 release. The following test classes have been commented out:
#
# class TestMemoryManagerContextLoading:
#     """Tests for window_size and tool call filtering."""
#     ...
#
# class TestMemoryManagerSummarization:
#     """Tests for summarization with real LLM."""
#     ...
#
# class TestMemoryManagerTokenAwareWindowing:
#     """Tests for token-aware windowing with real LLM."""
#     ...
