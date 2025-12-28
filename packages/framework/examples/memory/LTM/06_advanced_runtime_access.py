"""
Example 6: Advanced Runtime Access

Demonstrates a complex real-world scenario:
1. Pre-populate facts before agent conversations
2. Runtime fact access during conversations
3. Fact updates during conversations
4. Multi-thread conversations with shared facts
5. Fact retrieval and context injection

This mimics a production scenario where:
- Facts are pre-loaded from external sources (DB, API, etc.)
- Agent uses facts to personalize responses
- Facts are accessed and updated during runtime

Uses local HuggingFace model - no API key required.
"""

import asyncio

# MongoDB - no file cleanup needed
from framework.agents import Agent
from framework.memory import MemoryScope, PersistentFacts
from framework.models.huggingface import HuggingFaceLocal
from framework.storage.databases.mongodb import MongoDBStorage


async def main():
    """Advanced runtime access demonstration."""
    print("=== Advanced Runtime Access Demo ===\n")

    # Setup storage
    # MongoDB connection

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_ltm_test")
    await storage.connect()

    print("Loading local model (first time may take a few minutes to download)...")
    model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct")

    print("\n1. Pre-populating facts from external source (simulated)...")
    # Simulate loading facts from external source (DB, API, etc.)
    persistent_facts = PersistentFacts(
        storage=storage,
        scope=MemoryScope.USER,
        auto_extract=True,
        extraction_model=model,
    )

    user_id = "user_production_001"

    # Pre-populate facts (as if loaded from external source)
    await persistent_facts.add("user_name", "Emma Watson", scope_id=user_id)
    await persistent_facts.add("user_email", "[email protected]", scope_id=user_id)
    await persistent_facts.add(
        "preferences",
        {"theme": "dark", "language": "en", "timezone": "PST", "notifications": True},
        scope_id=user_id,
    )
    await persistent_facts.add("interests", ["reading", "yoga", "travel"], scope_id=user_id)
    await persistent_facts.add("location", "Los Angeles, CA", scope_id=user_id)
    await persistent_facts.add("occupation", "Software Engineer", scope_id=user_id)
    await persistent_facts.add("company", "TechCorp Inc.", scope_id=user_id)

    print("   ✅ Pre-populated 7 facts:")
    pre_facts = await persistent_facts.get_all(scope_id=user_id)
    for fact in pre_facts:
        print(f"      - {fact.key}: {fact.value}")

    print("\n2. Creating agent with persistent facts enabled...")
    # Create agent with persistent facts
    agent = Agent(
        name="PersonalAssistant",
        instructions="You are a helpful personal assistant. Use the user's facts to personalize your responses.",
        model=model,
        storage=storage,
        persistent_facts=persistent_facts,  # Use pre-configured PersistentFacts
    )

    # Assert persistent_facts is set (for type checker)
    assert agent.persistent_facts is not None

    print("   ✅ Agent created with:")
    print("      - Model: HuggingFace SmolLM2-360M-Instruct")
    print("      - Persistent facts: Enabled")

    thread_1 = "thread_support"
    thread_2 = "thread_shopping"

    print("\n3. Conversation 1: Agent accesses pre-populated facts...")
    response1 = await agent.invoke(
        "What do you know about me?",
        user_id=user_id,
        thread_id=thread_1,
    )
    print(f"   Agent: {response1[:200]}...")
    print("   ✅ Agent accessed pre-populated facts at runtime")

    await asyncio.sleep(0.5)

    print("\n4. Conversation 2: User shares new information...")
    response2 = await agent.invoke(
        "I just got promoted to Senior Software Engineer! Also, I'm learning Spanish now.",
        user_id=user_id,
        thread_id=thread_1,
    )
    print(f"   Agent: {response2[:200]}...")

    await asyncio.sleep(0.5)

    print("\n5. Verifying facts after conversations...")
    all_facts_after = await agent.persistent_facts.get_all(scope_id=user_id)
    print(f"   Total facts now: {len(all_facts_after)}")
    for fact in all_facts_after:
        print(f"      - {fact.key}: {fact.value}")

    print("\n6. Conversation 3: Different thread, agent recalls facts...")
    response3 = await agent.invoke(
        "What's my current job title?",
        user_id=user_id,
        thread_id=thread_2,  # Different thread
    )
    print(f"   Agent: {response3[:200]}...")
    print("   ✅ Agent recalled facts across different threads")

    await asyncio.sleep(0.5)

    print("\n7. Manual preference update with merge...")
    prefs = await agent.persistent_facts.get("preferences", scope_id=user_id)
    if prefs:
        await agent.persistent_facts.update(
            "preferences", {"theme": "light"}, scope_id=user_id, merge=True
        )
        updated_prefs = await agent.persistent_facts.get("preferences", scope_id=user_id)
        print(f"   ✅ Preferences updated (merge): {updated_prefs.value}")

    print("\n8. Explicit fact access (programmatic)...")
    # Access facts directly without agent
    user_name = await agent.persistent_facts.get("user_name", scope_id=user_id)
    preferences = await agent.persistent_facts.get("preferences", scope_id=user_id)
    interests = await agent.persistent_facts.get("interests", scope_id=user_id)

    print("   Retrieved directly:")
    print(f"      - Name: {user_name.value if user_name else 'N/A'}")
    print(f"      - Preferences: {preferences.value if preferences else 'N/A'}")
    print(f"      - Interests: {interests.value if interests else 'N/A'}")

    print("\n9. Search facts programmatically...")
    work_facts = await agent.persistent_facts.search("engineer", scope_id=user_id)
    print(f"   Search 'engineer': Found {len(work_facts)} facts")
    for fact in work_facts:
        print(f"      - {fact.key}: {fact.value}")

    print("\n10. Bulk operations demonstration...")
    bulk_facts = [
        {"key": "skills", "value": ["Python", "JavaScript", "React"]},
        {"key": "education", "value": "BS Computer Science"},
    ]
    bulk_updated = await agent.persistent_facts.bulk_update(bulk_facts, scope_id=user_id)
    print(f"   ✅ Bulk added/updated {len(bulk_updated)} facts")

    skills = await agent.persistent_facts.get("skills", scope_id=user_id)
    education = await agent.persistent_facts.get("education", scope_id=user_id)
    print(f"      - Skills: {skills.value if skills else 'N/A'}")
    print(f"      - Education: {education.value if education else 'N/A'}")

    print("\n11. Final fact summary...")
    final_facts = await agent.persistent_facts.get_all(scope_id=user_id)
    print(f"   Total facts stored: {len(final_facts)}")
    print("   Facts by category:")
    categories = {}
    for fact in final_facts:
        category = fact.key.split("_")[0] if "_" in fact.key else "other"
        categories.setdefault(category, []).append(fact.key)

    for category, keys in categories.items():
        print(
            f"      - {category}: {len(keys)} facts ({', '.join(keys[:3])}{'...' if len(keys) > 3 else ''})"
        )

    await storage.disconnect()

    print("\n✅ Advanced runtime access test completed!")
    print("\nKey Takeaways:")
    print("  1. Facts can be pre-populated before agent conversations")
    print("  2. Facts are automatically accessed during agent.invoke()")
    print("  3. Facts can be updated during conversations")
    print("  4. Facts persist across different threads for the same user")
    print("  5. Facts can be accessed programmatically without agent")
    print("  6. Bulk operations enable efficient fact management")


if __name__ == "__main__":
    asyncio.run(main())
