"""
Market Tools for Finance Team.

Uses ToolSpec architecture with rich metadata in docstrings.
"""

import random

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


# GET STOCK PRICE TOOL
class GetStockPriceInput(BaseModel):
    """Input for getting stock price."""

    symbol: str = Field(description="Stock ticker symbol (e.g., AAPL, GOOGL)")


class GetStockPriceOutput(BaseModel):
    """Output from stock price lookup."""

    symbol: str = Field(description="Stock ticker symbol")
    price: float = Field(description="Current price in USD")
    change_percent: float = Field(description="Percentage change from previous close")
    currency: str = Field(description="Currency code (USD, EUR, etc.)")


# Define ToolSpec
GET_STOCK_PRICE_SPEC = ToolSpec(
    name="get_stock_price",
    description="Get the current stock price for a given symbol",
    input_schema=GetStockPriceInput,
    output_schema=GetStockPriceOutput,
    examples=[
        {
            "input": {"symbol": "AAPL"},
            "output": {"symbol": "AAPL", "price": 150.25, "change_percent": 2.3, "currency": "USD"},
        }
    ],
)


# Bind implementation
@bind_tool(GET_STOCK_PRICE_SPEC)
async def get_stock_price(input: GetStockPriceInput) -> GetStockPriceOutput:
    """
    Get the current stock price for a given symbol.

    Constraints:
    - Symbol must be a valid stock ticker
    - Returns simulated data for demo purposes
    - Real-time data integration in production

    Notes:
    - Use for market analysis and price tracking
    - Real-time data in production environments

    Tags: market, stocks, finance
    """
    # Simulated data
    price = round(random.uniform(100, 1000), 2)
    change = round(random.uniform(-5, 5), 2)

    return GetStockPriceOutput(
        symbol=input.symbol, price=price, change_percent=change, currency="USD"
    )


# GET MARKET NEWS TOOL
class GetMarketNewsInput(BaseModel):
    """Input for getting market news."""

    sector: str = Field(
        default="technology", description="Market sector: technology, finance, or healthcare"
    )


class GetMarketNewsOutput(BaseModel):
    """Output from market news lookup."""

    sector: str = Field(description="Sector queried")
    headlines: list[str] = Field(description="List of news headlines")


# Define ToolSpec
GET_MARKET_NEWS_SPEC = ToolSpec(
    name="get_market_news",
    description="Get the latest market news headlines for a specific sector",
    input_schema=GetMarketNewsInput,
    output_schema=GetMarketNewsOutput,
    examples=[
        {
            "input": {"sector": "technology"},
            "output": {
                "sector": "technology",
                "headlines": [
                    "Tech stocks rally on AI optimism",
                    "Chip shortage expected to ease by Q4",
                ],
            },
        }
    ],
)


# Bind implementation
@bind_tool(GET_MARKET_NEWS_SPEC)
async def get_market_news(input: GetMarketNewsInput) -> GetMarketNewsOutput:
    """
    Get the latest market news headlines for a specific sector.

    Constraints:
    - Sector must be one of: technology, finance, healthcare
    - Returns curated headlines for demo purposes

    Notes:
    - Use for sentiment analysis and market monitoring
    - Real news API integration in production

    Tags: market, news, sentiment
    """
    # News data
    news = {
        "technology": [
            "Tech stocks rally on AI optimism",
            "Chip shortage expected to ease by Q4",
            "New privacy regulations impact ad revenue",
        ],
        "finance": [
            "Fed signals interest rate pause",
            "Banking sector shows resilience amidst volatility",
            "Fintech startups disruption continues",
        ],
        "healthcare": [
            "New drug approval boosts biotech sector",
            "Healthcare costs rising above inflation",
            "Telehealth adoption stabilizes post-pandemic",
        ],
    }

    headlines = news.get(input.sector.lower(), ["No specific news found for this sector"])

    return GetMarketNewsOutput(sector=input.sector, headlines=headlines)
