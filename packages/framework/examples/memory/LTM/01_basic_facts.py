"""
Example 1: Basic Persistent Facts Operations

Tests basic CRUD operations for persistent facts:
1. Add facts
2. Get facts
3. Update facts
4. Delete facts
5. Get all facts

This example does NOT require an LLM model (auto_extract=False).
Requires: MongoDB running locally on port 27017.
"""

import asyncio

from framework.memory import MemoryScope, PersistentFacts
from framework.storage.databases.mongodb import MongoDBStorage


async def main():
    """Test basic fact operations."""
    print("=== Basic Persistent Facts Operations ===\n")

    # Setup MongoDB storage
    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_ltm_test")
    await storage.connect()

    # Initialize PersistentFacts (no model needed when auto_extract=False)
    facts = PersistentFacts(
        storage=storage,
        scope=MemoryScope.USER,
        auto_extract=False,
    )

    user_id = "user_test_001"
    user_2_id = "user_test_002"

    # Clean up from previous runs
    await facts.clear_all(scope_id=user_id)
    await facts.clear_all(scope_id=user_2_id)

    print("1. Adding facts...")
    # Add some facts
    fact1 = await facts.add("user_name", "John Doe", scope_id=user_id)
    print(f"   Added: {fact1.key} = {fact1.value}")

    fact2 = await facts.add("preferences", {"theme": "dark", "language": "en"}, scope_id=user_id)
    print(f"   Added: {fact2.key} = {fact2.value}")

    fact3 = await facts.add(
        "location", "San Francisco", scope_id=user_id, tags=["personal", "location"]
    )
    print(f"   Added: {fact3.key} = {fact3.value}")

    print("\n2. Getting facts...")
    # Get a fact
    retrieved = await facts.get("user_name", scope_id=user_id)
    print(f"   Retrieved: {retrieved.key} = {retrieved.value}" if retrieved else "   Not found")

    print("\n3. Getting all facts...")
    # Get all facts
    all_facts = await facts.get_all(scope_id=user_id)
    print(f"   Total facts: {len(all_facts)}")
    for fact in all_facts:
        print(f"   - {fact.key}: {fact.value}")

    print("\n3a. Getting facts with limit and ordering...")
    # Get most recent 2 facts
    recent = await facts.get_all(
        scope_id=user_id, limit=2, order_by="created_at", order_direction=-1
    )
    print(f"   Most recent {len(recent)} facts:")
    for fact in recent:
        print(f"   - {fact.key}: {fact.value}")

    print("\n4. Updating a fact (overwrite)...")
    # Update a fact - overwrite mode
    updated = await facts.update(
        "preferences", {"theme": "light", "language": "en"}, scope_id=user_id, merge=False
    )
    print(f"   Updated (overwrite): {updated.key} = {updated.value}")

    print("\n4a. Updating a fact (merge)...")
    # First set preferences with more fields
    await facts.update(
        "preferences", {"theme": "dark", "language": "en", "notifications": True}, scope_id=user_id
    )
    # Now merge just the theme change
    merged = await facts.update("preferences", {"theme": "light"}, scope_id=user_id, merge=True)
    print(f"   Updated (merge): {merged.key} = {merged.value}")
    print(f"   ✅ Theme updated, notifications preserved: {merged.value.get('notifications')}")

    print("\n5. Searching facts...")
    # Search facts
    results = await facts.search("name", scope_id=user_id)
    print(f"   Search 'name': Found {len(results)} facts")
    for fact in results:
        print(f"   - {fact.key}: {fact.value}")

    print("\n6. Deleting a fact...")
    # Delete a fact
    deleted = await facts.delete("location", scope_id=user_id)
    print(f"   Deleted location fact: {deleted}")

    # Verify deletion
    remaining = await facts.get_all(scope_id=user_id)
    print(f"   Remaining facts: {len(remaining)}")

    print("\n7. Testing bulk operations...")
    # Bulk update multiple facts
    bulk_updates = [
        {"key": "user_name", "value": "John Doe Updated"},
        {"key": "preferences", "value": {"theme": "auto", "language": "en"}},
    ]
    bulk_updated = await facts.bulk_update(bulk_updates, scope_id=user_id, merge=False)
    print(f"   ✅ Bulk updated {len(bulk_updated)} facts")

    # Verify bulk update
    updated_name = await facts.get("user_name", scope_id=user_id)
    print(
        f"   ✅ Verified: {updated_name.key} = {updated_name.value}"
    ) if updated_name else "   Not found"

    print("\n8. Testing clear_all...")
    # Add some facts for another user
    await facts.add("temp_fact_1", "value1", scope_id=user_2_id)
    await facts.add("temp_fact_2", "value2", scope_id=user_2_id)

    # Clear all facts for user_2
    cleared_count = await facts.clear_all(scope_id=user_2_id)
    print(f"   ✅ Cleared {cleared_count} facts for user_2")

    # Verify user_1 facts still exist
    user_1_facts = await facts.get_all(scope_id=user_id)
    user_2_facts = await facts.get_all(scope_id=user_2_id)
    assert len(user_1_facts) > 0
    assert len(user_2_facts) == 0
    print(f"   ✅ User 1 still has {len(user_1_facts)} facts, User 2 has {len(user_2_facts)} facts")

    await storage.disconnect()

    print("\n✅ Basic operations test completed!")


if __name__ == "__main__":
    asyncio.run(main())
