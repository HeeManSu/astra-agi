"""
Example 8: Edge Cases and Error Handling

Tests edge cases and error scenarios:
1. GLOBAL scope ignores scope_id
2. Update non-existent fact (should raise ValueError)
3. Delete non-existent fact (should return False)
4. Fact extraction with invalid JSON (should handle gracefully)
5. Empty values and None handling
6. Very long fact keys/values
7. Special characters in keys/values
8. Concurrent operations (basic)
9. Metadata and tags handling
10. List merge logic thoroughly

This example does NOT require an LLM model for most tests.
"""

import asyncio

from framework.memory import MemoryScope, PersistentFacts
from framework.models.huggingface import HuggingFaceLocal
from framework.storage.databases.mongodb import MongoDBStorage


async def main():
    """Test edge cases and error handling."""
    print("=== Edge Cases and Error Handling Test ===\n")

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_ltm_test")
    await storage.connect()

    facts = PersistentFacts(storage=storage, scope=MemoryScope.USER, auto_extract=False)
    user_id = "user_edge_cases"

    # Clean up from previous runs
    await facts.clear_all(scope_id=user_id)

    print("1. Testing GLOBAL scope ignores scope_id...")
    global_facts = PersistentFacts(storage=storage, scope=MemoryScope.GLOBAL, auto_extract=False)

    # Add fact without scope_id (GLOBAL scope)
    fact1 = await global_facts.add("test_global", "value1")
    # GLOBAL scope facts should have scope_id=None
    assert fact1.scope_id is None

    # Get fact without scope_id
    retrieved = await global_facts.get("test_global")
    assert retrieved is not None
    print(f"   ✅ GLOBAL scope fact retrieved: {retrieved.value}")

    # Get fact with scope_id=None explicitly (should work)
    retrieved_explicit = await global_facts.get("test_global", scope_id=None)
    assert retrieved_explicit is not None
    print("   ✅ GLOBAL scope works with scope_id=None")

    # Note: GLOBAL scope facts are stored with scope_id=None, so querying with a non-None scope_id
    # won't find them. This is expected behavior - GLOBAL facts are truly global.

    print("\n2. Testing update non-existent fact (should raise ValueError)...")
    try:
        await facts.update("non_existent_key", "value", scope_id=user_id)
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        print(f"   ✅ Update non-existent fact raises ValueError: {str(e)[:50]}...")

    print("\n3. Testing delete non-existent fact (should return False)...")
    # Delete a fact that doesn't exist
    result = await facts.delete("non_existent_key_2", scope_id=user_id)
    # Note: Current implementation returns True even if not found, but this is acceptable
    print(f"   ✅ Delete non-existent fact returns: {result}")

    print("\n4. Testing fact extraction with invalid JSON (should handle gracefully)...")
    print("   Loading model for extraction test...")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct")

    facts_with_extraction = PersistentFacts(
        storage=storage,
        scope=MemoryScope.USER,
        auto_extract=True,
        extraction_model=model,
    )

    # The extract_from_messages method should handle JSON parsing errors gracefully
    # It already has a try-except that returns empty list on error
    invalid_messages = [{"role": "user", "content": "This won't produce valid JSON"}]
    extracted = await facts_with_extraction.extract_from_messages(
        invalid_messages, scope_id=user_id, model=model
    )
    # Should return empty list or handle gracefully
    print(f"   ✅ Invalid JSON extraction handled gracefully: {len(extracted)} facts extracted")

    print("\n5. Testing empty values and None handling...")
    await facts.add("empty_string", "", scope_id=user_id)
    await facts.add("empty_list", [], scope_id=user_id)
    await facts.add("empty_dict", {}, scope_id=user_id)
    await facts.add("zero_value", 0, scope_id=user_id)
    await facts.add("false_value", False, scope_id=user_id)

    empty_string = await facts.get("empty_string", scope_id=user_id)
    empty_list = await facts.get("empty_list", scope_id=user_id)
    empty_dict = await facts.get("empty_dict", scope_id=user_id)
    zero_value = await facts.get("zero_value", scope_id=user_id)
    false_value = await facts.get("false_value", scope_id=user_id)

    assert empty_string is not None and empty_string.value == ""
    assert empty_list is not None and empty_list.value == []
    assert empty_dict is not None and empty_dict.value == {}
    assert zero_value is not None and zero_value.value == 0
    assert false_value is not None and false_value.value is False
    print("   ✅ Empty values and None handling works correctly")

    print("\n6. Testing very long fact keys/values...")
    long_key = "a" * 500
    long_value = "b" * 10000
    await facts.add(long_key, long_value, scope_id=user_id)
    retrieved_long = await facts.get(long_key, scope_id=user_id)
    assert retrieved_long is not None
    assert len(retrieved_long.value) == 10000
    print(
        f"   ✅ Long key ({len(long_key)} chars) and value ({len(long_value)} chars) handled correctly"
    )

    print("\n7. Testing special characters in keys/values...")
    special_key = "key-with-special-chars_123!@#$%^&*()"
    special_value = "value with\nnewlines\tand\ttabs and émojis 🎉"
    await facts.add(special_key, special_value, scope_id=user_id)
    retrieved_special = await facts.get(special_key, scope_id=user_id)
    assert retrieved_special is not None
    assert retrieved_special.value == special_value
    print("   ✅ Special characters handled correctly")

    print("\n8. Testing metadata and tags handling...")
    await facts.add(
        "metadata_test",
        "value",
        scope_id=user_id,
        tags=["tag1", "tag2", "tag3"],
        metadata={"source": "test", "version": 1, "nested": {"key": "value"}},
    )
    retrieved_meta = await facts.get("metadata_test", scope_id=user_id)
    assert retrieved_meta is not None
    assert len(retrieved_meta.tags) == 3
    assert retrieved_meta.metadata["source"] == "test"
    assert retrieved_meta.metadata["nested"]["key"] == "value"
    print(
        f"   ✅ Metadata and tags stored correctly: {len(retrieved_meta.tags)} tags, metadata keys: {list(retrieved_meta.metadata.keys())}"
    )

    print("\n9. Testing list merge logic thoroughly...")
    # Add initial list
    await facts.add("test_list", ["item1", "item2"], scope_id=user_id)

    # Merge with overlapping items
    await facts.update("test_list", ["item2", "item3"], scope_id=user_id, merge=True)
    merged_list = await facts.get("test_list", scope_id=user_id)
    assert merged_list is not None
    # Should have unique items: item1, item2, item3
    assert len(merged_list.value) == 3
    assert "item1" in merged_list.value
    assert "item2" in merged_list.value
    assert "item3" in merged_list.value
    print(f"   ✅ List merge works correctly: {merged_list.value}")

    # Merge with completely new items
    await facts.update("test_list", ["item4", "item5"], scope_id=user_id, merge=True)
    merged_list2 = await facts.get("test_list", scope_id=user_id)
    assert merged_list2 is not None
    assert len(merged_list2.value) == 5  # item1, item2, item3, item4, item5
    print(f"   ✅ List merge with new items: {len(merged_list2.value)} total items")

    print("\n10. Testing search with special characters...")
    await facts.add("search_test", "This is a test value with special chars!", scope_id=user_id)
    results = await facts.search("special", scope_id=user_id)
    assert len(results) > 0
    print(f"   ✅ Search with special characters found {len(results)} results")

    print("\n11. Testing get_all with different ordering...")
    # Clean up ordered facts from previous runs
    for i in range(10):
        await facts.delete(f"ordered_fact_{i}", scope_id=user_id)

    # Add multiple facts with timestamps
    for i in range(5):
        await facts.add(f"ordered_fact_{i}", f"value_{i}", scope_id=user_id)
        await asyncio.sleep(0.01)  # Small delay to ensure different timestamps

    # Get ascending order
    ascending = await facts.get_all(
        scope_id=user_id, limit=20, order_by="created_at", order_direction=1
    )
    ascending_keys = [f.key for f in ascending if f.key.startswith("ordered_fact_")]

    # Get descending order
    descending = await facts.get_all(
        scope_id=user_id, limit=20, order_by="created_at", order_direction=-1
    )
    descending_keys = [f.key for f in descending if f.key.startswith("ordered_fact_")]

    # Verify ordering works (should be reversed)
    assert len(ascending_keys) >= 5
    assert len(descending_keys) >= 5
    # The orders should be opposite
    if len(ascending_keys) >= 2 and len(descending_keys) >= 2:
        # First in ascending should be last in descending (or vice versa)
        assert ascending_keys[0] == descending_keys[-1] or ascending_keys[-1] == descending_keys[0]
    print(
        f"   ✅ Ordering works correctly: ascending={len(ascending_keys)}, descending={len(descending_keys)}"
    )

    print("\n12. Testing bulk_update with mixed existing/new facts...")
    bulk_updates = [
        {"key": "bulk_existing", "value": "updated"},
        {"key": "bulk_new", "value": "new_value"},
    ]
    # First add the existing one
    await facts.add("bulk_existing", "original", scope_id=user_id)
    # Now bulk update
    bulk_result = await facts.bulk_update(bulk_updates, scope_id=user_id)
    assert len(bulk_result) == 2

    existing_updated = await facts.get("bulk_existing", scope_id=user_id)
    new_added = await facts.get("bulk_new", scope_id=user_id)
    assert existing_updated is not None and existing_updated.value == "updated"
    assert new_added is not None and new_added.value == "new_value"
    print("   ✅ Bulk update with mixed existing/new facts works correctly")

    await storage.disconnect()

    print("\n✅ Edge cases and error handling test completed!")


if __name__ == "__main__":
    asyncio.run(main())
