"""
Unit tests for PersistentFacts (CRUD operations without LLM extraction).

Tests fact management, scoping, and CRUD logic without LLM calls.
"""

from framework.memory.persistent_facts import PersistentFacts
from framework.storage.models import MemoryScope
import pytest


@pytest.mark.unit
class TestPersistentFactsInitialization:
    """Tests for PersistentFacts initialization."""

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage backend."""
        from unittest.mock import MagicMock

        return MagicMock()

    def test_default_initialization(self, mock_storage):
        """Test default initialization values."""
        facts = PersistentFacts(storage=mock_storage)
        assert facts.storage == mock_storage
        assert facts.scope == MemoryScope.USER
        assert facts.auto_extract is True
        assert facts.extraction_model is None
        assert len(facts.extraction_template) > 0

    def test_custom_scope(self, mock_storage):
        """Test initialization with custom scope."""
        facts = PersistentFacts(storage=mock_storage, scope=MemoryScope.SESSION)
        assert facts.scope == MemoryScope.SESSION

    def test_auto_extract_disabled(self, mock_storage):
        """Test initialization with auto_extract disabled."""
        facts = PersistentFacts(storage=mock_storage, auto_extract=False)
        assert facts.auto_extract is False

    def test_extraction_template_default(self, mock_storage):
        """Test that default extraction template is set."""
        facts = PersistentFacts(storage=mock_storage)
        template = facts.extraction_template
        assert len(template) > 0
        assert "Extract" in template or "extract" in template.lower()
        assert "JSON" in template or "json" in template.lower()


@pytest.mark.unit
class TestPersistentFactsCRUD:
    """Tests for CRUD operations (without LLM)."""

    @pytest.fixture
    def mock_fact_store(self):
        """Create a mock FactStore."""
        from unittest.mock import AsyncMock, MagicMock

        store = MagicMock()
        store.add = AsyncMock()
        store.get = AsyncMock()
        store.update = AsyncMock()
        store.delete = AsyncMock()
        store.get_all = AsyncMock(return_value=[])
        store.search = AsyncMock(return_value=[])
        store.clear_all = AsyncMock(return_value=0)
        return store

    @pytest.fixture
    def persistent_facts(self, mock_storage, mock_fact_store):
        """Create PersistentFacts instance with mocked store."""
        facts = PersistentFacts(storage=mock_storage, scope=MemoryScope.USER)
        facts._fact_store = mock_fact_store
        return facts

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage backend."""
        from unittest.mock import MagicMock

        return MagicMock()

    @pytest.mark.asyncio
    async def test_add_fact_user_scope(self, persistent_facts, mock_fact_store):
        """Test adding a fact with USER scope."""
        from framework.storage.models import Fact

        fact_data = Fact(
            id="fact-123",
            key="user_name",
            value="John",
            scope=MemoryScope.USER,
            scope_id="user123",
        )
        mock_fact_store.add.return_value = fact_data

        result = await persistent_facts.add(
            key="user_name",
            value="John",
            scope_id="user123",
        )

        assert result.key == "user_name"
        assert result.value == "John"
        assert result.scope == MemoryScope.USER
        assert result.scope_id == "user123"
        mock_fact_store.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_fact_global_scope(self, persistent_facts, mock_fact_store):
        """Test adding a fact with GLOBAL scope."""
        from framework.storage.models import Fact

        fact_data = Fact(
            id="fact-456",
            key="system_version",
            value="1.0.0",
            scope=MemoryScope.GLOBAL,
            scope_id=None,
        )
        mock_fact_store.add.return_value = fact_data

        result = await persistent_facts.add(
            key="system_version",
            value="1.0.0",
            scope=MemoryScope.GLOBAL,
        )

        assert result.scope == MemoryScope.GLOBAL
        assert result.scope_id is None
        mock_fact_store.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_fact_exists(self, persistent_facts, mock_fact_store):
        """Test getting an existing fact."""
        from framework.storage.models import Fact

        fact_data = Fact(
            id="fact-123",
            key="user_name",
            value="John",
            scope=MemoryScope.USER,
            scope_id="user123",
        )
        mock_fact_store.get.return_value = fact_data

        result = await persistent_facts.get(key="user_name", scope_id="user123")

        assert result is not None
        assert result.key == "user_name"
        assert result.value == "John"
        mock_fact_store.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_fact_not_found(self, persistent_facts, mock_fact_store):
        """Test getting a non-existent fact."""
        mock_fact_store.get.return_value = None

        result = await persistent_facts.get(key="nonexistent", scope_id="user123")

        assert result is None
        mock_fact_store.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_fact_exists(self, persistent_facts, mock_fact_store):
        """Test updating an existing fact."""
        from framework.storage.models import Fact

        existing_fact = Fact(
            id="fact-123",
            key="user_name",
            value="John",
            scope=MemoryScope.USER,
            scope_id="user123",
        )
        updated_fact = Fact(
            id="fact-123",
            key="user_name",
            value="Jane",
            scope=MemoryScope.USER,
            scope_id="user123",
        )
        mock_fact_store.get.return_value = existing_fact
        mock_fact_store.update.return_value = updated_fact

        result = await persistent_facts.update(
            key="user_name",
            value="Jane",
            scope_id="user123",
        )

        assert result.value == "Jane"
        mock_fact_store.get.assert_called_once()
        mock_fact_store.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_fact_not_found(self, persistent_facts, mock_fact_store):
        """Test updating a non-existent fact raises ValueError."""
        mock_fact_store.get.return_value = None

        with pytest.raises(ValueError, match="Fact not found"):
            await persistent_facts.update(
                key="nonexistent",
                value="value",
                scope_id="user123",
            )

    @pytest.mark.asyncio
    async def test_update_fact_merge_dict(self, persistent_facts, mock_fact_store):
        """Test updating fact with merge=True for dict."""
        from framework.storage.models import Fact

        existing_fact = Fact(
            id="fact-123",
            key="preferences",
            value={"theme": "dark", "lang": "en"},
            scope=MemoryScope.USER,
            scope_id="user123",
        )
        updated_fact = Fact(
            id="fact-123",
            key="preferences",
            value={"theme": "light", "lang": "en", "font": "arial"},
            scope=MemoryScope.USER,
            scope_id="user123",
        )
        mock_fact_store.get.return_value = existing_fact
        mock_fact_store.update.return_value = updated_fact

        result = await persistent_facts.update(
            key="preferences",
            value={"theme": "light", "font": "arial"},
            scope_id="user123",
            merge=True,
        )

        # Should merge dictionaries
        assert isinstance(result.value, dict)
        mock_fact_store.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_fact_exists(self, persistent_facts, mock_fact_store):
        """Test deleting an existing fact."""
        mock_fact_store.delete.return_value = True

        result = await persistent_facts.delete(key="user_name", scope_id="user123")

        assert result is True
        mock_fact_store.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_fact_not_found(self, persistent_facts, mock_fact_store):
        """Test deleting a non-existent fact."""
        mock_fact_store.delete.return_value = False

        result = await persistent_facts.delete(key="nonexistent", scope_id="user123")

        assert result is False
        mock_fact_store.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_facts(self, persistent_facts, mock_fact_store):
        """Test getting all facts for a scope."""
        from framework.storage.models import Fact

        facts = [
            Fact(
                id=f"fact-{i}",
                key=f"key_{i}",
                value=f"value_{i}",
                scope=MemoryScope.USER,
                scope_id="user123",
            )
            for i in range(3)
        ]
        mock_fact_store.get_all.return_value = facts

        result = await persistent_facts.get_all(scope_id="user123")

        assert len(result) == 3
        mock_fact_store.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_facts(self, persistent_facts, mock_fact_store):
        """Test searching facts by keyword."""
        from framework.storage.models import Fact

        facts = [
            Fact(
                id="fact-1",
                key="user_name",
                value="John",
                scope=MemoryScope.USER,
                scope_id="user123",
            )
        ]
        mock_fact_store.search.return_value = facts

        result = await persistent_facts.search(query="John", scope_id="user123")

        assert len(result) == 1
        assert result[0].key == "user_name"
        mock_fact_store.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_all_facts(self, persistent_facts, mock_fact_store):
        """Test clearing all facts for a scope."""
        mock_fact_store.clear_all.return_value = 5

        result = await persistent_facts.clear_all(scope_id="user123")

        assert result == 5
        mock_fact_store.clear_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update_facts(self, persistent_facts, mock_fact_store):
        """Test bulk updating multiple facts."""
        from framework.storage.models import Fact

        # Mock get to return existing facts
        existing_fact = Fact(
            id="fact-1",
            key="key1",
            value="old_value",
            scope=MemoryScope.USER,
            scope_id="user123",
        )
        mock_fact_store.get.return_value = existing_fact
        mock_fact_store.update.return_value = existing_fact

        updates = [
            {"key": "key1", "value": "new_value1"},
            {"key": "key2", "value": "new_value2"},
        ]

        # For key2, get returns None, so it should call add
        def get_side_effect(key, scope, scope_id):
            if key == "key1":
                return existing_fact
            return None

        mock_fact_store.get.side_effect = get_side_effect
        mock_fact_store.add.return_value = Fact(
            id="fact-2",
            key="key2",
            value="new_value2",
            scope=MemoryScope.USER,
            scope_id="user123",
        )

        result = await persistent_facts.bulk_update(updates, scope_id="user123")

        assert len(result) == 2
        assert mock_fact_store.update.call_count == 1  # key1 updated
        assert mock_fact_store.add.call_count == 1  # key2 added


@pytest.mark.unit
class TestPersistentFactsScoping:
    """Tests for memory scoping logic."""

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage backend."""
        from unittest.mock import MagicMock

        return MagicMock()

    @pytest.mark.asyncio
    async def test_default_scope_used(self, mock_storage):
        """Test that default scope is used when not specified."""
        facts = PersistentFacts(storage=mock_storage, scope=MemoryScope.SESSION)

        # Mock the fact store
        from unittest.mock import AsyncMock, MagicMock

        mock_fact_store = MagicMock()
        mock_fact_store.add = AsyncMock()
        facts._fact_store = mock_fact_store

        from framework.storage.models import Fact

        fact_data = Fact(
            id="fact-123",
            key="test_key",
            value="test_value",
            scope=MemoryScope.SESSION,
            scope_id="session123",
        )
        mock_fact_store.add.return_value = fact_data

        result = await facts.add(key="test_key", value="test_value", scope_id="session123")

        # Should use SESSION scope (the default)
        assert result.scope == MemoryScope.SESSION

    @pytest.mark.asyncio
    async def test_scope_override(self, mock_storage):
        """Test that scope can be overridden."""
        facts = PersistentFacts(storage=mock_storage, scope=MemoryScope.USER)

        from unittest.mock import AsyncMock, MagicMock

        mock_fact_store = MagicMock()
        mock_fact_store.add = AsyncMock()
        facts._fact_store = mock_fact_store

        from framework.storage.models import Fact

        fact_data = Fact(
            id="fact-123",
            key="test_key",
            value="test_value",
            scope=MemoryScope.AGENT,
            scope_id="agent123",
        )
        mock_fact_store.add.return_value = fact_data

        result = await facts.add(
            key="test_key",
            value="test_value",
            scope=MemoryScope.AGENT,
            scope_id="agent123",
        )

        # Should use AGENT scope (overridden)
        assert result.scope == MemoryScope.AGENT
