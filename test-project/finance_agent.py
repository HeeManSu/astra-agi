"""
Finance Agent Example - Using Astra Embedded Runtime

A simple finance assistant that can provide stock information and financial advice.
"""

import asyncio
import os

from astra import Agent, Gemini, tool


# Define finance tools
@tool
def get_stock_price(symbol: str) -> str:
    """Get the current stock price for a given symbol."""
    # Mock data for demonstration
    prices = {
        "AAPL": 185.50,
        "GOOGL": 141.25,
        "MSFT": 378.90,
        "AMZN": 178.35,
        "TSLA": 248.75,
        "NVDA": 495.20,
    }
    price = prices.get(symbol.upper())
    if price:
        return f"The current price of {symbol.upper()} is ${price:.2f}"
    return f"Stock symbol {symbol} not found. Try AAPL, GOOGL, MSFT, AMZN, TSLA, or NVDA."


@tool
def get_portfolio_value(stocks: str) -> str:
    """
    Calculate the total portfolio value.

    Args:
        stocks: Comma-separated list of stock:quantity pairs (e.g., "AAPL:10,GOOGL:5")
    """
    prices = {
        "AAPL": 185.50,
        "GOOGL": 141.25,
        "MSFT": 378.90,
        "AMZN": 178.35,
        "TSLA": 248.75,
        "NVDA": 495.20,
    }

    total = 0.0
    breakdown: list[str] = []

    for item in stocks.split(","):
        parts = item.strip().split(":")
        if len(parts) == 2:
            symbol, qty = parts[0].upper(), int(parts[1])
            price = prices.get(symbol, 0)
            value = price * qty
            total += value
            breakdown.append(f"  {symbol}: {qty} shares × ${price:.2f} = ${value:.2f}")

    result = "Portfolio Breakdown:\n" + "\n".join(breakdown)
    result += f"\n\nTotal Portfolio Value: ${total:.2f}"
    return result


@tool
def get_market_news(topic: str) -> str:
    """Get the latest market news on a specific topic."""
    # Mock news for demonstration
    news = {
        "tech": "Tech stocks rally as AI investments continue to drive growth. NVIDIA hits new highs.",
        "crypto": "Bitcoin stabilizes around $45,000 as institutional adoption increases.",
        "energy": "Oil prices rise amid OPEC+ production cut discussions.",
        "healthcare": "Healthcare sector sees gains as pharmaceutical companies report strong earnings.",
    }
    return news.get(
        topic.lower(),
        f"No specific news found for '{topic}'. Try: tech, crypto, energy, healthcare",
    )


async def main():
    # Ensure you have GOOGLE_API_KEY set in environment
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️  Please set GOOGLE_API_KEY environment variable")
        print("   export GOOGLE_API_KEY='your-api-key-here'")
        return

    # Create the finance agent
    agent = Agent(
        name="FinanceBot",
        model=Gemini("gemini-2.5-flash"),
        instructions="""You are a helpful Finance Assistant named FinanceBot.

Your capabilities:
- Get current stock prices for major tech companies
- Calculate portfolio values
- Provide latest market news

Always be helpful and provide clear, concise financial information.
When asked about stocks, use the available tools to get real data.
Format monetary values clearly with dollar signs and appropriate decimals.""",
        tools=[get_stock_price, get_portfolio_value, get_market_news],
    )

    print("=" * 60)
    print("🤖 FinanceBot - Your AI Finance Assistant")
    print("=" * 60)
    print("\nAvailable commands:")
    print("  - Ask about stock prices (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA)")
    print("  - Calculate portfolio value")
    print("  - Get market news (tech, crypto, energy, healthcare)")
    print("  - Type 'quit' to exit")
    print("-" * 60)

    # Interactive chat loop
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye! Happy investing!")
                break

            print("\n🤖 FinanceBot: ", end="", flush=True)
            response = await agent.invoke(user_input)
            print(response)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
