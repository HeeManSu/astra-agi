import asyncio
from framework import Agent, tool

# --- Tools ---

@tool
def get_stock_price(symbol: str) -> str:
    """Get current stock price for a given symbol."""
    # Mock data
    prices = {"AAPL": 175.50, "GOOGL": 142.25, "MSFT": 378.90}
    price = prices.get(symbol.upper(), 100.00)
    return f"{symbol.upper()}: ${price:.2f}"

@tool
def convert_currency(amount: float, from_curr: str, to_curr: str) -> str:
    """Convert amount from one currency to another."""
    rate = 0.92 if to_curr.upper() == "EUR" else 1.1
    return f"{amount} {from_curr} = {amount * rate:.2f} {to_curr}"

@tool
def get_market_news(topic: str = "stocks") -> str:
    """Get latest market news."""
    return f"Latest news for {topic}: Market is bullish."

@tool
def get_company_info(symbol: str) -> str:
    """Get company information."""
    return f"Info for {symbol}: Tech giant."

# --- Agent ---

# Complex agent with multiple tools using minimal init
agent = Agent(
    model="google/gemini-1.5-flash",
    tools=[get_stock_price, convert_currency, get_market_news, get_company_info],
    instructions="You are a helpful finance assistant."
)

async def main():
    print("=== Complex Finance Agent Example ===\n")
    print(f"Agent Name: {agent.name}")
    print(f"Agent Model: {agent.model}")
    print(f"Agent Instructions: {agent.instructions}")
    print(f"\nTools ({len(agent.tools)}):")
    for tool in agent.tools:
        print(f"  - {tool.name}: {tool.description}")
    
    print(f"\nAgent initialized successfully!")
    print(f"Agent ID: {agent.id}")
    print(f"Context ready: {agent.context is not None}")
    
    # Note: To actually invoke the agent, set GOOGLE_API_KEY environment variable
    # Example: response = await agent.invoke("What is AAPL price?")

if __name__ == "__main__":
    asyncio.run(main())
