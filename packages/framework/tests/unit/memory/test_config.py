"""
Unit tests for AgentMemory configuration model.

Tests pure configuration logic without LLM calls.
"""

from framework.memory.memory import AgentMemory
import pytest


@pytest.mark.unit
class TestAgentMemory:
    """Tests for AgentMemory configuration model."""

    def test_default_values(self):
        """Test that AgentMemory has correct default values for V1."""
        memory = AgentMemory()
        assert memory.add_history_to_messages is True
        assert memory.num_history_responses == 5

    def test_add_history_disabled(self):
        """Test that add_history_to_messages can be disabled."""
        memory = AgentMemory(add_history_to_messages=False)
        assert memory.add_history_to_messages is False

    def test_custom_num_history_responses(self):
        """Test that num_history_responses can be customized."""
        memory = AgentMemory(num_history_responses=10)
        assert memory.num_history_responses == 10


# @TODO: Himanshu. Disabled for now and will be enabled later with proper testing.
# Advanced AgentMemory features are disabled for V1 release.
#
# def test_custom_configuration(self):
#     """Test creating AgentMemory with custom values."""
#     memory = AgentMemory(
#         add_history_to_messages=False,
#         token_limit=1000,
#         window_size=10,
#         summarize_overflow=False,
#         include_system_messages=False,
#         include_tool_calls=True,
#         summary_model="gpt-3.5-turbo",
#         summary_prompt="Custom summary prompt",
#     )
#     assert memory.add_history_to_messages is False
#     assert memory.token_limit == 1000
#     assert memory.window_size == 10
#     assert memory.summarize_overflow is False
#     assert memory.include_system_messages is False
#     assert memory.include_tool_calls is True
#     assert memory.summary_model == "gpt-3.5-turbo"
#     assert memory.summary_prompt == "Custom summary prompt"
#
# def test_token_limit_none(self):
#     """Test that token_limit can be None (uses window_size fallback)."""
#     memory = AgentMemory(token_limit=None, window_size=15)
#     assert memory.token_limit is None
#     assert memory.window_size == 15
#
# def test_window_size_override(self):
#     """Test that window_size can override num_history_responses."""
#     memory = AgentMemory(window_size=30, num_history_responses=5)
#     assert memory.window_size == 30
#     assert memory.num_history_responses == 5
#
# def test_summary_prompt_default(self):
#     """Test default summary prompt content."""
#     memory = AgentMemory()
#     assert len(memory.summary_prompt) > 0
#     assert (
#         "conversation" in memory.summary_prompt.lower()
#         or "summarize" in memory.summary_prompt.lower()
#     )
