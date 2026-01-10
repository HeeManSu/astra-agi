"""
Integration tests for PersistentFacts with real LLM calls.

Tests fact extraction from conversations with real LLM.
"""

from framework.memory.persistent_facts import PersistentFacts
from framework.storage.models import MemoryScope
import pytest


@pytest.mark.integration
class TestPersistentFactsExtraction:
    """Tests for fact extraction with real LLM."""

    @pytest.mark.asyncio
    async def test_extract_from_messages_basic(self, hf_model, storage_backend):
        """Test extracting facts from simple conversation."""
        facts = PersistentFacts(
            storage=storage_backend,
            scope=MemoryScope.USER,
            auto_extract=True,
            extraction_model=hf_model,
        )

        messages = [
            {
                "role": "user",
                "content": "My name is Sarah and I live in San Francisco. I love hiking.",
            },
            {
                "role": "assistant",
                "content": "Nice to meet you, Sarah! San Francisco is a great city for hiking.",
            },
        ]

        extracted = await facts.extract_from_messages(
            messages=messages,
            scope=MemoryScope.USER,
            scope_id="user123",
        )

        # Should extract some facts
        assert isinstance(extracted, list)
        # May extract facts like name, location, interests
        if len(extracted) > 0:
            assert all(hasattr(fact, "key") and hasattr(fact, "value") for fact in extracted)

    @pytest.mark.asyncio
    async def test_extract_from_messages_auto_extract_disabled(self, hf_model, storage_backend):
        """Test that extraction returns empty when auto_extract is disabled."""
        facts = PersistentFacts(
            storage=storage_backend,
            scope=MemoryScope.USER,
            auto_extract=False,  # Disabled
            extraction_model=hf_model,
        )

        messages = [
            {"role": "user", "content": "My name is John"},
        ]

        extracted = await facts.extract_from_messages(messages=messages)

        assert extracted == []

    @pytest.mark.asyncio
    async def test_extract_from_messages_no_model(self, storage_backend):
        """Test that extraction returns empty when no model is provided."""
        facts = PersistentFacts(
            storage=storage_backend,
            scope=MemoryScope.USER,
            auto_extract=True,
            extraction_model=None,  # No model
        )

        messages = [
            {"role": "user", "content": "My name is John"},
        ]

        extracted = await facts.extract_from_messages(messages=messages)

        assert extracted == []

    @pytest.mark.asyncio
    async def test_extract_and_add_facts(self, hf_model, storage_backend):
        """Test extracting facts and adding them to storage."""
        facts = PersistentFacts(
            storage=storage_backend,
            scope=MemoryScope.USER,
            auto_extract=True,
            extraction_model=hf_model,
        )

        messages = [
            {
                "role": "user",
                "content": "I prefer dark mode UI and my favorite programming language is Python.",
            },
        ]

        extracted = await facts.extract_from_messages(
            messages=messages,
            scope_id="user456",
        )

        # Add extracted facts to storage
        for fact in extracted:
            await facts._fact_store.add(fact)

        # Verify facts were stored
        if len(extracted) > 0:
            all_facts = await facts.get_all(scope_id="user456")
            assert len(all_facts) >= len(extracted)


@pytest.mark.integration
class TestPersistentFactsCRUDIntegration:
    """Integration tests for CRUD operations with real storage."""

    @pytest.mark.asyncio
    async def test_add_and_get_fact(self, storage_backend):
        """Test adding and retrieving a fact."""
        facts = PersistentFacts(storage=storage_backend, scope=MemoryScope.USER)

        # Add fact
        fact = await facts.add(
            key="user_name",
            value="Alice",
            scope_id="user789",
        )

        assert fact.key == "user_name"
        assert fact.value == "Alice"
        assert fact.scope == MemoryScope.USER
        assert fact.scope_id == "user789"

        # Get fact
        retrieved = await facts.get(key="user_name", scope_id="user789")

        assert retrieved is not None
        assert retrieved.key == "user_name"
        assert retrieved.value == "Alice"

    @pytest.mark.asyncio
    async def test_update_fact(self, storage_backend):
        """Test updating an existing fact."""
        facts = PersistentFacts(storage=storage_backend, scope=MemoryScope.USER)

        # Add fact
        await facts.add(key="location", value="New York", scope_id="user999")

        # Update fact
        updated = await facts.update(
            key="location",
            value="San Francisco",
            scope_id="user999",
        )

        assert updated.value == "San Francisco"

        # Verify update
        retrieved = await facts.get(key="location", scope_id="user999")
        assert retrieved is not None
        assert retrieved.value == "San Francisco"

    @pytest.mark.asyncio
    async def test_update_fact_merge(self, storage_backend):
        """Test updating fact with merge=True."""
        facts = PersistentFacts(storage=storage_backend, scope=MemoryScope.USER)

        # Add fact with dict value
        await facts.add(
            key="preferences",
            value={"theme": "dark", "lang": "en"},
            scope_id="user888",
        )

        # Update with merge
        updated = await facts.update(
            key="preferences",
            value={"font": "arial"},
            scope_id="user888",
            merge=True,
        )

        assert isinstance(updated.value, dict)
        assert updated.value.get("theme") == "dark"  # Old value preserved
        assert updated.value.get("font") == "arial"  # New value added

    @pytest.mark.asyncio
    async def test_delete_fact(self, storage_backend):
        """Test deleting a fact."""
        facts = PersistentFacts(storage=storage_backend, scope=MemoryScope.USER)

        # Add fact
        await facts.add(key="temp_key", value="temp_value", scope_id="user777")

        # Delete fact
        deleted = await facts.delete(key="temp_key", scope_id="user777")
        assert deleted is True

        # Verify deletion
        retrieved = await facts.get(key="temp_key", scope_id="user777")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_all_facts(self, storage_backend):
        """Test getting all facts for a scope."""
        facts = PersistentFacts(storage=storage_backend, scope=MemoryScope.USER)

        # Add multiple facts
        await facts.add(key="fact1", value="value1", scope_id="user666")
        await facts.add(key="fact2", value="value2", scope_id="user666")
        await facts.add(key="fact3", value="value3", scope_id="user666")

        # Get all facts
        all_facts = await facts.get_all(scope_id="user666")

        assert len(all_facts) >= 3
        keys = {fact.key for fact in all_facts}
        assert "fact1" in keys
        assert "fact2" in keys
        assert "fact3" in keys

    @pytest.mark.asyncio
    async def test_search_facts(self, storage_backend):
        """Test searching facts by keyword."""
        facts = PersistentFacts(storage=storage_backend, scope=MemoryScope.USER)

        # Add facts
        await facts.add(key="user_name", value="Bob", scope_id="user555")
        await facts.add(key="user_location", value="Seattle", scope_id="user555")

        # Search for facts
        results = await facts.search(query="Bob", scope_id="user555")

        # Should find at least the user_name fact
        assert len(results) >= 1
        found_keys = {fact.key for fact in results}
        assert "user_name" in found_keys

    @pytest.mark.asyncio
    async def test_scope_isolation(self, storage_backend):
        """Test that facts are isolated by scope."""
        facts = PersistentFacts(storage=storage_backend, scope=MemoryScope.USER)

        # Add facts for different users
        await facts.add(key="name", value="User1", scope_id="user111")
        await facts.add(key="name", value="User2", scope_id="user222")

        # Get fact for user111
        fact1 = await facts.get(key="name", scope_id="user111")
        assert fact1 is not None
        assert fact1.value == "User1"

        # Get fact for user222
        fact2 = await facts.get(key="name", scope_id="user222")
        assert fact2 is not None
        assert fact2.value == "User2"

        # Facts should be different
        assert fact1.value != fact2.value

    @pytest.mark.asyncio
    async def test_global_scope(self, storage_backend):
        """Test facts with GLOBAL scope."""
        facts = PersistentFacts(storage=storage_backend, scope=MemoryScope.GLOBAL)

        # Add global fact (no scope_id needed)
        fact = await facts.add(key="system_version", value="1.0.0", scope=MemoryScope.GLOBAL)

        assert fact.scope == MemoryScope.GLOBAL
        assert fact.scope_id is None

        # Get global fact
        retrieved = await facts.get(key="system_version", scope=MemoryScope.GLOBAL)
        assert retrieved is not None
        assert retrieved.value == "1.0.0"
