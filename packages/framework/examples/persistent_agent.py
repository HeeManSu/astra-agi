import asyncio
import os
from framework.agents import Agent
from framework.models import Gemini
from framework.storage import SQLiteStorage

async def main():
    """
    Example of a persistent agent using SQLite storage.
    
    Prerequisites:
    - Set GOOGLE_API_KEY environment variable.
    """
    print("=== Persistent Agent Example ===")
    
    # 1. Initialize Storage
    # Use a local file for persistence
    storage = SQLiteStorage("file:agent_memory.db")
    await storage.connect()
    
    # 2. Create Agent with Storage
    agent = Agent(
        name="MemoryBot",
        model=Gemini("1.5-flash"),
        instructions="You are a helpful assistant with a good memory.",
        storage=storage
    )
    
    print(f"Agent initialized with storage: {agent.storage}")
    
    # 3. Run Agent
    # The agent will automatically save interactions to the database
    response = await agent.invoke("My favorite color is blue.")
    print(f"\nUser: My favorite color is blue.")
    print(f"Agent: {response}")
    
    response = await agent.invoke("What is my favorite color?")
    print(f"\nUser: What is my favorite color?")
    print(f"Agent: {response}")
    
    # 4. Verify History
    assert agent.memory is not None
    history = await agent.memory.get_history(agent.id)
    print(f"\nHistory in DB ({len(history)} messages):")
    for msg in history:
        print(f"- [{msg.role}]: {msg.content[:50]}...")
        
    # Cleanup
    await agent.shutdown()
    await storage.disconnect()
    
    # Uncomment to keep the DB file
    if os.path.exists("agent_memory.db"):
        os.remove("agent_memory.db")

if __name__ == "__main__":
    asyncio.run(main())
