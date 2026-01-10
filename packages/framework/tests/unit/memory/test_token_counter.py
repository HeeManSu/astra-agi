"""
Unit tests for TokenCounter.

Tests token counting logic without LLM calls.
"""

from framework.memory.token_counter import TokenCounter
import pytest


@pytest.mark.unit
class TestTokenCounter:
    """Tests for TokenCounter."""

    def test_initialization(self):
        """Test TokenCounter initialization."""
        counter = TokenCounter()
        assert counter.encoding == "cl100k_base"
        assert counter._cache == {}

    def test_initialization_custom_encoding(self):
        """Test TokenCounter with custom encoding."""
        counter = TokenCounter(encoding="p50k_base")
        assert counter.encoding == "p50k_base"

    def test_count_simple_text(self):
        """Test counting tokens in simple text."""
        counter = TokenCounter()
        tokens = counter.count("Hello world")
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_count_empty_string(self):
        """Test counting tokens in empty string."""
        counter = TokenCounter()
        tokens = counter.count("")
        assert tokens == 0

    def test_count_caching(self):
        """Test that token counting is cached."""
        counter = TokenCounter()
        text = "This is a test message for caching"
        tokens1 = counter.count(text)
        tokens2 = counter.count(text)
        assert tokens1 == tokens2
        assert text in counter._cache

    def test_count_message_simple(self):
        """Test counting tokens in a simple message."""
        counter = TokenCounter()
        message = {"role": "user", "content": "Hello"}
        tokens = counter.count_message(message)
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_count_message_with_overhead(self):
        """Test that message counting includes overhead."""
        counter = TokenCounter()
        message = {"role": "user", "content": "Hello"}
        tokens = counter.count_message(message)
        # Should include TOKENS_PER_MESSAGE overhead
        assert tokens >= int(counter.TOKENS_PER_MESSAGE)

    def test_count_message_different_roles(self):
        """Test counting tokens for different message roles."""
        counter = TokenCounter()
        user_msg = {"role": "user", "content": "Hello"}
        assistant_msg = {"role": "assistant", "content": "Hello"}
        system_msg = {"role": "system", "content": "Hello"}

        user_tokens = counter.count_message(user_msg)
        assistant_tokens = counter.count_message(assistant_msg)
        system_tokens = counter.count_message(system_msg)

        # All should have tokens
        assert user_tokens > 0
        assert assistant_tokens > 0
        assert system_tokens > 0

    def test_count_messages_empty_list(self):
        """Test counting tokens in empty message list."""
        counter = TokenCounter()
        tokens = counter.count_messages([])
        assert tokens == 0

    def test_count_messages_single(self):
        """Test counting tokens in single message."""
        counter = TokenCounter()
        messages = [{"role": "user", "content": "Hello"}]
        tokens = counter.count_messages(messages)
        assert tokens > 0
        # Should include conversation overhead
        assert tokens >= int(counter.TOKENS_PER_CONVERSATION)

    def test_count_messages_multiple(self):
        """Test counting tokens in multiple messages."""
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
        ]
        tokens = counter.count_messages(messages)
        assert tokens > 0
        # Should be more than single message
        single_tokens = counter.count_message(messages[0])
        assert tokens > single_tokens

    def test_count_input_messages_with_overhead(self):
        """Test count_input_messages with conversation overhead."""
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        tokens_with = counter.count_input_messages(messages, include_conversation_overhead=True)
        tokens_without = counter.count_input_messages(messages, include_conversation_overhead=False)
        assert tokens_with > tokens_without
        assert tokens_with - tokens_without == int(counter.TOKENS_PER_CONVERSATION)

    def test_count_input_messages_without_overhead(self):
        """Test count_input_messages without conversation overhead."""
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        tokens = counter.count_input_messages(messages, include_conversation_overhead=False)
        # Should be sum of message tokens without conversation overhead
        expected = sum(counter.count_message(msg) for msg in messages)
        assert tokens == expected

    def test_count_message_missing_fields(self):
        """Test counting tokens in message with missing fields."""
        counter = TokenCounter()
        # Missing role
        msg1 = {"content": "Hello"}
        tokens1 = counter.count_message(msg1)
        assert tokens1 > 0

        # Missing content
        msg2 = {"role": "user"}
        tokens2 = counter.count_message(msg2)
        assert tokens2 >= int(counter.TOKENS_PER_MESSAGE)

    def test_count_long_text(self):
        """Test counting tokens in long text."""
        counter = TokenCounter()
        long_text = "Hello " * 1000
        tokens = counter.count(long_text)
        assert tokens > 100  # Should have significant token count
