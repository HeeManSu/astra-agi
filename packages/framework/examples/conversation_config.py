import asyncio
import os
from framework.agents import Agent
from framework.models import Gemini
from framework.storage import SQLiteStorage

async def main():
    """
    Example demonstrating short-term memory configuration.
    
    Shows how to configure context window size and enable summary mode.
    """
    print("=== Short-Term Memory Configuration Example ===\n")
    
    # Setup storage
    storage = SQLiteStorage("conversation_config_demo.db")
    await storage.connect()
    
    # Example 1: Default configuration (10 messages, no summary)
    print("=" * 60)
    print("Example 1: Default Configuration")
    print("=" * 60)
    agent1 = Agent(
        name="DefaultBot",
        model=Gemini("1.5-flash"),
        storage=storage
        # context_window_size=10 (default)
        # enable_summary=False (default)
    )
    print(f"Context window size: {agent1.context_window_size}")
    print(f"Summary enabled: {agent1.enable_summary}\n")
    
    # Example 2: Larger context window (20 messages)
    print("=" * 60)
    print("Example 2: Larger Context Window")
    print("=" * 60)
    agent2 = Agent(
        name="LargeContextBot",
        model=Gemini("1.5-flash"),
        storage=storage,
        context_window_size=20  # Keep last 20 messages
    )
    print(f"Context window size: {agent2.context_window_size}")
    print(f"Summary enabled: {agent2.enable_summary}")
    print("Use case: Longer conversations where recent context is important\n")
    
    # Example 3: Smaller context window (6 messages) - saves tokens
    print("=" * 60)
    print("Example 3: Smaller Context Window (Token Efficient)")
    print("=" * 60)
    agent3 = Agent(
        name="EfficientBot",
        model=Gemini("1.5-flash"),
        storage=storage,
        context_window_size=6  # Keep last 6 messages only
    )
    print(f"Context window size: {agent3.context_window_size}")
    print(f"Summary enabled: {agent3.enable_summary}")
    print("Use case: Cost-sensitive applications, simple Q&A\n")
    
    # Example 4: Summary mode enabled
    print("=" * 60)
    print("Example 4: Summary Mode Enabled")
    print("=" * 60)
    agent4 = Agent(
        name="SummaryBot",
        model=Gemini("1.5-flash"),
        storage=storage,
        context_window_size=10,
        enable_summary=True  # Summarize old messages
    )
    print(f"Context window size: {agent4.context_window_size}")
    print(f"Summary enabled: {agent4.enable_summary}")
    print("Use case: Very long conversations (100+ messages)")
    print("Benefit: Retains awareness of early conversation without token waste\n")
    
    # Cleanup
    await storage.disconnect()
    
    if os.path.exists("conversation_config_demo.db"):
        os.remove("conversation_config_demo.db")
    
    print("\n" + "=" * 60)
    print("CONFIGURATION GUIDE:")
    print("=" * 60)
    print("context_window_size:")
    print("  - Default: 10 (good for most use cases)")
    print("  - Increase: More context, more tokens")
    print("  - Decrease: Less context, fewer tokens")
    print()
    print("enable_summary:")
    print("  - False (default): Drop old messages")
    print("  - True: Summarize old messages into system message")
    print("  - Use when: Very long conversations (100+ messages)")

if __name__ == "__main__":
    asyncio.run(main())
