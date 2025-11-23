import asyncio
from framework import Agent, tool

@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

# Minimal initialization as requested
agent = Agent(
    model="google/gemini-1.5-flash",
    tools=[add, multiply],
)

async def main():
    print(f"Agent Name: {agent.name}")
    print(f"Agent Instructions: {agent.instructions}")
    print(f"Agent Model: {agent.model}")
    print(f"Agent Tools: {[t.name for t in agent.tools]}")
    
    # Verify context lazy init
    print(f"Context Initialized: {agent.context is not None}")

if __name__ == "__main__":
    asyncio.run(main())
