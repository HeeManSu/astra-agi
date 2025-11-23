import pytest
from framework import Agent, tool

# Define tools
@tool
def get_stock_price(symbol: str) -> str:
    """Get stock price."""
    return f"{symbol}: $100"

@tool
def convert_currency(amount: float, from_curr: str, to_curr: str) -> str:
    """Convert currency."""
    return f"{amount} {from_curr} = {amount * 0.92} {to_curr}"

@tool
def get_market_news(topic: str = "stocks") -> str:
    """Get market news."""
    return f"News for {topic}"

@tool
def get_company_info(symbol: str) -> str:
    """Get company info."""
    return f"Info for {symbol}"

@pytest.mark.benchmark
def test_complex_agent_initialization_benchmark(benchmark):
    """Benchmark complex agent initialization with 4 tools."""
    def init_complex_agent():
        return Agent(
            model="google/gemini-1.5-flash",
            tools=[get_stock_price, convert_currency, get_market_news, get_company_info],
            instructions="You are a helpful finance assistant."
        )
    
    benchmark(init_complex_agent)

@pytest.mark.benchmark
def test_complex_agent_with_10_tools_benchmark(benchmark):
    """Benchmark agent initialization with 10 tools."""
    # Create 10 tools
    tools = [get_stock_price, convert_currency, get_market_news, get_company_info]
    
    # Add 6 more simple tools
    for i in range(6):
        @tool
        def dummy_tool(x: int) -> int:
            return x
        tools.append(dummy_tool)
    
    def init_agent_with_many_tools():
        return Agent(
            model="google/gemini-1.5-flash",
            tools=tools,
        )
    
    benchmark(init_agent_with_many_tools)
