import asyncio
import os
from framework.agents import Agent
from framework.astra import Astra
from framework.models import Gemini
from framework.storage import SQLiteStorage

async def main():
    """
    Example of Astra-managed storage.
    Astra injects the storage backend into all managed agents.
    
    Prerequisites:
    - Set GOOGLE_API_KEY environment variable.
    """
    print("=== Astra Managed Storage Example ===")
    
    # 1. Initialize Shared Storage
    storage = SQLiteStorage("file:astra_shared.db")
    
    # 2. Create Agents (without storage)
    agent1 = Agent(name="Agent1", model=Gemini("1.5-flash"))
    agent2 = Agent(name="Agent2", model=Gemini("1.5-flash"))
    
    # 3. Initialize Astra with Storage
    # Astra will inject this storage into agent1 and agent2
    astra = Astra(
        agents=[agent1, agent2],
        storage=storage
    )
    
    print(f"Agent1 storage: {agent1.storage}")
    print(f"Agent2 storage: {agent2.storage}")
    
    # 4. Run Agents
    # Both agents will save to the same DB (but different threads/IDs)
    await agent1.invoke("Hello from Agent 1")
    await agent2.invoke("Hello from Agent 2")
    
    # 5. Verify Persistence
    # We can access storage directly to verify
    await storage.connect()
    
    assert agent1.memory is not None
    assert agent2.memory is not None
    
    history1 = await agent1.memory.get_history(agent1.id)
    history2 = await agent2.memory.get_history(agent2.id)
    
    print(f"\nAgent1 History: {len(history1)} messages")
    print(f"Agent2 History: {len(history2)} messages")
    
    # Cleanup
    await astra.shutdown() # Handles agent shutdown
    await storage.disconnect()
    
    if os.path.exists("astra_shared.db"):
        os.remove("astra_shared.db")

if __name__ == "__main__":
    asyncio.run(main())
