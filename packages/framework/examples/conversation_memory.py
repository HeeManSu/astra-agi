import asyncio
import os
from framework.agents import Agent
from framework.models import Gemini
from framework.storage import SQLiteStorage

async def main():
    """
    Example demonstrating short-term memory (conversation continuity).
    
    Shows how agents maintain context across multiple turns using thread_id,
    while only loading recent messages to minimize token usage.
    """
    print("=== Short-Term Memory Example ===\n")
    
    # Setup storage
    storage = SQLiteStorage("conversation_demo.db")
    await storage.connect()
    
    # Create agent with storage
    agent = Agent(
        name="MemoryBot",
        model=Gemini("1.5-flash"),
        instructions="You are a helpful assistant with memory.",
        storage=storage
    )
    
    print("Agent created with short-term memory enabled.")
    print("The agent will remember recent conversation context.\n")
    
    # Conversation 1: Introduce yourself
    print("=" * 60)
    print("Turn 1: Introducing yourself")
    print("=" * 60)
    response1 = await agent.invoke(
        "My name is Alice and I love Python programming.",
        thread_id="conversation-1"  # Use thread_id for continuity
    )
    print(f"User: My name is Alice and I love Python programming.")
    print(f"Agent: {response1['content']}\n")
    
    # Conversation 2: Agent should remember your name
    print("=" * 60)
    print("Turn 2: Testing memory (should remember name)")
    print("=" * 60)
    response2 = await agent.invoke(
        "What's my name?",
        thread_id="conversation-1"  # Same thread_id = same context
    )
    print(f"User: What's my name?")
    print(f"Agent: {response2['content']}\n")
    
    # Conversation 3: Agent should remember your interest
    print("=" * 60)
    print("Turn 3: Testing memory (should remember interest)")
    print("=" * 60)
    response3 = await agent.invoke(
        "What programming language do I like?",
        thread_id="conversation-1"
    )
    print(f"User: What programming language do I like?")
    print(f"Agent: {response3['content']}\n")
    
    # New conversation (different thread_id = fresh context)
    print("=" * 60)
    print("Turn 4: New conversation (different thread_id)")
    print("=" * 60)
    response4 = await agent.invoke(
        "What's my name?",
        thread_id="conversation-2"  # Different thread = no context
    )
    print(f"User: What's my name?")
    print(f"Agent: {response4['content']}")
    print("(Should not know, since this is a new conversation)\n")
    
    # Cleanup
    await agent.shutdown()
    await storage.disconnect()
    
    if os.path.exists("conversation_demo.db"):
        os.remove("conversation_demo.db")
    
    print("\n" + "=" * 60)
    print("KEY POINTS:")
    print("=" * 60)
    print("1. Use thread_id to maintain conversation context")
    print("2. Only recent messages are loaded (default: last 10)")
    print("3. This minimizes token usage while maintaining continuity")
    print("4. Different thread_id = different conversation context")

if __name__ == "__main__":
    asyncio.run(main())
