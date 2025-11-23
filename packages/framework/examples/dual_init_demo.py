import asyncio
from framework.agents import Agent
from framework.astra import Astra
from framework.models import Gemini

# Mock resources for demonstration
class MockStorage:
    def __repr__(self): return "PostgresStorage(url='...')"

class MockKnowledge:
    def __repr__(self): return "PDFKnowledgeBase(path='...')"

async def main():
    print("=== Pattern 1: Standalone Agent (The 'Hello World') ===")
    # Simple, zero-friction initialization
    # Uses explicit model class (Recommended)
    agent1 = Agent(
        name="StandaloneBot",
        model=Gemini("1.5-flash"),
        instructions="You are a helpful assistant."
    )
    
    # Auto-initializes on first use
    # Note: In a real run, we'd await agent1.invoke("Hi")
    print(f"Created: {agent1}")
    print(f"Context initialized? {agent1._initialized}")  # False until invoked
    
    print("\n=== Pattern 2: Managed System (The 'Enterprise') ===")
    # Centralized management with shared resources
    storage = MockStorage()
    knowledge = MockKnowledge()
    
    # Define agents
    agent2 = Agent(name="Researcher", model=Gemini("1.5-pro"))
    agent3 = Agent(name="Writer", model=Gemini("1.5-flash"))
    
    # Initialize Astra with agents and global resources
    astra = Astra(
        agents=[agent2, agent3],
        storage=storage,
        knowledge=knowledge
    )
    
    print(f"Astra initialized with {len(astra.list_agents())} agents")
    print(f"Agent 2 storage: {agent2.storage}")  # Injected automatically
    print(f"Agent 3 knowledge: {agent3.knowledge}")  # Injected automatically
    
    print("\n=== Pattern 3: Dynamic Addition ===")
    # Add a new agent later
    agent4 = Agent(name="Analyst", model=Gemini("1.5-flash"))
    print(f"Agent 4 before add: storage={agent4.storage}")
    
    astra.add_agent(agent4)
    print(f"Agent 4 after add: storage={agent4.storage}")  # Injected!

if __name__ == "__main__":
    asyncio.run(main())
