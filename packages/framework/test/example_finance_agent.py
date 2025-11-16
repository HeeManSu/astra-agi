"""
Finance Agent Example - Complex example with async and sync tools.

Demonstrates:
- Multiple tools (3-4 tools)
- Mix of async and sync tools
- Real API calls (using free APIs)
- Direct agent usage
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework import Agent, tool

# Finance Tools

@tool
async def get_stock_price(symbol: str) -> str:
    """Get current stock price for a given symbol (e.g., AAPL, GOOGL, MSFT)."""
    # Mock stock prices (in production, use real API like Alpha Vantage, Yahoo Finance, etc.)
    stock_prices = {
        "AAPL": {"price": 175.50, "change": 2.30, "change_percent": 1.33},
        "GOOGL": {"price": 142.25, "change": -1.15, "change_percent": -0.80},
        "MSFT": {"price": 378.90, "change": 5.20, "change_percent": 1.39},
        "TSLA": {"price": 248.75, "change": -3.45, "change_percent": -1.37},
        "AMZN": {"price": 145.60, "change": 1.80, "change_percent": 1.25},
    }
    
    symbol_upper = symbol.upper()
    if symbol_upper in stock_prices:
        data = stock_prices[symbol_upper]
        return f"{symbol_upper}: ${data['price']:.2f} ({data['change']:+.2f}, {data['change_percent']:+.2f}%)"
    
    return f"Stock price for {symbol} not available. Available symbols: {', '.join(stock_prices.keys())}"


@tool
async def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert amount from one currency to another (e.g., USD to EUR)."""
    # Mock exchange rates (in production, use real API like ExchangeRate-API, Fixer.io, etc.)
    exchange_rates = {
        "USD": {"EUR": 0.92, "GBP": 0.79, "JPY": 150.25, "INR": 83.15},
        "EUR": {"USD": 1.09, "GBP": 0.86, "JPY": 163.50, "INR": 90.50},
        "GBP": {"USD": 1.27, "EUR": 1.16, "JPY": 190.00, "INR": 105.20},
    }
    
    from_curr = from_currency.upper()
    to_curr = to_currency.upper()
    
    if from_curr == to_curr:
        return f"{amount:.2f} {from_curr} = {amount:.2f} {to_curr}"
    
    if from_curr in exchange_rates and to_curr in exchange_rates[from_curr]:
        rate = exchange_rates[from_curr][to_curr]
        converted = amount * rate
        return f"{amount:.2f} {from_curr} = {converted:.2f} {to_curr} (rate: {rate:.4f})"
    
    return f"Exchange rate not available for {from_curr} to {to_curr}"


@tool
async def get_market_news(topic: str = "stocks") -> str:
    """Get latest market news for a given topic (stocks, crypto, economy, etc.)."""
    # Mock news (in production, use NewsAPI, Alpha Vantage News, etc.)
    news_items = {
        "stocks": [
            "Tech stocks rally on strong earnings reports",
            "Federal Reserve hints at potential rate cuts",
            "AI companies see surge in investor interest"
        ],
        "crypto": [
            "Bitcoin reaches new monthly high",
            "Ethereum upgrade improves transaction speeds",
            "Regulatory clarity boosts crypto market confidence"
        ],
        "economy": [
            "GDP growth exceeds expectations",
            "Unemployment rate drops to historic low",
            "Inflation shows signs of cooling"
        ]
    }
    
    topic_lower = topic.lower()
    if topic_lower in news_items:
        news = news_items[topic_lower]
        return f"Latest {topic} news:\n" + "\n".join(f"- {item}" for item in news)
    
    return f"News not available for topic '{topic}'. Available topics: {', '.join(news_items.keys())}"


@tool
def get_company_info(symbol: str) -> str:
    """Get company information including sector, market cap, and description."""
    # Mock company data (in production, use real API like Alpha Vantage, Yahoo Finance, etc.)
    companies = {
        "AAPL": {
            "name": "Apple Inc.",
            "sector": "Technology",
            "market_cap": "2.8T",
            "description": "Designs and manufactures consumer electronics, software, and online services."
        },
        "GOOGL": {
            "name": "Alphabet Inc.",
            "sector": "Technology",
            "market_cap": "1.7T",
            "description": "Provides internet-related products and services including search, cloud computing, and advertising."
        },
        "MSFT": {
            "name": "Microsoft Corporation",
            "sector": "Technology",
            "market_cap": "2.9T",
            "description": "Develops, licenses, and supports software, services, devices, and solutions."
        },
        "TSLA": {
            "name": "Tesla, Inc.",
            "sector": "Automotive",
            "market_cap": "790B",
            "description": "Designs, develops, manufactures, and sells electric vehicles and energy storage systems."
        }
    }
    
    symbol_upper = symbol.upper()
    if symbol_upper in companies:
        company = companies[symbol_upper]
        return (
            f"{company['name']} ({symbol_upper})\n"
            f"Sector: {company['sector']}\n"
            f"Market Cap: ${company['market_cap']}\n"
            f"Description: {company['description']}"
        )
    
    return f"Company info not available for {symbol}. Available symbols: {', '.join(companies.keys())}"


async def main():
    """Run finance agent example."""
    
    print("=== Finance Agent Example ===\n")
    
    # Create finance agent with multiple tools
    finance_agent = Agent(
        id="finance-agent",
        name="Finance Agent",
        description="An agent that provides financial information including stock prices, currency conversion, market news, and company information",
        instructions=(
            'You are a helpful finance assistant. '
            'Use the available tools to provide accurate financial information. '
            'When users ask about stocks, use get_stock_price. '
            'For currency conversion, use convert_currency. '
            'For market updates, use get_market_news. '
            'For company details, use get_company_info. '
            'Always be precise and include relevant details.'
        ),
        model={
            "provider": "google",
            "model": "gemini-2.5-flash",
            "api_key": "AIzaSyBdlhWIITmvhQLunWUTv9t9-V4nwvo90I8"
        },
        tools=[
            get_stock_price,
            convert_currency,
            get_market_news,
            get_company_info
        ]
    )
    
    print(f"Created agent: {finance_agent}\n")
    
    await finance_agent.startup()
    
    # Test queries
    queries = [
        "What is the current price of AAPL?",
        "Convert 1000 USD to EUR",
        "Get the latest stock market news",
        "Tell me about Microsoft (MSFT)"
    ]
    
    responses = []
    
    for query in queries:
        print(f"Query: {query}")
        response = await finance_agent.invoke(query)
        print(f"Response: {response['content']}\n")
        
        responses.append({
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
    
    # Save responses
    output_file = Path(__file__).parent.parent / "jsons" / "finance_agent_responses.json"
    with open(output_file, 'w') as f:
        json.dump({
            "agent_id": finance_agent.id,
            "agent_name": finance_agent.name,
            "timestamp": datetime.now().isoformat(),
            "responses": responses
        }, f, indent=2, default=str)
    
    print(f"Responses saved to: {output_file}\n")
    
    await finance_agent.shutdown()
    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())

