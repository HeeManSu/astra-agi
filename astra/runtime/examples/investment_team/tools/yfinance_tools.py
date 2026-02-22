"""
YFinance Tools for Astra Framework.

Wraps yfinance library as Astra Tool instances.
Matches all 9 Agno YFinanceTools methods to perfectly replicate token usage in the LLM context.
"""

import json

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field
import yfinance as yf


# --- 1. get_current_stock_price ---
class GetCurrentStockPriceInput(BaseModel):
    symbol: str = Field(description="The stock symbol")


class GetCurrentStockPriceOutput(BaseModel):
    result: str


get_current_stock_price_spec = ToolSpec(
    name="get_current_stock_price",
    description="Use this function to get the current stock price for a given symbol.",
    input_schema=GetCurrentStockPriceInput,
    output_schema=GetCurrentStockPriceOutput,
)


@bind_tool(get_current_stock_price_spec)
def get_current_stock_price(input: GetCurrentStockPriceInput) -> GetCurrentStockPriceOutput:
    """Get current stock price for a given symbol."""
    try:
        stock = yf.Ticker(input.symbol)
        price = stock.info.get("regularMarketPrice", stock.info.get("currentPrice"))
        res = f"{price:.4f}" if price else f"Could not fetch current price for {input.symbol}"
    except Exception as e:
        res = f"Error fetching current price for {input.symbol}: {e}"
    return GetCurrentStockPriceOutput(result=res)


# --- 2. get_company_info ---
class GetCompanyInfoInput(BaseModel):
    symbol: str = Field(description="The stock symbol")


class GetCompanyInfoOutput(BaseModel):
    result: str


get_company_info_spec = ToolSpec(
    name="get_company_info",
    description="Use this function to get company information and overview for a given stock symbol.",
    input_schema=GetCompanyInfoInput,
    output_schema=GetCompanyInfoOutput,
)


@bind_tool(get_company_info_spec)
def get_company_info(input: GetCompanyInfoInput) -> GetCompanyInfoOutput:
    try:
        info = yf.Ticker(input.symbol).info
        if info is None:
            return GetCompanyInfoOutput(result=f"Could not fetch company info for {input.symbol}")

        cleaned = {
            "Name": info.get("shortName"),
            "Symbol": info.get("symbol"),
            "Current Stock Price": f"{info.get('regularMarketPrice', info.get('currentPrice'))} {info.get('currency', 'USD')}",
            "Market Cap": f"{info.get('marketCap', info.get('enterpriseValue'))} {info.get('currency', 'USD')}",
            "Sector": info.get("sector"),
            "Industry": info.get("industry"),
            "Address": info.get("address1"),
            "City": info.get("city"),
            "State": info.get("state"),
            "Zip": info.get("zip"),
            "Country": info.get("country"),
            "EPS": info.get("trailingEps"),
            "P/E Ratio": info.get("trailingPE"),
            "52 Week Low": info.get("fiftyTwoWeekLow"),
            "52 Week High": info.get("fiftyTwoWeekHigh"),
            "50 Day Average": info.get("fiftyDayAverage"),
            "200 Day Average": info.get("twoHundredDayAverage"),
            "Website": info.get("website"),
            "Summary": info.get("longBusinessSummary"),
            "Analyst Recommendation": info.get("recommendationKey"),
            "Number Of Analyst Opinions": info.get("numberOfAnalystOpinions"),
            "Employees": info.get("fullTimeEmployees"),
            "Total Cash": info.get("totalCash"),
            "Free Cash flow": info.get("freeCashflow"),
            "Operating Cash flow": info.get("operatingCashflow"),
            "EBITDA": info.get("ebitda"),
            "Revenue Growth": info.get("revenueGrowth"),
            "Gross Margins": info.get("grossMargins"),
            "Ebitda Margins": info.get("ebitdaMargins"),
        }
        res = json.dumps(cleaned, indent=2)
    except Exception as e:
        res = f"Error fetching company profile for {input.symbol}: {e}"
    return GetCompanyInfoOutput(result=res)


# --- 3. get_historical_stock_prices ---
class GetHistoricalStockPricesInput(BaseModel):
    symbol: str = Field(description="The stock symbol")
    period: str = Field(
        default="1mo", description="The period for which to retrieve historical prices"
    )
    interval: str = Field(default="1d", description="The interval between data points")


class GetHistoricalStockPricesOutput(BaseModel):
    result: str


get_historical_stock_prices_spec = ToolSpec(
    name="get_historical_stock_prices",
    description="Use this function to get the historical stock price for a given symbol.",
    input_schema=GetHistoricalStockPricesInput,
    output_schema=GetHistoricalStockPricesOutput,
)


@bind_tool(get_historical_stock_prices_spec)
def get_historical_stock_prices(
    input: GetHistoricalStockPricesInput,
) -> GetHistoricalStockPricesOutput:
    try:
        stock = yf.Ticker(input.symbol)
        hist = stock.history(period=input.period, interval=input.interval)
        res = hist.to_json(orient="index") or "{}"
    except Exception as e:
        res = f"Error fetching historical prices for {input.symbol}: {e}"
    return GetHistoricalStockPricesOutput(result=res)


# --- 4. get_stock_fundamentals ---
class GetStockFundamentalsInput(BaseModel):
    symbol: str = Field(description="The stock symbol")


class GetStockFundamentalsOutput(BaseModel):
    result: str


get_stock_fundamentals_spec = ToolSpec(
    name="get_stock_fundamentals",
    description="Use this function to get fundamental data for a given stock symbol yfinance API.",
    input_schema=GetStockFundamentalsInput,
    output_schema=GetStockFundamentalsOutput,
)


@bind_tool(get_stock_fundamentals_spec)
def get_stock_fundamentals(input: GetStockFundamentalsInput) -> GetStockFundamentalsOutput:
    try:
        info = yf.Ticker(input.symbol).info
        fundamentals = {
            "symbol": input.symbol,
            "company_name": info.get("longName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap": info.get("marketCap", "N/A"),
            "pe_ratio": info.get("forwardPE", "N/A"),
            "pb_ratio": info.get("priceToBook", "N/A"),
            "dividend_yield": info.get("dividendYield", "N/A"),
            "eps": info.get("trailingEps", "N/A"),
            "beta": info.get("beta", "N/A"),
            "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
        }
        res = json.dumps(fundamentals, indent=2)
    except Exception as e:
        res = f"Error getting fundamentals for {input.symbol}: {e}"
    return GetStockFundamentalsOutput(result=res)


# --- 5. get_income_statements ---
class GetIncomeStatementsInput(BaseModel):
    symbol: str = Field(description="The stock symbol")


class GetIncomeStatementsOutput(BaseModel):
    result: str


get_income_statements_spec = ToolSpec(
    name="get_income_statements",
    description="Use this function to get income statements for a given stock symbol.",
    input_schema=GetIncomeStatementsInput,
    output_schema=GetIncomeStatementsOutput,
)


@bind_tool(get_income_statements_spec)
def get_income_statements(input: GetIncomeStatementsInput) -> GetIncomeStatementsOutput:
    try:
        import pandas as pd

        financials = yf.Ticker(input.symbol).financials
        if isinstance(financials, pd.DataFrame):
            res = financials.to_json(orient="index") or "{}"
        else:
            res = json.dumps(financials, indent=2) if financials else "{}"
    except Exception as e:
        res = f"Error fetching income statements for {input.symbol}: {e}"
    return GetIncomeStatementsOutput(result=res)


# --- 6. get_key_financial_ratios ---
class GetKeyFinancialRatiosInput(BaseModel):
    symbol: str = Field(description="The stock symbol")


class GetKeyFinancialRatiosOutput(BaseModel):
    result: str


get_key_financial_ratios_spec = ToolSpec(
    name="get_key_financial_ratios",
    description="Use this function to get key financial ratios for a given stock symbol.",
    input_schema=GetKeyFinancialRatiosInput,
    output_schema=GetKeyFinancialRatiosOutput,
)


@bind_tool(get_key_financial_ratios_spec)
def get_key_financial_ratios(input: GetKeyFinancialRatiosInput) -> GetKeyFinancialRatiosOutput:
    try:
        res = json.dumps(yf.Ticker(input.symbol).info, indent=2)
    except Exception as e:
        res = f"Error fetching key financial ratios: {e}"
    return GetKeyFinancialRatiosOutput(result=res)


# --- 7. get_analyst_recommendations ---
class GetAnalystRecommendationsInput(BaseModel):
    symbol: str = Field(description="The stock symbol")


class GetAnalystRecommendationsOutput(BaseModel):
    result: str


get_analyst_recommendations_spec = ToolSpec(
    name="get_analyst_recommendations",
    description="Use this function to get analyst recommendations for a given stock symbol.",
    input_schema=GetAnalystRecommendationsInput,
    output_schema=GetAnalystRecommendationsOutput,
)


@bind_tool(get_analyst_recommendations_spec)
def get_analyst_recommendations(
    input: GetAnalystRecommendationsInput,
) -> GetAnalystRecommendationsOutput:
    try:
        import pandas as pd

        recs = yf.Ticker(input.symbol).recommendations
        if isinstance(recs, pd.DataFrame):
            res = recs.to_json(orient="index") or "{}"
        else:
            res = json.dumps(recs, indent=2) if recs else "{}"
    except Exception as e:
        res = f"Error fetching analyst recommendations: {e}"
    return GetAnalystRecommendationsOutput(result=res)


# --- 8. get_company_news ---
class GetCompanyNewsInput(BaseModel):
    symbol: str = Field(description="The stock symbol")
    num_stories: int = Field(default=3, description="The number of news stories to return")


class GetCompanyNewsOutput(BaseModel):
    result: str


get_company_news_spec = ToolSpec(
    name="get_company_news",
    description="Use this function to get company news and press releases for a given stock symbol.",
    input_schema=GetCompanyNewsInput,
    output_schema=GetCompanyNewsOutput,
)


@bind_tool(get_company_news_spec)
def get_company_news(input: GetCompanyNewsInput) -> GetCompanyNewsOutput:
    try:
        news = yf.Ticker(input.symbol).news
        res = json.dumps(news[: input.num_stories], indent=2)
    except Exception as e:
        res = f"Error fetching news for {input.symbol}: {e}"
    return GetCompanyNewsOutput(result=res)


# --- 9. get_technical_indicators ---
class GetTechnicalIndicatorsInput(BaseModel):
    symbol: str = Field(description="The stock symbol")
    period: str = Field(
        default="3mo", description="The time period for which to retrieve indicators"
    )


class GetTechnicalIndicatorsOutput(BaseModel):
    result: str


get_technical_indicators_spec = ToolSpec(
    name="get_technical_indicators",
    description="Use this function to get technical indicators for a given stock symbol.",
    input_schema=GetTechnicalIndicatorsInput,
    output_schema=GetTechnicalIndicatorsOutput,
)


@bind_tool(get_technical_indicators_spec)
def get_technical_indicators(input: GetTechnicalIndicatorsInput) -> GetTechnicalIndicatorsOutput:
    try:
        res = yf.Ticker(input.symbol).history(period=input.period).to_json(orient="index") or "{}"
    except Exception as e:
        res = f"Error fetching indicators for {input.symbol}: {e}"
    return GetTechnicalIndicatorsOutput(result=res)


YFINANCE_ALL_TOOLS = [
    get_current_stock_price,
    get_company_info,
    get_historical_stock_prices,
    get_stock_fundamentals,
    get_income_statements,
    get_key_financial_ratios,
    get_analyst_recommendations,
    get_company_news,
    get_technical_indicators,
]
