import asyncio
from framework.agents import Agent
from framework.models import Gemini

async def main():
    """
    Example demonstrating agent configuration properties.
    
    Shows how to configure temperature, max_tokens, max_retries, and stream
    at the agent level for consistent behavior.
    """
    print("=== Agent Configuration Example ===\n")
    
    # 1. Create agent with custom configuration
    creative_agent = Agent(
        name="CreativeWriter",
        model=Gemini("1.5-flash"),
        instructions="You are a creative writer.",
        temperature=1.2,  # Higher temperature for more creativity
        max_tokens=2048,  # Limit response length
        max_retries=5,    # More retries for reliability
        stream=False      # Complete responses (default)
    )
    
    print(f"Agent: {creative_agent.name}")
    print(f"Temperature: {creative_agent.temperature}")
    print(f"Max Tokens: {creative_agent.max_tokens}")
    print(f"Max Retries: {creative_agent.max_retries}")
    print(f"Stream: {creative_agent.stream}")
    
    # 2. Create agent with defaults
    default_agent = Agent(
        name="DefaultBot",
        model=Gemini("1.5-flash"),
        instructions="You are a helpful assistant."
        # Uses defaults: temperature=0.7, max_tokens=4096, max_retries=3, stream=False
    )
    
    print(f"\nAgent: {default_agent.name}")
    print(f"Temperature: {default_agent.temperature} (default)")
    print(f"Max Tokens: {default_agent.max_tokens} (default)")
    print(f"Max Retries: {default_agent.max_retries} (default)")
    print(f"Stream: {default_agent.stream} (default)")
    
    # 3. Override at invocation time
    print("\n=== Invocation Examples ===")
    print("You can still override these at invocation time:")
    print("  await agent.invoke('Hello', temperature=0.5)")
    print("  await agent.invoke('Hello', max_tokens=100)")
    print("\nThis gives you flexibility while maintaining sensible defaults!")

if __name__ == "__main__":
    asyncio.run(main())
