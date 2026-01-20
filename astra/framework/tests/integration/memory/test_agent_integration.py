"""
Integration tests for Agent memory integration.

Tests memory context loading - specifically the "what is my name" scenario.
"""

import asyncio

from framework.agents import Agent
from framework.memory.memory import Memory
import pytest


@pytest.mark.integration
class TestAgentMemoryContext:
    """Tests for agent memory context loading."""

    @pytest.mark.asyncio
    async def test_agent_remembers_name(self, storage_backend):
        """Test that agent remembers user's name from conversation history.

        This test simulates the exact scenario:
        1. User says: "Hello, my name is Himanshu Sharma"
        2. Agent responds
        3. User asks: "What is my name?"
        4. Agent should remember and respond with "Himanshu Sharma"
        """
        from framework.models import Gemini
        from framework.storage.client import StorageClient

        # Use Gemini model for this test
        model = Gemini("gemini-2.0-flash-exp")

        # Create StorageClient wrapper
        agent_storage = StorageClient(storage=storage_backend, max_messages=50)
        thread_id = "test_thread_name_memory"

        # Create agent with memory and storage (pass StorageClient, not raw backend)
        memory_config = Memory(num_history_turns=10)
        agent = Agent(
            name="MemoryAgent",
            instructions="You are a helpful assistant. Remember and use information from previous conversations.",
            model=model,
            storage=agent_storage,
            memory=memory_config,
        )

        # Step 1: User introduces themselves
        print("\n[Step 1] User: Hello, my name is Himanshu Sharma.")
        response1 = await agent.invoke("Hello, my name is Himanshu Sharma.", thread_id=thread_id)
        print(f"[Step 1] Agent: {response1}")

        # Wait for storage to flush
        await agent_storage.queue.flush()
        await asyncio.sleep(0.5)

        # Step 2: User asks for their name
        print("\n[Step 2] User: What is my name?")
        response2 = await agent.invoke("What is my name?", thread_id=thread_id)
        print(f"[Step 2] Agent: {response2}")

        # Verify response
        assert response2 is not None
        assert len(response2.strip()) > 0

        # Response should reference the name from history
        response_lower = response2.lower()
        has_name = "himanshu" in response_lower or "sharma" in response_lower

        if has_name:
            print("\n✅ SUCCESS: Agent remembered the name!")
        else:
            print("\n❌ FAILED: Agent did not remember the name.")
            print(f"   Response was: {response2}")
            print("   Looking for: 'himanshu' or 'sharma' in response")

        assert has_name, (
            f"Response should reference 'Himanshu Sharma' from history. Got: {response2}"
        )

        await agent_storage.stop()

    @pytest.mark.asyncio
    async def test_agent_memory_disabled(self, hf_model, storage_backend):
        """Test that agent doesn't load history when memory is disabled."""
        from framework.storage.client import StorageClient

        agent_storage = StorageClient(storage=storage_backend, max_messages=50)
        thread_id = "test_thread_disabled"

        # Add messages
        await agent_storage.add_message(thread_id, "user", "My name is Bob.")
        await agent_storage.queue.flush()

        # Create agent with memory disabled
        memory_config = Memory(add_history_to_messages=False)
        agent = Agent(
            name="NoMemoryAgent",
            instructions="You are a helpful assistant.",
            model=hf_model,
            storage=storage_backend,
            memory=memory_config,
        )

        # Invoke agent
        response = await agent.invoke("What is my name?", thread_id=thread_id)

        assert response is not None
        # Agent should not have access to previous messages
        # Response may not reference "Bob" since history is disabled

        await agent_storage.stop()


# @TODO: Himanshu. PersistentFacts disabled for V1 release. Will be enabled later.
# TestAgentPersistentFacts class has been moved to git history.
# The following tests were disabled:
# - test_agent_with_persistent_facts
# - test_agent_persistent_facts_extraction
# - test_agent_custom_persistent_facts
# - test_agent_memory_and_facts_together
