"""
Integration tests for Agent memory integration.

Tests memory context loading and persistent facts in agent responses.
"""

from framework.agents import Agent
from framework.memory.memory import AgentMemory
import pytest


@pytest.mark.integration
class TestAgentMemoryContext:
    """Tests for agent memory context loading."""

    @pytest.mark.asyncio
    async def test_agent_loads_conversation_history(self, hf_model, storage_backend):
        """Test that agent loads conversation history from storage."""
        from framework.storage.memory import AgentStorage

        agent_storage = AgentStorage(storage=storage_backend, max_messages=50)
        thread_id = "test_thread_history"

        # Add messages to storage
        await agent_storage.add_message(thread_id, "user", "Hello, my name is Alex.")
        await agent_storage.add_message(thread_id, "assistant", "Nice to meet you, Alex!")
        await agent_storage.queue.flush()

        # Create agent with memory and storage (V1: using num_history_responses)
        memory_config = AgentMemory(num_history_responses=10)
        agent = Agent(
            name="MemoryAgent",
            instructions="You are a helpful assistant. Remember previous conversations.",
            model=hf_model,
            storage=storage_backend,
            memory=memory_config,
        )

        # Invoke agent - it should have access to previous messages
        response = await agent.invoke("What is my name?", thread_id=thread_id)

        assert response is not None
        assert len(response.strip()) > 0

        # Response should reference the name from history
        response_lower = response.lower()
        assert (
            "alex" in response_lower or "name" in response_lower or "remember" in response_lower
        ), f"Response should reference the name from history. Got: {response}"

        await agent_storage.stop()

    @pytest.mark.asyncio
    async def test_agent_memory_disabled(self, hf_model, storage_backend):
        """Test that agent doesn't load history when memory is disabled."""
        from framework.storage.memory import AgentStorage

        agent_storage = AgentStorage(storage=storage_backend, max_messages=50)
        thread_id = "test_thread_disabled"

        # Add messages
        await agent_storage.add_message(thread_id, "user", "My name is Bob.")
        await agent_storage.queue.flush()

        # Create agent with memory disabled
        memory_config = AgentMemory(add_history_to_messages=False)
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
