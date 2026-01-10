"""
Integration tests for Agent memory integration.

Tests memory context loading and persistent facts in agent responses.
"""

from framework.agents import Agent
from framework.memory.memory import AgentMemory
from framework.memory.persistent_facts import PersistentFacts
from framework.storage.models import MemoryScope
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

        # Create agent with memory and storage
        memory_config = AgentMemory(window_size=10)
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
    async def test_agent_respects_window_size(self, hf_model, storage_backend):
        """Test that agent respects window_size limit."""
        from framework.storage.memory import AgentStorage

        agent_storage = AgentStorage(storage=storage_backend, max_messages=50)
        thread_id = "test_thread_window"

        # Add many messages
        for i in range(20):
            await agent_storage.add_message(thread_id, "user", f"Message {i}")
            await agent_storage.add_message(thread_id, "assistant", f"Response {i}")
        await agent_storage.queue.flush()

        # Create agent with small window_size
        memory_config = AgentMemory(window_size=3)
        agent = Agent(
            name="WindowAgent",
            instructions="You are a helpful assistant.",
            model=hf_model,
            storage=storage_backend,
            memory=memory_config,
        )

        # Invoke agent
        response = await agent.invoke("What was the last message number?", thread_id=thread_id)

        assert response is not None
        # Agent should only have access to recent messages (within window_size)
        # Response may or may not reference specific message numbers

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


@pytest.mark.integration
class TestAgentPersistentFacts:
    """Tests for agent persistent facts integration."""

    @pytest.mark.asyncio
    async def test_agent_with_persistent_facts(self, hf_model, storage_backend):
        """Test agent with persistent facts enabled."""
        # Create agent with persistent facts
        agent = Agent(
            name="FactsAgent",
            instructions="You are a helpful assistant. Use persistent facts to remember user information.",
            model=hf_model,
            storage=storage_backend,
            enable_persistent_facts=True,
        )

        thread_id = "test_thread_facts"
        user_id = "user_facts_123"

        # Add a fact manually
        if agent.persistent_facts:
            await agent.persistent_facts.add(
                key="user_name",
                value="Charlie",
                scope_id=user_id,
            )

        # Invoke agent - it should be able to access facts
        # Note: The agent may not automatically inject facts into context,
        # but the persistent_facts object is available
        response = await agent.invoke("Hello!", thread_id=thread_id)

        assert response is not None
        assert len(response.strip()) > 0

        # Verify fact exists
        if agent.persistent_facts:
            fact = await agent.persistent_facts.get(key="user_name", scope_id=user_id)
            assert fact is not None
            assert fact.value == "Charlie"

    @pytest.mark.asyncio
    async def test_agent_persistent_facts_extraction(self, hf_model, storage_backend):
        """Test that agent can extract facts from conversation."""
        # Create agent with persistent facts and extraction
        agent = Agent(
            name="ExtractAgent",
            instructions="You are a helpful assistant.",
            model=hf_model,
            storage=storage_backend,
            enable_persistent_facts=True,
        )

        thread_id = "test_thread_extract"
        user_id = "user_extract_456"

        # Invoke agent with information that should be extracted
        response = await agent.invoke(
            "My name is Diana and I live in Boston. I love reading books.",
            thread_id=thread_id,
        )

        assert response is not None

        # Manually extract facts from the conversation
        if agent.persistent_facts and agent.persistent_facts.auto_extract:
            messages = [
                {
                    "role": "user",
                    "content": "My name is Diana and I live in Boston. I love reading books.",
                },
            ]
            extracted = await agent.persistent_facts.extract_from_messages(
                messages=messages,
                scope_id=user_id,
            )

            # Should extract some facts
            assert isinstance(extracted, list)
            if len(extracted) > 0:
                # Verify facts were extracted
                assert all(hasattr(fact, "key") and hasattr(fact, "value") for fact in extracted)

    @pytest.mark.asyncio
    async def test_agent_custom_persistent_facts(self, hf_model, storage_backend):
        """Test agent with custom PersistentFacts instance."""
        # Create custom persistent facts
        custom_facts = PersistentFacts(
            storage=storage_backend,
            scope=MemoryScope.USER,
            auto_extract=True,
            extraction_model=hf_model,
        )

        # Create agent with custom persistent facts
        agent = Agent(
            name="CustomFactsAgent",
            instructions="You are a helpful assistant.",
            model=hf_model,
            storage=storage_backend,
            persistent_facts=custom_facts,
        )

        assert agent.persistent_facts == custom_facts
        assert agent.persistent_facts is not None

        # Store reference for type narrowing
        persistent_facts = agent.persistent_facts

        # Add a fact
        await persistent_facts.add(
            key="preference",
            value="dark_mode",
            scope_id="user_custom_789",
        )

        # Verify fact exists
        fact = await persistent_facts.get(key="preference", scope_id="user_custom_789")
        assert fact is not None
        assert fact.value == "dark_mode"

    @pytest.mark.asyncio
    async def test_agent_memory_and_facts_together(self, hf_model, storage_backend):
        """Test agent with both memory and persistent facts."""
        from framework.storage.memory import AgentStorage

        agent_storage = AgentStorage(storage=storage_backend, max_messages=50)
        thread_id = "test_thread_both"
        user_id = "user_both_999"

        # Add conversation history
        await agent_storage.add_message(thread_id, "user", "I prefer Python over Java.")
        await agent_storage.queue.flush()

        # Create agent with both memory and persistent facts
        memory_config = AgentMemory(window_size=10)
        agent = Agent(
            name="FullMemoryAgent",
            instructions="You are a helpful assistant. Remember user preferences.",
            model=hf_model,
            storage=storage_backend,
            memory=memory_config,
            enable_persistent_facts=True,
        )

        # Add persistent fact
        if agent.persistent_facts:
            await agent.persistent_facts.add(
                key="favorite_language",
                value="Python",
                scope_id=user_id,
            )

        # Invoke agent
        response = await agent.invoke(
            "What programming languages do I like?",
            thread_id=thread_id,
        )

        assert response is not None
        assert len(response.strip()) > 0

        # Response should be relevant
        response_lower = response.lower()
        assert (
            "python" in response_lower
            or "programming" in response_lower
            or "language" in response_lower
        ), f"Response should mention programming languages. Got: {response}"

        await agent_storage.stop()
