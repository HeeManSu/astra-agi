"""Agent with memory example - CONCEPT DEMONSTRATION

NOTE: This is a concept demonstration. Full persistent facts functionality 
requires storage backend configuration.

Shows the concept of:
- AgentMemory for conversation history
- PersistentFacts for cross-session knowledge  
- Memory scopes (GLOBAL, USER, THREAD)
"""

import asyncio

from astra import Agent, MemoryScope
from astra import HuggingFaceLocal


async def main():
    """
    Concept demonstration of memory and facts.
    
    In production, you would configure storage backend for persistence.
    """
    
    print("=== Astra Agent with Memory (Concept Demo) ===\n")
    
    # Create an agent
    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="""You are a helpful personal assistant.
        You should remember information about the user across conversations.""",
        name="memory-demo",
    )
    
    #First conversation
    print("👤 User: My name is Alice and I'm a software engineer at TechCorp")
    response = await agent.invoke("My name is Alice and I'm a software engineer at TechCorp")
    print(f"🤖 Agent: {response}\n")
    
    # In a real implementation with persistent facts:
    # - Facts would be automatically extracted from conversations
    # - Facts would be stored in a database with scopes:
    #   * GLOBAL: Shared across all users/threads
    #   * USER: Specific to a user ID
    #   * THREAD: Specific to a conversation thread
    
    print("=" * 60)
    print("Memory & Facts Concepts")
    print("=" * 60)
    print("\n📝 **MemoryScope**:")
    print(f"  - GLOBAL: {MemoryScope.GLOBAL}")
    print(f"  - USER: {MemoryScope.USER}")
    print(f"  - SESSION: {MemoryScope.SESSION}")
    
    print("\n💾 **PersistentFacts** (requires storage):")
    print("  - Stores facts across sessions")
    print("  - Methods: add(), get(), get_all(), update(), delete()")
    print("  - Each fact has: key, value, scope, scope_id")
    
    print("\n🧠 **AgentMemory**:")
    print("  - Manages conversation history")
    print("  - Integrates with storage backend")
    print("  - Supports thread-based conversations")
    
    print("\n✅ To use full memory features:")
    print("  1. Configure storage backend (LibSQL or MongoDB)")
    print("  2. Pass storage to agent")
    print("  3. Use PersistentFacts(storage=storage)")
    print("  4. Facts are automatically persisted")


if __name__ == "__main__":
    asyncio.run(main())
