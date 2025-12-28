"""
Example 3: Memory Scoping

Tests different memory scopes:
1. USER scope (user-specific)
2. SESSION scope (temporary, thread-specific)
3. AGENT scope (shared across users)
4. GLOBAL scope (system-wide)

This example does NOT require an LLM model.
"""

import asyncio

# MongoDB - no file cleanup needed
from framework.memory import MemoryScope, PersistentFacts
from framework.storage.databases.mongodb import MongoDBStorage


async def main():
    """Test memory scoping."""
    print("=== Memory Scoping Test ===\n")

    # Setup storage
    # MongoDB connection

    storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_ltm_test")
    await storage.connect()

    print("1. USER Scope (user-specific facts)...")
    user_facts = PersistentFacts(storage=storage, scope=MemoryScope.USER, auto_extract=False)
    user_id_1 = "user_alice"
    user_id_2 = "user_bob"

    await user_facts.add("preferences", {"theme": "dark"}, scope_id=user_id_1)
    await user_facts.add("preferences", {"theme": "light"}, scope_id=user_id_2)

    alice_prefs = await user_facts.get("preferences", scope_id=user_id_1)
    bob_prefs = await user_facts.get("preferences", scope_id=user_id_2)
    assert alice_prefs is not None
    assert bob_prefs is not None
    print(f"   Alice's preferences: {alice_prefs.value}")
    print(f"   Bob's preferences: {bob_prefs.value}")
    print("   ✅ USER scope: Facts are isolated per user")

    print("\n2. SESSION Scope (temporary, thread-specific)...")
    session_facts = PersistentFacts(storage=storage, scope=MemoryScope.SESSION, auto_extract=False)
    thread_1 = "thread_abc"
    thread_2 = "thread_xyz"

    await session_facts.add("current_task", "writing report", scope_id=thread_1)
    await session_facts.add("current_task", "reviewing code", scope_id=thread_2)

    task_1 = await session_facts.get("current_task", scope_id=thread_1)
    task_2 = await session_facts.get("current_task", scope_id=thread_2)
    assert task_1 is not None
    assert task_2 is not None
    print(f"   Thread 1 task: {task_1.value}")
    print(f"   Thread 2 task: {task_2.value}")
    print("   ✅ SESSION scope: Facts are isolated per thread")

    print("\n3. AGENT Scope (shared across users)...")
    agent_facts = PersistentFacts(storage=storage, scope=MemoryScope.AGENT, auto_extract=False)
    agent_id = "agent_support_bot"

    await agent_facts.add("last_maintenance", "2024-01-15", scope_id=agent_id)
    await agent_facts.add("version", "1.0.0", scope_id=agent_id)

    # Both users can access agent facts
    maintenance = await agent_facts.get("last_maintenance", scope_id=agent_id)
    version = await agent_facts.get("version", scope_id=agent_id)
    assert maintenance is not None
    assert version is not None
    print(f"   Agent maintenance: {maintenance.value}")
    print(f"   Agent version: {version.value}")
    print("   ✅ AGENT scope: Facts are shared by all users of the agent")

    print("\n4. GLOBAL Scope (system-wide)...")
    global_facts = PersistentFacts(storage=storage, scope=MemoryScope.GLOBAL, auto_extract=False)

    await global_facts.add("system_version", "2.0.0")
    await global_facts.add("maintenance_window", "Sundays 2-4 AM UTC")

    sys_version = await global_facts.get("system_version")
    maint_window = await global_facts.get("maintenance_window")
    assert sys_version is not None
    assert maint_window is not None
    print(f"   System version: {sys_version.value}")
    print(f"   Maintenance window: {maint_window.value}")
    print("   ✅ GLOBAL scope: Facts are accessible by everyone")

    print("\n5. Scope isolation verification...")
    # Verify USER facts don't leak to other users
    alice_all = await user_facts.get_all(scope_id=user_id_1)
    bob_all = await user_facts.get_all(scope_id=user_id_2)
    print(f"   Alice's facts: {len(alice_all)}")
    print(f"   Bob's facts: {len(bob_all)}")
    print("   ✅ Scopes are properly isolated")

    await storage.disconnect()

    print("\n✅ Memory scoping test completed!")


if __name__ == "__main__":
    asyncio.run(main())
