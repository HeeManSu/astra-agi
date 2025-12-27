"""
Example 1: AgentMemory Configuration

This example demonstrates how to configure AgentMemory for your agents with the new STM features.

What it demonstrates:
1. Default memory configuration: Understanding default values
2. Message count windowing: Using window_size for simple message limits
3. Token-aware windowing: Using token_limit for precise token control
4. Overflow handling: Automatic summarization when limits are exceeded
5. System message filtering: Control whether system messages count toward limits

Codebase components:
- framework.memory.memory.AgentMemory: Pydantic model for memory configuration
- New STM fields:
  * token_limit: Token-based windowing (primary)
  * window_size: Message count limit (fallback)
  * summarize_overflow: Enable automatic summarization
  * include_system_messages: Count system messages in limits
  * summary_model: Optional lighter model for summarization

Usage:
- Simple: AgentMemory(window_size=20) - Message count limit
- Advanced: AgentMemory(token_limit=4000) - Token-aware with overflow handling
- Custom: AgentMemory(token_limit=4000, summarize_overflow=True, ...)
"""

from framework.memory import AgentMemory


def test_memory_defaults():
    """
    Test default memory configuration.

    Demonstrates that AgentMemory has sensible defaults:
    - History loading is enabled by default
    - window_size defaults to 20 messages
    - Token-aware windowing is disabled (token_limit=None)
    - Overflow summarization is enabled by default
    """
    memory = AgentMemory()

    # Verify default values
    assert memory.add_history_to_messages is True
    assert memory.window_size == 20
    assert memory.token_limit is None
    assert memory.summarize_overflow is True
    assert memory.include_system_messages is True

    print("✓ Default configuration verified!")
    print("  - History loading: Enabled")
    print("  - Window size: 20 messages")
    print("  - Token limit: None (using message count)")
    print("  - Overflow summarization: Enabled")


def test_message_count_windowing():
    """
    Test message count-based windowing.

    Simple approach: limit by number of messages.
    Useful when you want predictable behavior without token counting.
    """
    memory = AgentMemory(
        window_size=10,  # Keep only last 10 messages
        token_limit=None,  # Disable token-aware windowing
    )

    assert memory.window_size == 10
    assert memory.token_limit is None

    print("✓ Message count windowing configured!")
    print("  - Window size: 10 messages")
    print("  - Token limit: Disabled")


def test_token_aware_windowing():
    """
    Test token-aware windowing.

    Advanced approach: limit by token count for precise control.
    Automatically trims messages to fit within token budget.
    """
    memory = AgentMemory(
        token_limit=4000,  # Primary: token-based limit
        window_size=20,  # Fallback: if token_limit not set
        summarize_overflow=True,  # Summarize when exceeding limit
    )

    assert memory.token_limit == 4000
    assert memory.summarize_overflow is True

    print("✓ Token-aware windowing configured!")
    print("  - Token limit: 4000 tokens")
    print("  - Overflow handling: Summarization enabled")


def test_system_message_filtering():
    """
    Test system message filtering.

    Control whether system messages count toward the window limit.
    """
    # Include system messages in count
    memory_with_system = AgentMemory(
        window_size=20,
        include_system_messages=True,  # System messages count toward limit
    )

    # Exclude system messages from count
    memory_without_system = AgentMemory(
        window_size=20,
        include_system_messages=False,  # System messages don't count
    )

    assert memory_with_system.include_system_messages is True
    assert memory_without_system.include_system_messages is False

    print("✓ System message filtering configured!")
    print("  - With system: System messages count toward limit")
    print("  - Without system: System messages excluded from limit")


def test_complete_config():
    """
    Test complete STM configuration.

    Shows all new features working together.
    """
    memory = AgentMemory(
        # Basic
        add_history_to_messages=True,
        # Windowing
        token_limit=4000,  # Token-aware (primary)
        window_size=20,  # Fallback message count
        # Overflow handling
        summarize_overflow=True,
        summary_model="gpt-3.5-turbo",  # Lighter model for summarization
        # System messages
        include_system_messages=True,
        # Summary prompt
        summary_prompt="Summarize key decisions and facts from this conversation.",
    )

    assert memory.token_limit == 4000
    assert memory.summarize_overflow is True
    assert memory.summary_model == "gpt-3.5-turbo"

    print("✓ Complete STM configuration!")
    print("  - Token-aware windowing: 4000 tokens")
    print("  - Overflow handling: Enabled with custom model")
    print("  - System messages: Included in count")


if __name__ == "__main__":
    test_memory_defaults()
    test_message_count_windowing()
    test_token_aware_windowing()
    test_system_message_filtering()
    test_complete_config()
