"""
Example 5: Comprehensive LTM Test

Tests all LTM features comprehensively with realistic scenarios:
1. CRUD operations with real-world data
2. Fact extraction with actual conversations
3. Memory scoping across different users
4. Search functionality
5. Bulk operations
6. Update logic (merge vs overwrite)
7. Retrieval options (limit, ordering)
8. Edge cases and error handling

Uses local HuggingFace model - no API key required.
"""

import asyncio

# MongoDB - no file cleanup needed
from framework.memory import MemoryScope, PersistentFacts
from framework.models.huggingface import HuggingFaceLocal
from framework.storage.databases.mongodb import MongoDBStorage


async def main():
    """Comprehensive LTM test with realistic scenarios."""
    print("=== Comprehensive LTM Test ===\n")

    # Setup storage
    # MongoDB connection

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_ltm_test")
    await storage.connect()

    print("Loading local model (first time may take a few minutes to download)...")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct")
    facts = PersistentFacts(storage=storage, scope=MemoryScope.USER, extraction_model=model)

    user_id = "user_alice"

    # Clean up from previous runs
    await facts.clear_all(scope_id=user_id)

    print("\n1. Real-world scenario: User profile setup...")
    # Simulate a real user setting up their profile
    await facts.add("user_name", "Alice Johnson", scope_id=user_id)
    await facts.add("user_email", "[email protected]", scope_id=user_id)
    await facts.add(
        "preferences", {"theme": "dark", "language": "en", "notifications": True}, scope_id=user_id
    )
    await facts.add("interests", ["reading", "hiking", "photography"], scope_id=user_id)
    await facts.add(
        "location", "San Francisco, CA", scope_id=user_id, tags=["personal", "location"]
    )
    print("   ✅ Created user profile with realistic data")

    print("\n2. Testing fact retrieval with real data...")
    name = await facts.get("user_name", scope_id=user_id)
    preferences = await facts.get("preferences", scope_id=user_id)
    assert name is not None
    assert preferences is not None
    assert name.value == "Alice Johnson"
    assert preferences.value["theme"] == "dark"
    print(f"   ✅ Retrieved: Name={name.value}, Theme={preferences.value['theme']}")

    print("\n3. Real-world scenario: User updates preferences (merge)...")
    # User changes theme but keeps other preferences
    await facts.update("preferences", {"theme": "light"}, scope_id=user_id, merge=True)
    updated_preferences = await facts.get("preferences", scope_id=user_id)
    assert updated_preferences is not None
    assert updated_preferences.value["theme"] == "light"
    assert updated_preferences.value["language"] == "en"  # Should be preserved
    assert updated_preferences.value["notifications"] is True  # Should be preserved
    print(f"   ✅ Merged preferences: {updated_preferences.value}")

    print("\n4. Real-world scenario: User updates preferences (overwrite)...")
    # User completely changes preferences
    await facts.update(
        "preferences", {"theme": "auto", "language": "es"}, scope_id=user_id, merge=False
    )
    overwritten_preferences = await facts.get("preferences", scope_id=user_id)
    assert overwritten_preferences is not None
    assert overwritten_preferences.value["theme"] == "auto"
    assert overwritten_preferences.value["language"] == "es"
    assert "notifications" not in overwritten_preferences.value  # Should be removed
    print(f"   ✅ Overwritten preferences: {overwritten_preferences.value}")

    print("\n5. Real-world scenario: Fact extraction from conversation...")
    # Simulate a real conversation
    messages = [
        {
            "role": "user",
            "content": "Hi! I'm Alice. I work as a software engineer at TechCorp. "
            "I love reading science fiction books and hiking on weekends. "
            "My favorite programming language is Python.",
        },
        {
            "role": "assistant",
            "content": "Nice to meet you, Alice! What kind of projects do you work on?",
        },
        {
            "role": "user",
            "content": "I work on AI systems and machine learning models. "
            "I also enjoy contributing to open source projects.",
        },
    ]

    extracted = await facts.extract_from_messages(messages, scope_id=user_id, model=model)
    print(f"   ✅ Extracted {len(extracted)} facts from conversation")

    # Store extracted facts intelligently
    for fact in extracted:
        existing = await facts.get(fact.key, scope_id=user_id)
        if existing:
            # Merge if it's a dict/list, overwrite if it's a string
            # But preserve user_name if existing is more complete
            if (
                fact.key == "user_name"
                and isinstance(existing.value, str)
                and isinstance(fact.value, str)
            ):
                # Keep the longer/more complete name
                if len(existing.value) > len(fact.value):
                    continue  # Skip update, keep existing
            if isinstance(existing.value, dict) and isinstance(fact.value, dict):
                await facts.update(fact.key, fact.value, scope_id=user_id, merge=True)
            else:
                await facts.update(fact.key, fact.value, scope_id=user_id, merge=False)
        else:
            await facts.add(fact.key, fact.value, scope_id=user_id, tags=fact.tags)

    print("\n6. Testing retrieval options (limit and ordering)...")
    # Get most recent 3 facts
    recent_facts = await facts.get_all(
        scope_id=user_id, limit=3, order_by="created_at", order_direction=-1
    )
    print(f"   ✅ Retrieved {len(recent_facts)} most recent facts")
    for fact in recent_facts:
        print(f"      - {fact.key}: {fact.value}")

    # Get oldest 2 facts
    oldest_facts = await facts.get_all(
        scope_id=user_id, limit=2, order_by="created_at", order_direction=1
    )
    print(f"   ✅ Retrieved {len(oldest_facts)} oldest facts")

    print("\n7. Real-world scenario: Bulk update user preferences...")
    # User updates multiple preferences at once
    bulk_updates = [
        {"key": "preferences", "value": {"theme": "dark", "language": "en", "timezone": "PST"}},
        {"key": "interests", "value": ["reading", "hiking", "photography", "coding"]},
    ]
    updated = await facts.bulk_update(bulk_updates, scope_id=user_id, merge=True)
    print(f"   ✅ Bulk updated {len(updated)} facts")

    # Verify bulk update
    bulk_preferences = await facts.get("preferences", scope_id=user_id)
    bulk_interests = await facts.get("interests", scope_id=user_id)
    assert bulk_preferences is not None
    assert bulk_interests is not None
    assert bulk_preferences.value["theme"] == "dark"
    assert "coding" in bulk_interests.value
    print(f"   ✅ Verified: Theme={bulk_preferences.value['theme']}, Interests include coding")

    print("\n8. Real-world scenario: Search functionality...")
    # Search for facts related to work
    work_results = await facts.search("work", scope_id=user_id)
    print(f"   ✅ Search 'work' found {len(work_results)} facts")
    for fact in work_results:
        print(f"      - {fact.key}: {fact.value}")

    # Search for facts related to interests
    interest_results = await facts.search("interest", scope_id=user_id)
    print(f"   ✅ Search 'interest' found {len(interest_results)} facts")

    print("\n9. Real-world scenario: Multi-user isolation...")
    user_bob_id = "user_bob"
    # Clean up from previous runs
    await facts.clear_all(scope_id=user_bob_id)
    await facts.add("user_name", "Bob Smith", scope_id=user_bob_id)
    await facts.add("preferences", {"theme": "light", "language": "fr"}, scope_id=user_bob_id)

    alice_facts = await facts.get_all(scope_id=user_id)
    bob_facts = await facts.get_all(scope_id=user_bob_id)

    alice_name = await facts.get("user_name", scope_id=user_id)
    bob_name = await facts.get("user_name", scope_id=user_bob_id)

    assert alice_name is not None
    assert bob_name is not None
    assert alice_name.value == "Alice Johnson"
    assert bob_name.value == "Bob Smith"
    assert len(alice_facts) != len(bob_facts)
    print(
        f"   ✅ User isolation: Alice has {len(alice_facts)} facts, Bob has {len(bob_facts)} facts"
    )

    print("\n10. Real-world scenario: Clear all facts for a user...")
    # Simulate user account deletion or reset
    deleted_count = await facts.clear_all(scope_id=user_bob_id)
    print(f"   ✅ Cleared {deleted_count} facts for Bob")

    # Verify deletion
    bob_facts_after = await facts.get_all(scope_id=user_bob_id)
    assert len(bob_facts_after) == 0
    print("   ✅ Verified: Bob's facts are cleared")

    # Alice's facts should still exist
    alice_facts_after = await facts.get_all(scope_id=user_id)
    assert len(alice_facts_after) > 0
    print(f"   ✅ Verified: Alice still has {len(alice_facts_after)} facts")

    print("\n11. Testing edge cases...")
    # Update non-existent fact (should raise)
    try:
        await facts.update("non_existent", "value", scope_id=user_id)
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        print("   ✅ Update non-existent fact raises ValueError")

    # Get non-existent fact (should return None)
    non_existent = await facts.get("non_existent", scope_id=user_id)
    assert non_existent is None
    print("   ✅ Get non-existent fact returns None")

    # Bulk update with non-existent facts (should create them)
    new_facts = await facts.bulk_update(
        [{"key": "new_fact_1", "value": "value1"}, {"key": "new_fact_2", "value": "value2"}],
        scope_id=user_id,
    )
    assert len(new_facts) == 2
    print(f"   ✅ Bulk update created {len(new_facts)} new facts")

    print("\n12. Final verification: All facts for Alice...")
    final_facts = await facts.get_all(scope_id=user_id)
    print(f"   ✅ Alice has {len(final_facts)} total facts:")
    for fact in final_facts[:5]:  # Show first 5
        print(f"      - {fact.key}: {fact.value}")

    await storage.disconnect()

    print("\n✅ Comprehensive test completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
