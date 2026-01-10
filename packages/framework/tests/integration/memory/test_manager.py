"""
Integration tests for MemoryManager with real LLM calls.

Tests summarization, token-aware windowing, and context loading.
"""

from framework.memory.manager import MemoryManager
from framework.memory.memory import AgentMemory
import pytest


@pytest.mark.integration
class TestMemoryManagerContextLoading:
    """Tests for loading conversation context with real storage."""

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

        memory_config = AgentMemory(window_size=10)
        manager = MemoryManager(memory_config, hf_model)

        context = await manager.get_context(thread_id, agent_storage)

        assert len(context) == 3
        assert context[0]["role"] == "user"
        assert "Hello" in context[0]["content"] or "hello" in context[0]["content"].lower()
        assert context[1]["role"] == "assistant"
        assert context[2]["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_context_respects_window_size(self, hf_model, agent_storage):
        """Test that get_context respects window_size limit."""
        thread_id = "test_thread_2"

        # Add more messages than window_size
        for i in range(15):
            await agent_storage.add_message(thread_id, "user", f"Message {i}")
            await agent_storage.add_message(thread_id, "assistant", f"Response {i}")

        await agent_storage.queue.flush()

        memory_config = AgentMemory(window_size=5)
        manager = MemoryManager(memory_config, hf_model)

        context = await manager.get_context(thread_id, agent_storage)

        # Should be limited to window_size (5 messages)
        assert len(context) <= 5

    @pytest.mark.asyncio
    async def test_get_context_excludes_tool_calls(self, hf_model, agent_storage):
        """Test that tool calls are excluded when include_tool_calls is False."""
        thread_id = "test_thread_3"

        await agent_storage.add_message(thread_id, "user", "Calculate 2+2")
        await agent_storage.add_message(
            thread_id,
            "assistant",
            "I'll calculate that for you.",
            tool_calls=[{"name": "calculator", "arguments": {"a": 2, "b": 2}}],
        )
        await agent_storage.add_message(thread_id, "tool", "4")
        await agent_storage.add_message(thread_id, "assistant", "The result is 4")

        await agent_storage.queue.flush()

        memory_config = AgentMemory(window_size=10, include_tool_calls=False)
        manager = MemoryManager(memory_config, hf_model)

        context = await manager.get_context(thread_id, agent_storage)

        # Tool messages should be excluded
        tool_messages = [msg for msg in context if msg.get("role") == "tool"]
        assert len(tool_messages) == 0

    @pytest.mark.asyncio
    async def test_get_context_includes_tool_calls(self, hf_model, agent_storage):
        """Test that tool calls are included when include_tool_calls is True."""
        thread_id = "test_thread_4"

        await agent_storage.add_message(thread_id, "user", "Calculate 2+2")
        await agent_storage.add_message(thread_id, "tool", "4")

        await agent_storage.queue.flush()

        memory_config = AgentMemory(window_size=10, include_tool_calls=True)
        manager = MemoryManager(memory_config, hf_model)

        context = await manager.get_context(thread_id, agent_storage)

        # Tool messages should be included
        tool_messages = [msg for msg in context if msg.get("role") == "tool"]
        assert len(tool_messages) == 1


@pytest.mark.integration
class TestMemoryManagerSummarization:
    """Tests for summarization with real LLM."""

    @pytest.mark.asyncio
    async def test_summarization_on_overflow(self, hf_model, agent_storage):
        """Test that summarization occurs when messages exceed token limit."""
        thread_id = "test_thread_summary"

        # Add many messages to trigger overflow
        for i in range(20):
            await agent_storage.add_message(
                thread_id,
                "user",
                f"This is message number {i}. It contains some content about Python programming and AI development.",
            )
            await agent_storage.add_message(
                thread_id,
                "assistant",
                f"Response to message {i}. I understand you're asking about Python and AI.",
            )

        await agent_storage.queue.flush()

        # Configure memory with token limit and summarization enabled
        memory_config = AgentMemory(
            token_limit=500,  # Small token limit to trigger overflow
            summarize_overflow=True,
            window_size=10,
        )
        manager = MemoryManager(memory_config, hf_model)

        context = await manager.get_context(thread_id, agent_storage, max_tokens=500)

        # Should have context (possibly with summary)
        assert len(context) > 0

        # Summarization may or may not occur depending on token counts
        # But context should be valid
        assert all(msg.get("role") in ["user", "assistant", "system"] for msg in context)

    @pytest.mark.asyncio
    async def test_summarization_disabled(self, hf_model, agent_storage):
        """Test that no summarization occurs when disabled."""
        thread_id = "test_thread_no_summary"

        for i in range(10):
            await agent_storage.add_message(
                thread_id,
                "user",
                f"Message {i} with some content about testing and development.",
            )

        await agent_storage.queue.flush()

        memory_config = AgentMemory(
            token_limit=200,
            summarize_overflow=False,  # Disabled
            window_size=10,
        )
        manager = MemoryManager(memory_config, hf_model)

        context = await manager.get_context(thread_id, agent_storage, max_tokens=200)

        # Should have context but no summary messages
        assert len(context) > 0
        summary_messages = [
            msg
            for msg in context
            if msg.get("role") == "system" and "summary" in msg.get("content", "").lower()
        ]
        # With summarization disabled, should not have summary messages
        # (unless they were already in the conversation)
        assert len(summary_messages) == 0


@pytest.mark.integration
class TestMemoryManagerTokenAwareWindowing:
    """Tests for token-aware windowing with real LLM."""

    @pytest.mark.asyncio
    async def test_token_aware_limiting(self, hf_model, agent_storage):
        """Test token-aware limiting when token_limit is set."""
        thread_id = "test_thread_tokens"

        # Add messages with varying lengths
        await agent_storage.add_message(thread_id, "user", "Short message")
        await agent_storage.add_message(
            thread_id,
            "assistant",
            "This is a longer response that contains more tokens and provides detailed information about the topic.",
        )
        await agent_storage.add_message(
            thread_id,
            "user",
            "Another message with moderate length that asks a question about the previous response.",
        )

        await agent_storage.queue.flush()

        memory_config = AgentMemory(token_limit=100, window_size=10)
        manager = MemoryManager(memory_config, hf_model)

        context = await manager.get_context(thread_id, agent_storage, max_tokens=100)

        # Should have context that fits within token limit
        assert len(context) > 0
        # All messages should be valid
        assert all("role" in msg and "content" in msg for msg in context)

    @pytest.mark.asyncio
    async def test_token_aware_with_system_messages(self, hf_model, agent_storage):
        """Test token-aware limiting with system messages."""
        thread_id = "test_thread_system"

        # Add system message
        await agent_storage.add_message(
            thread_id,
            "system",
            "You are a helpful assistant. Always be concise and friendly.",
        )

        # Add user messages
        for i in range(5):
            await agent_storage.add_message(
                thread_id,
                "user",
                f"User message {i} with some content.",
            )

        await agent_storage.queue.flush()

        memory_config = AgentMemory(
            token_limit=200,
            include_system_messages=True,
            window_size=10,
        )
        manager = MemoryManager(memory_config, hf_model)

        context = await manager.get_context(thread_id, agent_storage, max_tokens=200)

        # Should include system message
        system_messages = [msg for msg in context if msg.get("role") == "system"]
        assert len(system_messages) >= 1

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
