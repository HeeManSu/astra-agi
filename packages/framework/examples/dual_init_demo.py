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
    
    print("\n=== Pattern 2: Shared Infrastructure (The 'Enterprise') ===")
    # Initialize global infrastructure
    astra = Astra()
    
    # Create shared resources
    storage = MockStorage()
    knowledge = MockKnowledge()
    
    # Define agents with shared resources
    agent2 = Agent(
        name="Researcher", 
        model=Gemini("1.5-pro"),
        storage=storage,
        knowledge=knowledge
    )
    
    agent3 = Agent(
        name="Writer", 
        model=Gemini("1.5-flash"),
        storage=storage
    )
    
    # Manually share context (optional, but good for shared observability)
    agent2.set_context(astra.context)
    agent3.set_context(astra.context)
    
    print(f"Astra initialized: {astra}")
    print(f"Agent 2 storage: {agent2.storage}")
    print(f"Agent 3 storage: {agent3.storage}")
    
    print("\n=== Pattern 3: Dynamic Addition ===")
    # Add a new agent later
    agent4 = Agent(name="Analyst", model=Gemini("1.5-flash"))
    
    # Share context
    agent4.set_context(astra.context)
    print(f"Agent 4 context shared: {agent4.context}")

if __name__ == "__main__":
    asyncio.run(main())
