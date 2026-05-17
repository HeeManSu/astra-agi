"""
Financial Tools for Astra Framework.

Four yfinance-based tools for the Financial Analyst agent.
Each returns a compact JSON snapshot — no raw DataFrames.
"""

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


try:
    import yfinance as yf
except ImportError as e:
    raise ImportError("`yfinance` not installed. Install with: pip install yfinance") from e


def _safe_get(info: dict, key: str, default="N/A"):
    val = info.get(key)
    return val if val is not None else default


def _pct(value) -> str:
    if value is None or value == "N/A":
        return "N/A"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_num(value) -> str:
    if value is None or value == "N/A":
        return "N/A"
    try:
        v = float(value)
        if abs(v) >= 1e9:
            return f"${v / 1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v / 1e6:.1f}M"
        return f"${v:,.0f}"
    except (TypeError, ValueError):
        return "N/A"


# 1. get_financial_statements
class FinancialStatementsInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol (e.g. AAPL, NVDA)")


class FinancialStatementsOutput(BaseModel):
    result: dict = Field(
        description="Dict with revenue, net income, operating CF for last 4 periods"
    )


financial_statements_spec = ToolSpec(
    name="get_financial_statements",
    description="Get income statement and cash flow highlights for a stock.",
    input_schema=FinancialStatementsInput,
    output_schema=FinancialStatementsOutput,
    examples=[{"input": {"symbol": "AAPL"}, "output": {"result": '{"revenue": "$383.3B"}'}}],
)


@bind_tool(financial_statements_spec)
def get_financial_statements(input: FinancialStatementsInput) -> FinancialStatementsOutput:
    """Fetch income statement + cash flow highlights from yfinance."""
    try:
        info = yf.Ticker(input.symbol).info or {}
        data = {
            "symbol": input.symbol,
            "revenue": _fmt_num(_safe_get(info, "totalRevenue")),
            "net_income": _fmt_num(_safe_get(info, "netIncomeToCommon")),
            "gross_profit": _fmt_num(_safe_get(info, "grossProfits")),
            "operating_cashflow": _fmt_num(_safe_get(info, "operatingCashflow")),
            "free_cashflow": _fmt_num(_safe_get(info, "freeCashflow")),
            "ebitda": _fmt_num(_safe_get(info, "ebitda")),
        }
        res = data
    except Exception as e:
        res = {"error": f"Error fetching financial statements for {input.symbol}: {e}"}
    return FinancialStatementsOutput(result=res)


# 2. get_key_financial_metrics
class KeyFinancialMetricsInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol (e.g. AAPL, NVDA)")


class KeyFinancialMetricsOutput(BaseModel):
    result: dict = Field(description="Dict with margins, ROIC, ROE, debt metrics")


key_financial_metrics_spec = ToolSpec(
    name="get_key_financial_metrics",
    description="Get profitability and efficiency metrics: margins, ROE, ROIC, debt ratios.",
    input_schema=KeyFinancialMetricsInput,
    output_schema=KeyFinancialMetricsOutput,
    examples=[{"input": {"symbol": "AAPL"}, "output": {"result": '{"gross_margin": "44.1%"}'}}],
)


@bind_tool(key_financial_metrics_spec)
def get_key_financial_metrics(input: KeyFinancialMetricsInput) -> KeyFinancialMetricsOutput:
    """Fetch profitability and efficiency metrics from yfinance."""
    try:
        info = yf.Ticker(input.symbol).info or {}
        data = {
            "symbol": input.symbol,
            "gross_margin": _pct(_safe_get(info, "grossMargins")),
            "operating_margin": _pct(_safe_get(info, "operatingMargins")),
            "net_margin": _pct(_safe_get(info, "profitMargins")),
            "ebitda_margin": _pct(_safe_get(info, "ebitdaMargins")),
            "roe": _pct(_safe_get(info, "returnOnEquity")),
            "roa": _pct(_safe_get(info, "returnOnAssets")),
            "debt_to_equity": _safe_get(info, "debtToEquity"),
            "current_ratio": _safe_get(info, "currentRatio"),
        }
        res = data
    except Exception as e:
        res = {"error": f"Error fetching financial metrics for {input.symbol}: {e}"}
    return KeyFinancialMetricsOutput(result=res)


# 3. get_growth_metrics
class GrowthMetricsInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol (e.g. AAPL, NVDA)")


class GrowthMetricsOutput(BaseModel):
    result: dict = Field(description="Dict with revenue growth, earnings growth rates")


growth_metrics_spec = ToolSpec(
    name="get_growth_metrics",
    description="Get growth rates: revenue growth, earnings growth, and quarterly trends.",
    input_schema=GrowthMetricsInput,
    output_schema=GrowthMetricsOutput,
    examples=[{"input": {"symbol": "NVDA"}, "output": {"result": '{"revenue_growth": "122.4%"}'}}],
)


@bind_tool(growth_metrics_spec)
def get_growth_metrics(input: GrowthMetricsInput) -> GrowthMetricsOutput:
    """Fetch growth metrics from yfinance."""
    try:
        info = yf.Ticker(input.symbol).info or {}
        data = {
            "symbol": input.symbol,
            "revenue_growth": _pct(_safe_get(info, "revenueGrowth")),
            "earnings_growth": _pct(_safe_get(info, "earningsGrowth")),
            "earnings_quarterly_growth": _pct(_safe_get(info, "earningsQuarterlyGrowth")),
            "trailing_eps": _safe_get(info, "trailingEps"),
            "forward_eps": _safe_get(info, "forwardEps"),
            "peg_ratio": _safe_get(info, "pegRatio"),
        }
        res = data
    except Exception as e:
        res = {"error": f"Error fetching growth metrics for {input.symbol}: {e}"}
    return GrowthMetricsOutput(result=res)


# 4. get_balance_sheet_strength
class BalanceSheetInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol (e.g. AAPL, NVDA)")


class BalanceSheetOutput(BaseModel):
    result: dict = Field(description="Dict with cash, debt, equity, and coverage ratios")


balance_sheet_spec = ToolSpec(
    name="get_balance_sheet_strength",
    description="Get balance sheet health: cash, debt, equity, debt-to-equity, book value.",
    input_schema=BalanceSheetInput,
    output_schema=BalanceSheetOutput,
    examples=[{"input": {"symbol": "AAPL"}, "output": {"result": '{"total_cash": "$29.97B"}'}}],
)


@bind_tool(balance_sheet_spec)
def get_balance_sheet_strength(input: BalanceSheetInput) -> BalanceSheetOutput:
    """Fetch balance sheet strength from yfinance."""
    try:
        info = yf.Ticker(input.symbol).info or {}
        data = {
            "symbol": input.symbol,
            "total_cash": _fmt_num(_safe_get(info, "totalCash")),
            "total_debt": _fmt_num(_safe_get(info, "totalDebt")),
            "net_cash": _fmt_num((info.get("totalCash") or 0) - (info.get("totalDebt") or 0)),
            "debt_to_equity": _safe_get(info, "debtToEquity"),
            "current_ratio": _safe_get(info, "currentRatio"),
            "book_value_per_share": _safe_get(info, "bookValue"),
        }
        res = data
    except Exception as e:
        res = {"error": f"Error fetching balance sheet for {input.symbol}: {e}"}
    return BalanceSheetOutput(result=res)


# Export
FINANCIAL_ALL_TOOLS = [
    get_financial_statements,
    get_key_financial_metrics,
    get_growth_metrics,
    get_balance_sheet_strength,
]
