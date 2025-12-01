"""
Example 1: AgentMemory Configuration

This example demonstrates how to configure AgentMemory for your agents.

What it demonstrates:
1. Default memory configuration: Understanding default values
2. Custom memory configuration: Setting custom values for memory behavior
3. Configuration options: Available fields and their purposes

Codebase components:
- framework.memory.memory.AgentMemory: Pydantic model for memory configuration
- Configuration fields:
  * add_history_to_messages: Whether to load conversation history
  * num_history_responses: Number of recent responses to keep in context
  * create_session_summary: Whether to enable summarization
  * summary_prompt: Custom prompt for generating summaries

Usage:
- Use default config: AgentMemory() - Good for most cases
- Custom config: AgentMemory(num_history_responses=5, ...) - Fine-tune behavior
- Share config: Create once, use across multiple agents
"""

from framework.memory import AgentMemory


def test_memory_defaults():
    """
    Test default memory configuration.

    Demonstrates that AgentMemory has sensible defaults:
    - History loading is enabled by default
    - Keeps 10 recent responses in context
    - Summarization is disabled by default

    This is useful when you want standard behavior without configuration.
    """
    # Create memory with default settings
    # Tests: framework.memory.memory.AgentMemory default values
    memory = AgentMemory()

    # Verify default values
    assert memory.add_history_to_messages is True, "History loading should be enabled by default"
    assert memory.num_history_responses == 10, "Should keep 10 recent responses by default"
    assert memory.create_session_summary is False, "Summarization should be disabled by default"

    print("✓ Default configuration verified!")
    print("  - History loading: Enabled")
    print("  - Context window: 10 responses")
    print("  - Summarization: Disabled")


def test_custom_config():
    """
    Test custom memory configuration.

    Demonstrates how to customize memory behavior:
    - Reduce context window size (num_history_responses)
    - Enable summarization (create_session_summary)
    - Set custom summary prompt (summary_prompt)

    This is useful when you need:
    - Smaller context windows (reduce token usage)
    - Summarization for long conversations
    - Custom summary formatting
    """
    # Create memory with custom settings
    # Tests: framework.memory.memory.AgentMemory custom configuration
    memory = AgentMemory(
        num_history_responses=5,  # Keep only 5 recent responses (instead of default 10)
        create_session_summary=True,  # Enable summarization
        summary_prompt="Custom prompt",  # Custom summary generation prompt
    )

    # Verify custom values are set correctly
    assert memory.num_history_responses == 5, "Should keep 5 recent responses"
    assert memory.create_session_summary is True, "Summarization should be enabled"
    assert memory.summary_prompt == "Custom prompt", "Custom prompt should be set"

    print("✓ Custom configuration verified!")
    print("  - Context window: 5 responses (custom)")
    print("  - Summarization: Enabled")
    print("  - Summary prompt: Custom")


if __name__ == "__main__":
    test_memory_defaults()
    test_custom_config()
