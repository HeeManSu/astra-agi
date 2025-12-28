"""Persistent Facts - Long-term declarative memory for facts and preferences.

Provides CRUD operations, memory scoping, and fact extraction.
Built on top of existing StorageBackend - no new dependencies.
"""

import json
from typing import Any
from uuid import uuid4

from framework.models import Model
from framework.storage.base import StorageBackend
from framework.storage.models import Fact, MemoryScope
from framework.storage.stores.fact import FactStore


class PersistentFacts:
    """
    Long-term declarative memory for facts and preferences.

    Features:
    - CRUD operations (add/get/update/delete)
    - Memory scoping (USER/SESSION/AGENT/GLOBAL)
    - Automatic fact extraction from conversations (optional)
    - Fact search by keyword/metadata
    - Built on existing StorageBackend

    Example:
        persistent_facts = PersistentFacts(
            storage=storage,
            scope=MemoryScope.USER,
            auto_extract=True,
        )
    """

    def __init__(
        self,
        storage: StorageBackend,
        scope: MemoryScope = MemoryScope.USER,
        auto_extract: bool = True,
        extraction_model: Model | None = None,
        extraction_template: str | None = None,
    ):
        """
        Initialize PersistentFacts.

        Args:
            storage: Storage backend instance (uses existing Agent.storage)
            scope: Default memory scope (default: USER)
                - USER: Facts scoped to user_id (most common)
                - SESSION: Facts scoped to session/thread_id (temporary)
                - AGENT: Facts scoped to agent_id (shared across users)
                - GLOBAL: Facts with no scope_id (system-wide)
            auto_extract: Enable automatic fact extraction from conversations
            extraction_model: Model for extraction (uses agent's model if None)
            extraction_template: Template for structured extraction

        Note:
            The default scope is USER. When you call add/get/update/delete without
            specifying scope, it uses USER scope. To use other scopes, pass scope
            parameter explicitly or set scope_id accordingly.
        """
        self.storage = storage
        self.scope = scope
        self.auto_extract = auto_extract
        self.extraction_model = extraction_model
        self.extraction_template = extraction_template or self._default_extraction_template()
        self._fact_store = FactStore(storage)

    @staticmethod
    def _default_extraction_template() -> str:
        """Default extraction template for fact extraction."""
        return """Extract structured facts from the conversation using a key-value format.

## Fact Extraction Guidelines

Extract facts that capture meaningful information about the user that would be useful in future conversations:

**Extract:**
- Personal information: name, age, location, occupation, contact details
- Preferences: UI themes, languages, meeting times, communication styles
- Interests and hobbies: activities, topics, skills
- Goals and plans: current objectives, future plans, aspirations
- Context: current situation, challenges, constraints, relationships
- Opinions: likes, dislikes, values, beliefs

**Do NOT extract:**
- Temporary states ("I'm tired right now")
- One-time events without significance ("I had coffee this morning")
- Information already mentioned in previous facts
- Assumptions or inferences not directly stated

## Fact Format

Each fact must be a key-value pair where:
- **Key**: Descriptive identifier using snake_case (e.g., `user_name`, `preferences_ui_theme`, `interests_hiking`)
- **Value**: The actual fact content (string, number, array, or object)

## Examples

Input: "My name is Sarah and I live in San Francisco. I love hiking and prefer dark mode UI."

Output:
{
  "user_name": "Sarah",
  "location": "San Francisco",
  "interests": ["hiking"],
  "preferences_ui_theme": "dark"
}

Input: "I'm learning Python and my goal is to build a web app by next month."

Output:
{
  "skills_learning": ["Python"],
  "goals": "Build a web app by next month"
}

## Output Requirements

- Return ONLY valid JSON (no markdown, no code blocks)
- Use descriptive keys that indicate the category (e.g., `preferences_*`, `interests_*`, `goals_*`)
- Group related facts logically (e.g., all preferences together)
- Use arrays for multiple related items (e.g., `interests: ["hiking", "reading"]`)
- Keep values concise but informative
- Only extract facts explicitly stated or clearly implied"""

    async def add(
        self,
        key: str,
        value: Any,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Fact:
        """
        Add a new fact.

        Args:
            key: Fact key (e.g., "user_preferences")
            value: Fact value (JSON-serializable)
            scope: Memory scope (defaults to instance scope, which is USER by default)
                - USER: Requires scope_id (user_id) - most common
                - SESSION: Requires scope_id (session_id or thread_id) - temporary
                - AGENT: Requires scope_id (agent_id) - shared across users
                - GLOBAL: scope_id should be None - system-wide
            scope_id: Scope identifier
                - For USER: user_id (e.g., "[email protected]")
                - For SESSION: session_id or thread_id
                - For AGENT: agent_id
                - For GLOBAL: None (ignored)
            tags: Optional tags for categorization
            metadata: Optional additional metadata

        Returns:
            Created Fact object

        Examples:
            # USER scope (default - most common)
            # Facts belong to a specific user, persist across all sessions
            await facts.add("preferences", {"theme": "dark"}, scope_id="[email protected]")
            # This fact is only accessible when scope_id="[email protected]"

            # SESSION scope (temporary)
            # Facts belong to a session/thread, cleared when session ends
            await facts.add(
                "current_task",
                "writing report",
                scope=MemoryScope.SESSION,
                scope_id="thread_123"
            )
            # This fact is only accessible for thread_123

            # AGENT scope (shared across users)
            # Facts belong to an agent, shared by all users of that agent
            await facts.add(
                "last_maintenance",
                "2024-01-15",
                scope=MemoryScope.AGENT,
                scope_id="agent_456"
            )
            # All users of agent_456 can access this fact

            # GLOBAL scope (system-wide)
            # Facts are shared by everyone, no scope_id needed
            await facts.add("system_version", "1.0.0", scope=MemoryScope.GLOBAL)
            # Everyone can access this fact, scope_id is ignored
        """
        fact = Fact(
            id=f"fact-{uuid4().hex[:12]}",
            key=key,
            value=value,
            scope=scope or self.scope,
            scope_id=scope_id,
            tags=tags or [],
            metadata=metadata or {},
        )
        return await self._fact_store.add(fact)

    async def get(
        self,
        key: str,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
    ) -> Fact | None:
        """
        Retrieve a fact by key.

        Args:
            key: Fact key
            scope: Memory scope (defaults to instance scope, which is USER by default)
            scope_id: Scope identifier (required for USER/SESSION/AGENT, None for GLOBAL)

        Returns:
            Fact if found, None otherwise

        Examples:
            # Get USER fact (default scope)
            fact = await facts.get("preferences", scope_id="[email protected]")
            # Returns fact if it exists for this user

            # Get SESSION fact
            fact = await facts.get(
                "current_task",
                scope=MemoryScope.SESSION,
                scope_id="thread_123"
            )

            # Get GLOBAL fact (scope_id not needed)
            fact = await facts.get("system_version", scope=MemoryScope.GLOBAL)
        """
        return await self._fact_store.get(
            key=key,
            scope=scope or self.scope,
            scope_id=scope_id,
        )

    async def update(
        self,
        key: str,
        value: Any,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
        merge: bool = False,
    ) -> Fact:
        """
        Update an existing fact.

        Args:
            key: Fact key
            value: New value
            scope: Memory scope (uses instance default if None)
            scope_id: Scope identifier
            merge: If True, merge with existing value (for dict/list). If False, overwrite.

        Returns:
            Updated Fact object

        Raises:
            ValueError: If fact not found
        """
        fact = await self.get(key=key, scope=scope, scope_id=scope_id)
        if not fact:
            raise ValueError(
                f"Fact not found: key={key}, scope={scope or self.scope}, scope_id={scope_id}"
            )

        # Handle merge logic for preference changes
        if merge:
            if isinstance(fact.value, dict) and isinstance(value, dict):
                # Merge dictionaries - new values override old ones
                merged_value = {**fact.value, **value}
                fact.value = merged_value
            elif isinstance(fact.value, list) and isinstance(value, list):
                # Merge lists - combine unique items
                merged_value = list(set(fact.value + value))
                fact.value = merged_value
            else:
                # For non-dict/list, store both old and new
                fact.value = {"previous": fact.value, "current": value}
        else:
            # Simple overwrite
            fact.value = value

        return await self._fact_store.update(fact)

    async def delete(
        self,
        key: str,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
    ) -> bool:
        """
        Delete a fact (soft delete).

        Args:
            key: Fact key
            scope: Memory scope (uses instance default if None)
            scope_id: Scope identifier

        Returns:
            True if deleted, False if not found
        """
        return await self._fact_store.delete(
            key=key,
            scope=scope or self.scope,
            scope_id=scope_id,
        )

    async def get_all(
        self,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
        limit: int | None = None,
        order_by: str = "created_at",
        order_direction: int = -1,
    ) -> list[Fact]:
        """
        Get all facts for a scope.

        Args:
            scope: Memory scope (uses instance default if None)
            scope_id: Scope identifier
            limit: Maximum number of facts to return (None = all)
            order_by: Field to sort by (default: "created_at")
            order_direction: Sort direction (1 = ascending, -1 = descending)

        Returns:
            List of Fact objects
        """
        return await self._fact_store.get_all(
            scope=scope or self.scope,
            scope_id=scope_id,
            limit=limit,
            order_by=order_by,
            order_direction=order_direction,
        )

    async def search(
        self,
        query: str,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
        limit: int = 10,
    ) -> list[Fact]:
        """
        Search facts by keyword.

        Args:
            query: Search query string
            scope: Memory scope (uses instance default if None)
            scope_id: Scope identifier
            limit: Maximum number of results

        Returns:
            List of matching Fact objects
        """
        return await self._fact_store.search(
            query=query,
            scope=scope or self.scope,
            scope_id=scope_id,
            limit=limit,
        )

    async def extract_from_messages(
        self,
        messages: list[dict[str, Any]],
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
        model: Model | None = None,
    ) -> list[Fact]:
        """
        Extract facts from conversation messages using LLM.

        Args:
            messages: List of message dicts
            scope: Memory scope (uses instance default if None)
            scope_id: Scope identifier
            model: Model to use for extraction (uses instance model if None)

        Returns:
            List of extracted Fact objects
        """
        if not self.auto_extract:
            return []

        extraction_model = model or self.extraction_model
        if not extraction_model:
            # Cannot extract without a model
            return []

        # Format messages for extraction
        conversation_text = "\n".join(
            [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in messages]
        )

        # Create extraction prompt
        prompt = f"{self.extraction_template}\n\nConversation:\n{conversation_text}\n\nExtract facts as JSON:"

        try:
            # Invoke model for extraction
            response = await extraction_model.invoke([{"role": "user", "content": prompt}])
            extracted_data = json.loads(response.content)

            # Convert extracted data to facts
            facts = []
            for key, value in extracted_data.items():
                fact = Fact(
                    id=f"fact-{uuid4().hex[:12]}",
                    key=key,
                    value=value,
                    scope=scope or self.scope,
                    scope_id=scope_id,
                    tags=["extracted"],
                )
                facts.append(fact)

            return facts
        except Exception:
            return []

    async def clear_all(
        self,
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
    ) -> int:
        """
        Clear all facts for a scope (soft delete).

        Args:
            scope: Memory scope (uses instance default if None)
            scope_id: Scope identifier

        Returns:
            Number of facts deleted
        """
        return await self._fact_store.clear_all(
            scope=scope or self.scope,
            scope_id=scope_id,
        )

    async def bulk_update(
        self,
        updates: list[dict[str, Any]],
        scope: MemoryScope | None = None,
        scope_id: str | None = None,
        merge: bool = False,
    ) -> list[Fact]:
        """
        Bulk update multiple facts.

        Args:
            updates: List of dicts with 'key' and 'value' fields
            scope: Memory scope (uses instance default if None)
            scope_id: Scope identifier
            merge: If True, merge with existing values

        Returns:
            List of updated Fact objects

        Example:
            await facts.bulk_update([
                {"key": "preferences", "value": {"theme": "dark"}},
                {"key": "location", "value": "NYC"},
            ], scope_id="user123")
        """
        updated_facts = []
        for update in updates:
            key = update.get("key")
            value = update.get("value")
            if not key:
                continue

            try:
                fact = await self.update(
                    key=key,
                    value=value,
                    scope=scope,
                    scope_id=scope_id,
                    merge=merge,
                )
                updated_facts.append(fact)
            except ValueError:
                # Fact doesn't exist, create it
                fact = await self.add(
                    key=key,
                    value=value,
                    scope=scope,
                    scope_id=scope_id,
                )
                updated_facts.append(fact)

        return updated_facts
