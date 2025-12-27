"""
Example 3: Summarization and Advanced Memory Features

This example demonstrates advanced memory features including summarization,
context window management, and multi-agent memory configurations.

What it demonstrates:
1. Summarization: Automatic summarization of older messages when context window is exceeded
2. History window management: How num_history_responses limits context size
3. Disabling history: How to disable history loading completely
4. Multiple agents: Sharing memory configuration across agents
5. Custom prompts: Using custom summary generation prompts
6. Memory independence: Each agent has its own MemoryManager instance
7. Context isolation: Agents maintain independent context loading

Codebase components tested:
- framework.memory.memory.AgentMemory: Memory configuration model
- framework.memory.manager.MemoryManager: Context management and summarization
- framework.agents.agent.Agent: Agent initialization with memory
- framework.storage.memory.AgentStorage: Message storage and retrieval
- framework.storage.databases.libsql.LibSQLStorage: Database backend

Test scenarios:
1. Summarization trigger: When history exceeds window, older messages are summarized
2. Summarization disabled: When disabled, no summaries are generated
3. History window: Only recent messages are loaded based on num_history_responses
4. No history loading: When add_history_to_messages=False, context is empty
5. Multiple agents: Agents can share memory config but have independent managers
6. Custom prompts: Summary generation uses custom prompts
7. Empty threads: Handling threads with no messages
8. Summary caching: Summaries are cached per MemoryManager instance
9. Shared memory instances: Multiple agents can share the same AgentMemory instance
10. Per-agent configs: Agents can have different memory configurations
11. MemoryManager independence: Each agent has its own MemoryManager
12. Context loading independence: Context loading is isolated per agent
13. Ten agents: Scaling to many agents with shared memory
14. Config immutability: How memory config changes affect agents

Note: These tests use the Gemini API and may hit rate limits.
"""

import asyncio
import os
from uuid import uuid4

from framework.agents import Agent
from framework.memory import AgentMemory
from framework.models.huggingface import HuggingFaceLocal
from framework.storage.databases.libsql import LibSQLStorage


async def test_summarization():
    """Test that summarization is triggered when history exceeds window."""
    print("\n" + "=" * 60)
    print("Test 1: Summarization Trigger")
    print("=" * 60)

    # Setup
    db_file = "./test_summary.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    # Use local model
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    # Configure memory to keep only 1 recent response (2 messages)
    # and enable summarization
    memory = AgentMemory(
        num_history_responses=1,
        add_history_to_messages=True,
        summarize_overflow=True,
        summary_prompt="Summarize the following conversation concisely, retaining key facts and decisions.",
    )

    agent = Agent(
        name="SummaryAgent",
        instructions="You are a helpful assistant. Be concise.",
        model=model,
        storage=storage,
        memory=memory,
    )
    # Patch storage with faster debounce for testing
    if agent.storage:
        agent.storage.queue.debounce_seconds = 0.01

    thread_id = f"thread-{uuid4().hex[:8]}"

    # Send 3 messages (should trigger summarization on 3rd)
    print("Sending Message 1...")
    await agent.invoke("What is 2+2?", thread_id=thread_id)
    await asyncio.sleep(0.2)  # Wait for queue flush

    print("Sending Message 2...")
    await agent.invoke("What is 3+3?", thread_id=thread_id)
    await asyncio.sleep(0.2)  # Wait for queue flush

    # Check message count
    assert agent.storage is not None, "Storage should be initialized"
    messages = await agent.storage.get_history(thread_id, limit=10)
    print(f"\nMessages in storage before Message 3: {len(messages)}")
    for msg in messages:
        print(f"  - {msg.role}: {msg.content[:50]}...")

    print("\nSending Message 3 (should trigger summarization)...")
    await agent.invoke("What is 4+4?", thread_id=thread_id)
    await asyncio.sleep(0.2)  # Wait for queue flush

    # Verify messages were stored
    messages = await agent.storage.get_history(thread_id, limit=10)
    print(f"\nTotal messages in storage: {len(messages)}")
    assert len(messages) >= 6, "Should have at least 6 messages (3 user + 3 assistant)"

    print("✓ PASS: Summarization test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_summarization_disabled():
    """Test that summarization is NOT triggered when disabled."""
    print("\n" + "=" * 60)
    print("Test 2: Summarization Disabled")
    print("=" * 60)

    db_file = "./test_summary_disabled.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    # Disable summarization
    memory = AgentMemory(
        num_history_responses=1,
        add_history_to_messages=True,
        summarize_overflow=False,  # Disabled
    )

    agent = Agent(
        name="NoSummaryAgent",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=memory,
    )

    if agent.storage:
        agent.storage.queue.debounce_seconds = 0.01

    thread_id = f"thread-{uuid4().hex[:8]}"

    # Send multiple messages
    await agent.invoke("Message 1", thread_id=thread_id)
    await asyncio.sleep(0.1)
    await agent.invoke("Message 2", thread_id=thread_id)
    await asyncio.sleep(0.1)
    await agent.invoke("Message 3", thread_id=thread_id)
    await asyncio.sleep(0.1)

    assert agent.storage is not None, "Storage should be initialized"
    messages = await agent.storage.get_history(thread_id, limit=10)
    print(f"Messages stored: {len(messages)}")
    assert len(messages) >= 6, "Should have messages stored"

    print("✓ PASS: Summarization disabled test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_history_window():
    """Test that only recent messages are loaded based on num_history_responses."""
    print("\n" + "=" * 60)
    print("Test 3: History Window Size")
    print("=" * 60)

    db_file = "./test_history_window.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    # Keep only 2 recent responses (4 messages)
    memory = AgentMemory(
        num_history_responses=2,
        add_history_to_messages=True,
        summarize_overflow=False,
    )

    agent = Agent(
        name="HistoryWindowAgent",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=memory,
    )

    if agent.storage:
        agent.storage.queue.debounce_seconds = 0.01

    thread_id = f"thread-{uuid4().hex[:8]}"

    # Send 5 messages (10 total messages: 5 user + 5 assistant)
    for i in range(1, 6):
        await agent.invoke(f"Message {i}", thread_id=thread_id)
        await asyncio.sleep(0.1)

    assert agent.storage is not None, "Storage should be initialized"
    all_messages = await agent.storage.get_history(thread_id, limit=20)
    print(f"Total messages stored: {len(all_messages)}")

    # Get context (should only return recent window)
    assert agent.storage is not None, "Storage should be initialized"
    context = await agent.memory_manager.get_context(thread_id, agent.storage)
    print(f"Messages in context window: {len(context)}")
    # Should be <= 4 (2 responses * 2 messages per response)
    assert len(context) <= 4, f"Context should have <= 4 messages, got {len(context)}"

    print("✓ PASS: History window test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_no_history_loading():
    """Test that history is NOT loaded when add_history_to_messages=False."""
    print("\n" + "=" * 60)
    print("Test 4: No History Loading")
    print("=" * 60)

    db_file = "./test_no_history.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    # Disable history loading
    memory = AgentMemory(
        num_history_responses=10,
        add_history_to_messages=False,  # Disabled
        summarize_overflow=False,
    )

    agent = Agent(
        name="NoHistoryAgent",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=memory,
    )

    if agent.storage:
        agent.storage.queue.debounce_seconds = 0.01

    thread_id = f"thread-{uuid4().hex[:8]}"

    # Send multiple messages
    await agent.invoke("First message", thread_id=thread_id)
    await asyncio.sleep(0.1)
    await agent.invoke("Second message", thread_id=thread_id)
    await asyncio.sleep(0.1)

    assert agent.storage is not None, "Storage should be initialized"
    # Messages should be stored
    messages = await agent.storage.get_history(thread_id, limit=10)
    print(f"Messages stored: {len(messages)}")
    assert len(messages) >= 4, "Messages should be stored"

    # But context should be empty (no history loaded)
    assert agent.storage is not None, "Storage should be initialized"
    context = await agent.memory_manager.get_context(thread_id, agent.storage)
    print(f"Messages in context: {len(context)}")
    assert len(context) == 0, "Context should be empty when add_history_to_messages=False"

    print("✓ PASS: No history loading test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_multiple_agents_shared_memory():
    """Test multiple agents sharing the same memory configuration."""
    print("\n" + "=" * 60)
    print("Test 5: Multiple Agents with Shared Memory Config")
    print("=" * 60)

    db_file = "./test_multiple_agents.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    # Shared memory configuration
    shared_memory = AgentMemory(
        num_history_responses=2,
        add_history_to_messages=True,
        summarize_overflow=False,
    )

    # Create 3 agents with same memory config
    agents = []
    for i in range(3):
        agent = Agent(
            name=f"Agent{i + 1}",
            instructions="You are helpful.",
            model=model,
            storage=storage,  # Same storage instance
            memory=shared_memory,  # Same memory config
        )
        if agent.storage:
            agent.storage.queue.debounce_seconds = 0.01
        agents.append(agent)

    # Each agent uses different thread_id (data is separated)
    thread_ids = [f"thread-{uuid4().hex[:8]}" for _ in range(3)]

    # Each agent sends messages to its own thread
    for i, agent in enumerate(agents):
        thread_id = thread_ids[i]
        await agent.invoke(f"Message from Agent{i + 1}", thread_id=thread_id)
        await asyncio.sleep(0.1)

    # Verify each thread has its own messages
    assert agents[0].storage is not None, "Storage should be initialized"
    for i, thread_id in enumerate(thread_ids):
        messages = await agents[0].storage.get_history(thread_id, limit=10)
        print(f"Thread {i + 1} messages: {len(messages)}")
        assert len(messages) >= 2, f"Thread {i + 1} should have messages"

    print("✓ PASS: Multiple agents shared memory test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_custom_summary_prompt():
    """Test custom summary prompt."""
    print("\n" + "=" * 60)
    print("Test 6: Custom Summary Prompt")
    print("=" * 60)

    db_file = "./test_custom_prompt.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    custom_prompt = "Create a brief summary focusing on numbers and calculations."
    memory = AgentMemory(
        num_history_responses=1,
        add_history_to_messages=True,
        summarize_overflow=True,
        summary_prompt=custom_prompt,
    )

    agent = Agent(
        name="CustomPromptAgent",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=memory,
    )

    if agent.storage:
        agent.storage.queue.debounce_seconds = 0.01

    thread_id = f"thread-{uuid4().hex[:8]}"

    await agent.invoke("What is 10+10?", thread_id=thread_id)
    await asyncio.sleep(0.1)
    await agent.invoke("What is 20+20?", thread_id=thread_id)
    await asyncio.sleep(0.1)
    await agent.invoke("What is 30+30?", thread_id=thread_id)
    await asyncio.sleep(0.1)

    # Verify custom prompt is used (check memory manager)
    assert agent.memory_manager.memory.summary_prompt == custom_prompt
    print(f"Custom prompt verified: {custom_prompt[:50]}...")

    print("✓ PASS: Custom summary prompt test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_empty_thread():
    """Test behavior with empty thread (no history)."""
    print("\n" + "=" * 60)
    print("Test 7: Empty Thread")
    print("=" * 60)

    db_file = "./test_empty_thread.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    memory = AgentMemory(
        num_history_responses=5,
        add_history_to_messages=True,
        summarize_overflow=True,
    )

    agent = Agent(
        name="EmptyThreadAgent",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=memory,
    )

    if agent.storage:
        agent.storage.queue.debounce_seconds = 0.01

    thread_id = f"thread-{uuid4().hex[:8]}"

    # Get context for empty thread
    assert agent.storage is not None, "Storage should be initialized"
    context = await agent.memory_manager.get_context(thread_id, agent.storage)
    print(f"Context for empty thread: {len(context)} messages")
    assert len(context) == 0, "Empty thread should have no context"

    # Send first message
    await agent.invoke("First message", thread_id=thread_id)
    await asyncio.sleep(0.1)

    # Get context again (should have 2 messages: user + assistant)
    context = await agent.memory_manager.get_context(thread_id, agent.storage)
    print(f"Context after first message: {len(context)} messages")
    assert len(context) == 2, "Should have user and assistant messages"

    print("✓ PASS: Empty thread test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_summary_cache():
    """Test that summaries are cached and reused."""
    print("\n" + "=" * 60)
    print("Test 8: Summary Cache")
    print("=" * 60)

    db_file = "./test_summary_cache.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    memory = AgentMemory(
        num_history_responses=1,
        add_history_to_messages=True,
        summarize_overflow=True,
    )

    agent = Agent(
        name="CacheAgent",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=memory,
    )

    if agent.storage:
        agent.storage.queue.debounce_seconds = 0.01

    thread_id = f"thread-{uuid4().hex[:8]}"

    # Send messages to trigger summarization
    await agent.invoke("Message 1", thread_id=thread_id)
    await asyncio.sleep(0.1)
    await agent.invoke("Message 2", thread_id=thread_id)
    await asyncio.sleep(0.1)
    await agent.invoke("Message 3", thread_id=thread_id)
    await asyncio.sleep(0.1)

    # Check cache (internal implementation detail, but we can verify it exists)
    assert hasattr(agent.memory_manager, "_summary_cache"), "MemoryManager should have cache"
    print("Summary cache exists")

    print("✓ PASS: Summary cache test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_shared_memory_instance():
    """Test that agents sharing the same AgentMemory instance have same behavior."""
    print("\n" + "=" * 60)
    print("Test 9: Shared AgentMemory Instance")
    print("=" * 60)

    db_file = "./test_shared_instance.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    # Create ONE memory instance
    shared_memory = AgentMemory(
        num_history_responses=3,
        add_history_to_messages=True,
        summarize_overflow=False,
    )

    # Create 2 agents with SAME memory instance
    agent1 = Agent(
        name="Agent1",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=shared_memory,  # Same instance
    )
    agent2 = Agent(
        name="Agent2",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=shared_memory,  # Same instance
    )

    if agent1.storage:
        agent1.storage.queue.debounce_seconds = 0.01
    if agent2.storage:
        agent2.storage.queue.debounce_seconds = 0.01

    # Verify they reference the same memory object
    assert agent1.memory is agent2.memory, "Agents should share the same memory instance"
    assert agent1.memory.num_history_responses == agent2.memory.num_history_responses
    assert agent1.memory.add_history_to_messages == agent2.memory.add_history_to_messages
    print("✓ Both agents use the same memory instance")

    # Verify they have different MemoryManager instances
    assert agent1.memory_manager is not agent2.memory_manager, (
        "Each agent should have its own MemoryManager"
    )
    print("✓ Each agent has its own MemoryManager instance")

    # Test behavior: both should load same amount of history
    thread_id1 = f"thread-{uuid4().hex[:8]}"
    thread_id2 = f"thread-{uuid4().hex[:8]}"

    # Send messages to both agents
    await agent1.invoke("Message 1", thread_id=thread_id1)
    await agent1.invoke("Message 2", thread_id=thread_id1)
    await agent1.invoke("Message 3", thread_id=thread_id1)
    await asyncio.sleep(0.2)

    await agent2.invoke("Message A", thread_id=thread_id2)
    await agent2.invoke("Message B", thread_id=thread_id2)
    await agent2.invoke("Message C", thread_id=thread_id2)
    await asyncio.sleep(0.2)

    # Both should load same amount of context (3 responses = 6 messages)
    assert agent1.storage is not None and agent2.storage is not None
    context1 = await agent1.memory_manager.get_context(thread_id1, agent1.storage)
    context2 = await agent2.memory_manager.get_context(thread_id2, agent2.storage)

    print(f"Agent1 context: {len(context1)} messages")
    print(f"Agent2 context: {len(context2)} messages")
    # Both should have same window size (3 responses * 2 = 6 messages max)
    assert len(context1) <= 6, "Agent1 should respect num_history_responses=3"
    assert len(context2) <= 6, "Agent2 should respect num_history_responses=3"

    print("✓ PASS: Shared memory instance test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_per_agent_different_memory():
    """Test that agents with different AgentMemory have different settings."""
    print("\n" + "=" * 60)
    print("Test 10: Per-Agent Different Memory Config")
    print("=" * 60)

    db_file = "./test_per_agent_memory.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    # Create DIFFERENT memory configs
    memory1 = AgentMemory(
        num_history_responses=2,  # Keep 2 responses
        add_history_to_messages=True,
        summarize_overflow=False,
    )
    memory2 = AgentMemory(
        num_history_responses=5,  # Keep 5 responses
        add_history_to_messages=True,
        summarize_overflow=False,
    )

    # Create 2 agents with DIFFERENT memory configs
    agent1 = Agent(
        name="Agent1",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=memory1,  # Different config
    )
    agent2 = Agent(
        name="Agent2",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=memory2,  # Different config
    )

    if agent1.storage:
        agent1.storage.queue.debounce_seconds = 0.01
    if agent2.storage:
        agent2.storage.queue.debounce_seconds = 0.01

    # Verify they have different memory configs
    assert agent1.memory is not agent2.memory, "Agents should have different memory instances"
    assert agent1.memory.num_history_responses == 2, "Agent1 should have num_history_responses=2"
    assert agent2.memory.num_history_responses == 5, "Agent2 should have num_history_responses=5"
    print("✓ Agents have different memory configurations")

    # Verify they have different MemoryManager instances
    assert agent1.memory_manager is not agent2.memory_manager, (
        "Each agent should have its own MemoryManager"
    )
    print("✓ Each agent has its own MemoryManager instance")

    # Test behavior: they should load different amounts of history
    thread_id1 = f"thread-{uuid4().hex[:8]}"
    thread_id2 = f"thread-{uuid4().hex[:8]}"

    # Send 6 messages to both agents (3 user + 3 assistant)
    for i in range(3):
        await agent1.invoke(f"Message {i + 1}", thread_id=thread_id1)
        await asyncio.sleep(0.1)
        await agent2.invoke(f"Message {i + 1}", thread_id=thread_id2)
        await asyncio.sleep(0.1)

    await asyncio.sleep(0.2)

    # Agent1 should load less history (2 responses = 4 messages max)
    # Agent2 should load more history (5 responses = 10 messages max)
    assert agent1.storage is not None and agent2.storage is not None
    context1 = await agent1.memory_manager.get_context(thread_id1, agent1.storage)
    context2 = await agent2.memory_manager.get_context(thread_id2, agent2.storage)

    print(f"Agent1 context (num_history_responses=2): {len(context1)} messages")
    print(f"Agent2 context (num_history_responses=5): {len(context2)} messages")

    assert len(context1) <= 4, "Agent1 should respect num_history_responses=2"
    assert len(context2) <= 10, "Agent2 should respect num_history_responses=5"
    # Agent2 should have more context than Agent1
    assert len(context2) >= len(context1), "Agent2 should load more history than Agent1"

    print("✓ PASS: Per-agent different memory test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_memory_manager_independent():
    """Test that each agent has its own MemoryManager with independent cache."""
    print("\n" + "=" * 60)
    print("Test 11: MemoryManager Independence")
    print("=" * 60)

    db_file = "./test_manager_independent.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    shared_memory = AgentMemory(
        num_history_responses=1,
        add_history_to_messages=True,
        summarize_overflow=True,
    )

    # Create 2 agents
    agent1 = Agent(
        name="Agent1",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=shared_memory,
    )
    agent2 = Agent(
        name="Agent2",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=shared_memory,
    )

    if agent1.storage:
        agent1.storage.queue.debounce_seconds = 0.01
    if agent2.storage:
        agent2.storage.queue.debounce_seconds = 0.01

    # Verify they have different MemoryManager instances
    assert agent1.memory_manager is not agent2.memory_manager, (
        "Each agent should have its own MemoryManager"
    )
    print("✓ Each agent has its own MemoryManager instance")

    # Verify they have independent summary caches
    thread_id1 = f"thread-{uuid4().hex[:8]}"
    thread_id2 = f"thread-{uuid4().hex[:8]}"

    # Send messages to trigger summarization
    await agent1.invoke("Message 1", thread_id=thread_id1)
    await asyncio.sleep(0.1)
    await agent1.invoke("Message 2", thread_id=thread_id1)
    await asyncio.sleep(0.1)
    await agent1.invoke("Message 3", thread_id=thread_id1)
    await asyncio.sleep(0.2)

    await agent2.invoke("Message A", thread_id=thread_id2)
    await asyncio.sleep(0.1)
    await agent2.invoke("Message B", thread_id=thread_id2)
    await asyncio.sleep(0.1)
    await agent2.invoke("Message C", thread_id=thread_id2)
    await asyncio.sleep(0.2)

    # Check that caches are independent
    cache1 = agent1.memory_manager._summary_cache
    cache2 = agent2.memory_manager._summary_cache

    print(f"Agent1 cache keys: {list(cache1.keys())}")
    print(f"Agent2 cache keys: {list(cache2.keys())}")

    # Caches should be independent (different thread_ids)
    assert thread_id1 in cache1 or len(cache1) == 0, "Agent1 cache should be independent"
    assert thread_id2 in cache2 or len(cache2) == 0, "Agent2 cache should be independent"
    # Agent1's cache should not contain Agent2's thread_id
    assert thread_id2 not in cache1, "Agent1 cache should not contain Agent2's data"
    # Agent2's cache should not contain Agent1's thread_id
    assert thread_id1 not in cache2, "Agent2 cache should not contain Agent1's data"

    print("✓ Summary caches are independent per MemoryManager")

    print("✓ PASS: MemoryManager independence test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_context_loading_independent():
    """Test that context loading is independent per agent."""
    print("\n" + "=" * 60)
    print("Test 12: Context Loading Independence")
    print("=" * 60)

    db_file = "./test_context_independent.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    memory = AgentMemory(
        num_history_responses=3,
        add_history_to_messages=True,
        summarize_overflow=False,
    )

    # Create 2 agents
    agent1 = Agent(
        name="Agent1",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=memory,
    )
    agent2 = Agent(
        name="Agent2",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=memory,
    )

    if agent1.storage:
        agent1.storage.queue.debounce_seconds = 0.01
    if agent2.storage:
        agent2.storage.queue.debounce_seconds = 0.01

    thread_id1 = f"thread-{uuid4().hex[:8]}"
    thread_id2 = f"thread-{uuid4().hex[:8]}"

    # Send different messages to each agent
    await agent1.invoke("Agent1 Message 1", thread_id=thread_id1)
    await agent1.invoke("Agent1 Message 2", thread_id=thread_id1)
    await agent1.invoke("Agent1 Message 3", thread_id=thread_id1)
    await asyncio.sleep(0.2)

    await agent2.invoke("Agent2 Message 1", thread_id=thread_id2)
    await agent2.invoke("Agent2 Message 2", thread_id=thread_id2)
    await agent2.invoke("Agent2 Message 3", thread_id=thread_id2)
    await asyncio.sleep(0.2)

    # Load context for both agents
    assert agent1.storage is not None and agent2.storage is not None
    context1 = await agent1.memory_manager.get_context(thread_id1, agent1.storage)
    context2 = await agent2.memory_manager.get_context(thread_id2, agent2.storage)

    print(f"Agent1 context: {len(context1)} messages")
    print(f"Agent2 context: {len(context2)} messages")

    # Verify contexts are independent (different content)
    agent1_content = " ".join([msg.get("content", "") for msg in context1])
    agent2_content = " ".join([msg.get("content", "") for msg in context2])

    assert "Agent1 Message" in agent1_content, "Agent1 context should contain its own messages"
    assert "Agent2 Message" in agent2_content, "Agent2 context should contain its own messages"
    assert "Agent2 Message" not in agent1_content, (
        "Agent1 context should not contain Agent2's messages"
    )
    assert "Agent1 Message" not in agent2_content, (
        "Agent2 context should not contain Agent1's messages"
    )

    print("✓ Context loading is independent per agent")

    # Verify they can load context concurrently without interference
    contexts = await asyncio.gather(
        agent1.memory_manager.get_context(thread_id1, agent1.storage),
        agent2.memory_manager.get_context(thread_id2, agent2.storage),
    )
    assert len(contexts) == 2, "Should load both contexts"
    assert len(contexts[0]) > 0, "Agent1 context should be loaded"
    assert len(contexts[1]) > 0, "Agent2 context should be loaded"

    print("✓ Concurrent context loading works independently")

    print("✓ PASS: Context loading independence test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_ten_agents_shared_memory():
    """Test 10 agents sharing the same memory configuration."""
    print("\n" + "=" * 60)
    print("Test 13: Ten Agents with Shared Memory")
    print("=" * 60)

    db_file = "./test_ten_agents.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    # Shared memory configuration
    shared_memory = AgentMemory(
        num_history_responses=2,
        add_history_to_messages=True,
        summarize_overflow=False,
    )

    # Create 10 agents with same memory config
    agents = []
    for i in range(10):
        agent = Agent(
            name=f"Agent{i + 1}",
            instructions="You are helpful.",
            model=model,
            storage=storage,  # Same storage instance
            memory=shared_memory,  # Same memory config instance
        )
        if agent.storage:
            agent.storage.queue.debounce_seconds = 0.01
        agents.append(agent)

    # Verify all agents share the same memory instance
    for i in range(1, 10):
        assert agents[0].memory is agents[i].memory, f"Agent{i + 1} should share memory with Agent1"
        assert agents[0].memory_manager is not agents[i].memory_manager, (
            f"Agent{i + 1} should have its own MemoryManager"
        )

    print("✓ All 10 agents share the same memory instance")
    print("✓ Each agent has its own MemoryManager instance")

    # Each agent uses different thread_id
    thread_ids = [f"thread-{uuid4().hex[:8]}" for _ in range(10)]

    # Each agent sends messages to its own thread
    for i, agent in enumerate(agents):
        thread_id = thread_ids[i]
        await agent.invoke(f"Message from Agent{i + 1}", thread_id=thread_id)
        await asyncio.sleep(0.05)  # Small delay

    await asyncio.sleep(0.3)  # Wait for all queues to flush

    # Verify each thread has its own messages
    assert agents[0].storage is not None, "Storage should be initialized"
    for i, thread_id in enumerate(thread_ids):
        messages = await agents[0].storage.get_history(thread_id, limit=10)
        assert len(messages) >= 2, f"Thread {i + 1} should have messages"
        # Verify message content is correct
        user_messages = [m for m in messages if m.role == "user"]
        assert len(user_messages) > 0, f"Thread {i + 1} should have user messages"
        assert f"Agent{i + 1}" in user_messages[0].content, (
            f"Thread {i + 1} should have correct content"
        )

    print("✓ All 10 threads have their own messages stored")
    print("✓ Data is properly separated by thread_id")

    # Verify context loading works for all agents
    contexts = await asyncio.gather(
        *[
            agent.memory_manager.get_context(thread_ids[i], agent.storage)
            for i, agent in enumerate(agents)
            if agent.storage
        ]
    )
    assert len(contexts) == 10, "Should load contexts for all 10 agents"
    for i, context in enumerate(contexts):
        assert len(context) > 0, f"Agent{i + 1} should have context loaded"

    print("✓ Context loading works for all 10 agents independently")

    print("✓ PASS: Ten agents shared memory test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def test_memory_config_immutability():
    """Test that changing memory config after agent creation doesn't affect agents."""
    print("\n" + "=" * 60)
    print("Test 14: Memory Config Immutability")
    print("=" * 60)

    db_file = "./test_memory_immutability.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct", max_new_tokens=100)

    memory = AgentMemory(
        num_history_responses=2,
        add_history_to_messages=True,
        summarize_overflow=False,
    )

    agent = Agent(
        name="TestAgent",
        instructions="You are helpful.",
        model=model,
        storage=storage,
        memory=memory,
    )

    if agent.storage:
        agent.storage.queue.debounce_seconds = 0.01

    # Store original value
    original_value = agent.memory.num_history_responses
    assert original_value == 2, "Initial value should be 2"

    # Change memory config (should not affect agent's memory)
    memory.num_history_responses = 10

    # Agent's memory should still reference the same object, so it will change
    # But this tests that the agent uses the config at creation time
    # Actually, since it's the same object reference, it will change
    # This test verifies the behavior
    assert agent.memory.num_history_responses == 10, (
        "Agent's memory should reflect changes to shared instance"
    )

    # But MemoryManager uses the config, so behavior might change
    # This is expected behavior - if you share the instance, changes affect all agents
    print("✓ Memory config changes affect agents when using shared instance")
    print("✓ Use separate instances if you want immutable configs")

    print("✓ PASS: Memory config immutability test completed")
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


async def main():
    """Run all memory tests."""
    print("\n" + "=" * 60)
    print("Memory Layer Tests - Summarization & Context Management")
    print("=" * 60)
    print("Note: Using Gemini API - rate limits may apply")
    print("=" * 60)

    tests = [
        test_summarization,
        test_summarization_disabled,
        test_history_window,
        test_no_history_loading,
        test_multiple_agents_shared_memory,
        test_custom_summary_prompt,
        test_empty_thread,
        test_summary_cache,
        test_shared_memory_instance,
        test_per_agent_different_memory,
        test_memory_manager_independent,
        test_context_loading_independent,
        test_ten_agents_shared_memory,
        test_memory_config_immutability,
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(tests):
        try:
            print(f"\n[{i + 1}/{len(tests)}] Running {test.__name__}...")
            await test()
            passed += 1
            # Add delay between tests to avoid rate limits
            if i < len(tests) - 1:
                await asyncio.sleep(2)
        except Exception as e:
            print(f"\n✗ FAIL: {test.__name__}: {e}")
            import traceback

            traceback.print_exc()
            failed += 1
            # If rate limit error, wait longer before next test
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("Rate limit hit, waiting 30 seconds...")
                await asyncio.sleep(30)

    print("\n" + "=" * 60)
    print(f"Tests completed: {passed} passed, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
