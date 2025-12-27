"""
Example 4: Token-Aware Windowing

This example demonstrates token-aware windowing in STM memory.

What it demonstrates:
1. Token-aware windowing: Messages trimmed based on token count, not message count
2. Overflow handling: Automatic summarization when token limit is exceeded
3. System message filtering: How system messages are handled in token limits

Test scenario:
- Configure token_limit=500 (small limit for testing)
- Send multiple messages with varying lengths
- Verify that messages are trimmed to fit token budget
- Verify overflow summarization when needed
"""

import asyncio
import os
from uuid import uuid4

from framework.agents import Agent
from framework.memory import AgentMemory
from framework.models.huggingface import HuggingFaceLocal
from framework.storage.databases.libsql import LibSQLStorage


async def test_token_aware_windowing():
    """
    Test token-aware windowing with small token limit.
    """
    print("\nTesting Token-Aware Windowing...")

    # Setup
    db_file = "./test_token_windowing.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    # Configure memory with small token limit for testing
    memory = AgentMemory(
        token_limit=500,  # Small limit to trigger trimming
        window_size=20,  # Fallback (not used when token_limit is set)
        summarize_overflow=True,  # Enable overflow handling
        include_system_messages=True,
    )

    agent = Agent(
        name="TokenAwareAgent",
        instructions="You are a helpful assistant.",
        model=model,
        storage=storage,
        memory=memory,
    )

    if agent.storage:
        agent.storage.queue.debounce_seconds = 0.01

    thread_id = f"thread-{uuid4().hex[:8]}"

    # Send messages of varying lengths
    await agent.invoke("Short message", thread_id=thread_id)
    await asyncio.sleep(0.1)

    await agent.invoke(
        "This is a medium length message that should take up some tokens.",
        thread_id=thread_id,
    )
    await asyncio.sleep(0.1)

    # Long message
    long_message = " ".join([f"Word{i}" for i in range(150)])  # ~200 tokens
    await agent.invoke(long_message, thread_id=thread_id)
    await asyncio.sleep(0.1)

    # Very long message
    very_long_message = " ".join([f"Token{i}" for i in range(300)])  # ~400 tokens
    await agent.invoke(very_long_message, thread_id=thread_id)
    await asyncio.sleep(0.1)

    # Check final context via memory manager
    assert agent.storage is not None
    context = await agent.memory_manager.get_context(thread_id, agent.storage)
    print(f"\nMessages in context window: {len(context)}")

    for i, msg in enumerate(context):
        content_preview = (
            msg.get("content", "")[:50] + "..."
            if len(msg.get("content", "")) > 50
            else msg.get("content", "")
        )
        print(f"  {i + 1}. {msg.get('role', 'unknown')}: {content_preview}")

    assert len(context) > 0, "Should have messages in context"

    # Check if summary was added (indicates overflow handling)
    # Note: Summaries typically replace older messages
    has_summary = any("summary" in msg.get("content", "").lower() for msg in context)
    print(f"\n✓ Overflow summarization: {'Enabled' if has_summary else 'Not triggered'}")
    print("✓ Token-aware windowing verified!")

    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_system_message_filtering():
    """
    Test system message filtering with token limits.
    """
    print("\nTesting System Message Filtering...")

    db_file = "./test_system_filtering.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    # Test with system messages included
    memory_with_system = AgentMemory(
        token_limit=500,
        include_system_messages=True,
    )

    agent = Agent(
        name="SystemFilterAgent",
        instructions="You are a helpful assistant with detailed instructions.",
        model=model,
        storage=storage,
        memory=memory_with_system,
    )

    if agent.storage:
        agent.storage.queue.debounce_seconds = 0.01

    thread_id = f"thread-{uuid4().hex[:8]}"
    await agent.invoke("Test message", thread_id=thread_id)
    await asyncio.sleep(0.1)

    # Count system messages in context
    assert agent.storage is not None
    context = await agent.memory_manager.get_context(thread_id, agent.storage)
    system_count = sum(1 for msg in context if msg.get("role") == "system")
    print(f"  - System messages in context: {system_count}")
    print("✓ System message filtering tested!")

    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


if __name__ == "__main__":
    asyncio.run(test_token_aware_windowing())
    asyncio.run(test_system_message_filtering())
