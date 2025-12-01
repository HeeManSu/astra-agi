"""
Test Context Window Management

This test verifies that the memory layer correctly limits the number of historical messages
loaded into the context window based on the `num_history_responses` configuration.

What it tests:
1. Memory configuration: `num_history_responses` limits the context window size
2. Agent.invoke(): How history is loaded and passed to the model
3. MemoryManager.get_context(): Sliding window implementation
4. AgentStorage.get_history(): Message retrieval from storage

Codebase components tested:
- framework.memory.memory.AgentMemory: Memory configuration model
- framework.memory.manager.MemoryManager: Context window management
- framework.agents.agent.Agent: History loading in invoke() method
- framework.storage.memory.AgentStorage: Message retrieval from storage
- framework.agents.agent.Agent._prepare_messages(): Message preparation with history

Test scenario:
- Configure memory to keep only 2 recent responses (4 messages: 2 user + 2 assistant)
- Send 5 messages to the agent
- Verify that only the last 2 responses (messages 3-4) are included in context
- Verify that older messages (1-2) are excluded from context
"""

import asyncio
from collections.abc import AsyncIterator
import os
from typing import Any
from uuid import uuid4

from framework.agents import Agent
from framework.memory import AgentMemory
from framework.models import Model, ModelResponse
from framework.storage.databases.libsql import LibSQLStorage


class MockModel(Model):
    """
    Mock model that captures the messages sent to it.

    This allows us to verify what context was actually passed to the model,
    without making real API calls.
    """

    def __init__(self):
        super().__init__(id="mock", name="Mock", provider="mock", model_id="mock-1")
        self.last_messages = []  # Store messages from last invoke call

    async def invoke(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """
        Capture messages for verification.

        In a real model, this would send messages to the LLM API.
        Here we just store them to verify the context window.
        """
        self.last_messages = messages
        return ModelResponse(content="Response")

    async def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ModelResponse]:
        """Mock streaming implementation."""
        yield ModelResponse(content="Response")


async def test_context_window():
    """
    Test that context window correctly limits historical messages.

    Test flow:
    1. Configure memory to keep only 2 recent responses
    2. Send 5 messages (creates 5 user + 5 assistant = 10 total messages)
    3. On the 5th invoke, verify only messages 3-4 are in context
    4. Verify older messages (1-2) are excluded
    """
    print("\nTesting Context Window...")

    # Setup: Create a temporary database for this test
    db_file = "./test_context.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    # Initialize storage backend (LibSQLStorage)
    # This will be wrapped by AgentStorage inside the Agent
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{db_file}")

    # Create mock model to capture messages
    model = MockModel()

    # Configure memory to keep only 2 recent responses
    # This means: 2 responses * 2 messages per response (user + assistant) = 4 messages max
    # Tests: framework.memory.memory.AgentMemory
    memory = AgentMemory(num_history_responses=2, add_history_to_messages=True)

    # Create agent with storage and memory configuration
    # Tests: framework.agents.agent.Agent.__init__()
    # - How AgentStorage is created from storage backend
    # - How MemoryManager is initialized with memory config
    agent = Agent(
        name="ContextAgent",
        instructions="System instructions",
        model=model,
        storage=storage,  # Storage backend (will be wrapped in AgentStorage)
        memory=memory,  # Memory configuration
    )

    # Speed up test by reducing debounce time
    # This ensures messages are saved quickly for verification
    if agent.storage:
        agent.storage.queue.debounce_seconds = 0.01

    # Create a unique thread ID for this conversation
    thread_id = f"thread-{uuid4().hex[:8]}"

    # Send 5 messages to the agent
    # Each invoke will:
    # 1. Load history (via MemoryManager.get_context())
    # 2. Prepare messages with history (via Agent._prepare_messages())
    # 3. Save messages to storage (via AgentStorage.add_message())
    # Tests: framework.agents.agent.Agent.invoke()
    for i in range(5):
        await agent.invoke(f"Message {i + 1}", thread_id=thread_id)
        # Wait for storage queue to flush (messages are saved asynchronously)
        await asyncio.sleep(0.1)

    # Verify context window in the last invoke (5th message)
    # Expected messages sent to model:
    # 1. System instruction (from agent.instructions)
    # 2. Message 3 (User) - oldest message in window
    # 3. Response 3 (Assistant) - oldest response in window
    # 4. Message 4 (User)
    # 5. Response 4 (Assistant)
    # 6. Message 5 (User) - current message
    #
    # Messages 1-2 should be excluded (outside the window)
    #
    # Tests: framework.memory.manager.MemoryManager.get_context()
    # - Sliding window calculation: limit = num_history_responses * 2
    # - Message retrieval: storage.get_history(thread_id, limit=4)
    # - Message reconstruction: storage._message_to_dict()

    print(f"Messages sent to model: {len(model.last_messages)}")
    for msg in model.last_messages:
        print(f" - {msg['role']}: {msg['content']}")

    # Verify total message count
    # System (1) + History window (4) + Current User (1) = 6 messages
    assert len(model.last_messages) == 6, (
        f"Expected 6 messages (system + 4 history + current), got {len(model.last_messages)}"
    )

    # Verify oldest message in context is Message 3 (not Message 1 or 2)
    # This confirms that messages 1-2 were excluded from the context window
    assert model.last_messages[1]["content"] == "Message 3", (
        "Oldest message in context should be Message 3, not Message 1 or 2"
    )

    # Verify current message is Message 5
    assert model.last_messages[5]["content"] == "Message 5", "Current message should be Message 5"

    print("Context window verified!")
    print("✓ Only last 2 responses (messages 3-4) included in context")
    print("✓ Older messages (1-2) correctly excluded")

    # Cleanup
    await storage.disconnect()
    if os.path.exists(db_file):
        os.remove(db_file)


if __name__ == "__main__":
    asyncio.run(test_context_window())
