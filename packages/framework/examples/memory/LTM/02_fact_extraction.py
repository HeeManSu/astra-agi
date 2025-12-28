"""
Example 2: Fact Extraction from Conversations

Tests automatic fact extraction from conversation messages:
1. Extract facts from user messages
2. Store extracted facts
3. Verify extraction quality

Uses local HuggingFace model - no API key required.
"""

import asyncio

# MongoDB - no file cleanup needed
from framework.memory import MemoryScope, PersistentFacts
from framework.models.huggingface import HuggingFaceLocal
from framework.storage.databases.mongodb import MongoDBStorage


async def main():
    """Test fact extraction."""
    print("=== Fact Extraction from Conversations ===\n")

    # Setup storage
    # MongoDB connection

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_ltm_test")
    await storage.connect()

    # Initialize local HuggingFace model (smaller model for faster loading)
    print("Loading local model (first time may take a few minutes to download)...")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct")

    # Initialize PersistentFacts with auto-extraction enabled
    facts = PersistentFacts(
        storage=storage,
        scope=MemoryScope.USER,
        auto_extract=True,
        extraction_model=model,
    )

    user_id = "user_extract_001"

    print("\n1. Extracting facts from conversation...")
    # Simulate a conversation
    messages = [
        {
            "role": "user",
            "content": "Hi, my name is Sarah Connor. I live in Los Angeles and I'm a software engineer.",
        },
        {
            "role": "assistant",
            "content": "Nice to meet you, Sarah! What kind of software do you work on?",
        },
        {
            "role": "user",
            "content": "I work on AI systems. I prefer dark mode UI and I love hiking on weekends.",
        },
    ]

    # Extract facts
    extracted = await facts.extract_from_messages(messages, scope_id=user_id, model=model)
    print(f"   Extracted {len(extracted)} facts:")

    # Store extracted facts
    for fact in extracted:
        print(f"   - {fact.key}: {fact.value}")
        # Check if fact already exists
        existing = await facts.get(fact.key, scope_id=user_id)
        if existing:
            await facts.update(fact.key, fact.value, scope_id=user_id)
            print("     (Updated existing fact)")
        else:
            await facts.add(fact.key, fact.value, scope_id=user_id, tags=fact.tags)
            print("     (Added new fact)")

    print("\n2. Verifying stored facts...")
    # Get all facts
    all_facts = await facts.get_all(scope_id=user_id)
    print(f"   Total stored facts: {len(all_facts)}")
    for fact in all_facts:
        print(f"   - {fact.key}: {fact.value}")

    print("\n3. Testing with more complex conversation...")
    # More complex conversation
    messages2 = [
        {
            "role": "user",
            "content": "Actually, I changed my mind. I prefer light mode now, and I'm learning Python programming.",
        },
    ]

    extracted2 = await facts.extract_from_messages(messages2, scope_id=user_id, model=model)
    print(f"   Extracted {len(extracted2)} new/updated facts:")

    for fact in extracted2:
        existing = await facts.get(fact.key, scope_id=user_id)
        if existing:
            await facts.update(fact.key, fact.value, scope_id=user_id)
            print(f"   - Updated: {fact.key} = {fact.value}")
        else:
            await facts.add(fact.key, fact.value, scope_id=user_id, tags=fact.tags)
            print(f"   - Added: {fact.key} = {fact.value}")

    print("\n4. Final fact state...")
    final_facts = await facts.get_all(scope_id=user_id)
    for fact in final_facts:
        print(f"   - {fact.key}: {fact.value}")

    await storage.disconnect()

    print("\n✅ Fact extraction test completed!")


if __name__ == "__main__":
    asyncio.run(main())
