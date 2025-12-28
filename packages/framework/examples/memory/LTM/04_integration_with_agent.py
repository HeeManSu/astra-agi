"""
Example 4: Integration with Agent

Tests persistent facts integration with Agent:
1. Enable persistent facts on agent
2. Automatic fact extraction during invoke
3. Fact retrieval for context
4. End-to-end conversation flow

Uses local HuggingFace model - no API key required.
"""

import asyncio

from framework.agents import Agent
from framework.models.huggingface import HuggingFaceLocal
from framework.storage.databases.mongodb import MongoDBStorage


async def main():
    """Test agent integration."""
    print("=== Agent Integration Test ===\n")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_ltm_test")
    await storage.connect()

    print("Loading local model (first time may take a few minutes to download)...")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct")

    print("\n1. Creating agent with persistent facts enabled...")
    agent = Agent(
        name="PersonalAssistant",
        instructions="You are a helpful assistant that remembers user preferences.",
        model=model,
        storage=storage,
        enable_persistent_facts=True,  # Enable LTM
    )

    user_id = "user_integration_test"
    thread_id_1 = "thread_1"
    thread_id_2 = "thread_2"

    print("\n2. First conversation - user shares information...")
    response1 = await agent.invoke(
        "Hi, my name is Alex. I live in Seattle and I love reading science fiction books. "
        "I prefer dark mode UI and morning meetings.",
        user_id=user_id,
        thread_id=thread_id_1,
    )
    print(f"   Agent: {response1[:200]}...")

    # Give time for async operations
    await asyncio.sleep(1)

    print("\n3. Checking extracted facts...")
    if agent.persistent_facts:
        all_facts = await agent.persistent_facts.get_all(scope_id=user_id)
        print(f"   Extracted {len(all_facts)} facts:")
        for fact in all_facts:
            print(f"   - {fact.key}: {fact.value}")

    print("\n4. Second conversation - different thread, agent recalls...")
    response2 = await agent.invoke(
        "What do you know about me?",
        user_id=user_id,
        thread_id=thread_id_2,  # Different thread
    )
    print(f"   Agent: {response2[:200]}...")
    print("   ✅ Agent should recall user's name, location, preferences")

    await asyncio.sleep(1)

    print("\n5. Third conversation - user updates preferences...")
    response3 = await agent.invoke(
        "Actually, I changed my mind. I prefer light mode UI now.",
        user_id=user_id,
        thread_id=thread_id_1,
    )
    print(f"   Agent: {response3[:100]}...")

    await asyncio.sleep(1)

    print("\n6. Verifying updated facts...")
    if agent.persistent_facts:
        updated_facts = await agent.persistent_facts.get_all(scope_id=user_id)
        print("   Current facts:")
        for fact in updated_facts:
            print(f"   - {fact.key}: {fact.value}")

    print("\n7. Fourth conversation - verify update persisted...")
    response4 = await agent.invoke(
        "What is my UI theme preference?",
        user_id=user_id,
        thread_id=thread_id_2,  # Back to thread 2
    )
    print(f"   Agent: {response4[:200]}...")
    print("   ✅ Agent should recall updated preference (light mode)")

    await storage.disconnect()

    print("\n✅ Agent integration test completed!")


if __name__ == "__main__":
    asyncio.run(main())
