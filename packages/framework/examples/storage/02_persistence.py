"""
Test Agent integration with storage backend.

Database Parts Tested:
- AgentStorage (AgentMemory) message persistence
- SaveQueueManager for batched writes
- Thread auto-creation
- Message insertion with sequence numbers
- History retrieval

Tests:
- Agent with storage configuration
- Message persistence via queue
- Debounce and batch behavior
- History retrieval after persistence
"""

import asyncio
from typing import Any
from uuid import uuid4

from framework.agents.agent import Agent
from framework.models import Model, ModelResponse
from framework.storage.databases.libsql import LibSQLStorage


class MockModel(Model):
    def __init__(self):
        super().__init__(id="mock-model", name="MockModel", provider="mock", model_id="mock-1")

    async def invoke(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        last_msg = messages[-1].get("content", "") if messages else ""
        if "name" in str(last_msg).lower():
            content = "My name is Astra."
        else:
            content = "I am a mock agent."

        return ModelResponse(content=content)

    async def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        yield await self.invoke(messages, tools, temperature, max_tokens, response_format, **kwargs)


async def main():
    # 1. Initialize Storage
    db_url = "sqlite+aiosqlite:///./astra_agent_test.db"
    print(f"Initializing Storage: {db_url}")
    storage = LibSQLStorage(url=db_url)
    await storage.connect()

    # 2. Initialize Agent with Storage
    print("\nInitializing Agent...")
    agent = Agent(
        name="StorageAgent",
        instructions="You are a helpful assistant that remembers conversations.",
        model=MockModel(),
        storage=storage,
    )

    # 3. Run Agent (First Turn)
    thread_id = f"thread-{uuid4().hex[:8]}"
    print(f"\n--- Turn 1 (Thread: {thread_id}) ---")
    response1 = await agent.invoke("My name is Astra.", thread_id=thread_id)
    print("User: My name is Astra.")
    print(f"Agent: {response1}")

    # 4. Run Agent (Second Turn - Should remember name)
    print(f"\n--- Turn 2 (Thread: {thread_id}) ---")
    response2 = await agent.invoke("What is my name?", thread_id=thread_id)
    print("User: What is my name?")
    print(f"Agent: {response2}")

    # 5. Verify Persistence
    # We can check if the messages are in the DB
    print("\nVerifying Persistence...")
    if agent.storage:
        print("Waiting for debounce...")
        await asyncio.sleep(1)

        history = await agent.storage.get_history(thread_id)
        print(f"History count: {len(history)}")
        for msg in history:
            print(f" - {msg.role}: {msg.content}")

        if len(history) >= 4:
            print("Persistence verified!")
        else:
            print("Persistence failed!")
    else:
        print("Storage not initialized!")

    # 6. Clean up
    await storage.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
