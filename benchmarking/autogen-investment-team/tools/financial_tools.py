"""
Financial Tools — CrewAI version.

Same compute as Agno/Astra — four yfinance-based tools for the Financial
Analyst agent. Only the binding shape differs: each function is wrapped
with CrewAI's `@tool` decorator.
"""

try:
    import yfinance as yf
except ImportError as e:
    raise ImportError("`yfinance` not installed. pip install yfinance") from e


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


def get_financial_statements(symbol: str) -> dict:
    """Get income statement and cash flow highlights for a stock.

    Args:
        symbol (str): Stock ticker symbol (e.g. AAPL, NVDA).
    """
    try:
        info = yf.Ticker(symbol).info or {}
        return {
            "symbol": symbol,
            "revenue": _fmt_num(_safe_get(info, "totalRevenue")),
            "net_income": _fmt_num(_safe_get(info, "netIncomeToCommon")),
            "gross_profit": _fmt_num(_safe_get(info, "grossProfits")),
            "operating_cashflow": _fmt_num(_safe_get(info, "operatingCashflow")),
            "free_cashflow": _fmt_num(_safe_get(info, "freeCashflow")),
            "ebitda": _fmt_num(_safe_get(info, "ebitda")),
        }
    except Exception as e:
        return {"error": f"Error fetching financial statements for {symbol}: {e}"}


def get_key_financial_metrics(symbol: str) -> dict:
    """Get profitability and efficiency metrics: margins, ROE, ROIC, debt ratios.

    Args:
        symbol (str): Stock ticker symbol (e.g. AAPL, NVDA).
    """
    try:
        info = yf.Ticker(symbol).info or {}
        return {
            "symbol": symbol,
            "gross_margin": _pct(_safe_get(info, "grossMargins")),
            "operating_margin": _pct(_safe_get(info, "operatingMargins")),
            "net_margin": _pct(_safe_get(info, "profitMargins")),
            "ebitda_margin": _pct(_safe_get(info, "ebitdaMargins")),
            "roe": _pct(_safe_get(info, "returnOnEquity")),
            "roa": _pct(_safe_get(info, "returnOnAssets")),
            "debt_to_equity": _safe_get(info, "debtToEquity"),
            "current_ratio": _safe_get(info, "currentRatio"),
        }
    except Exception as e:
        return {"error": f"Error fetching financial metrics for {symbol}: {e}"}


def get_growth_metrics(symbol: str) -> dict:
    """Get growth rates: revenue growth, earnings growth, and quarterly trends.

    Args:
        symbol (str): Stock ticker symbol (e.g. AAPL, NVDA).
    """
    try:
        info = yf.Ticker(symbol).info or {}
        return {
            "symbol": symbol,
            "revenue_growth": _pct(_safe_get(info, "revenueGrowth")),
            "earnings_growth": _pct(_safe_get(info, "earningsGrowth")),
            "earnings_quarterly_growth": _pct(_safe_get(info, "earningsQuarterlyGrowth")),
            "trailing_eps": _safe_get(info, "trailingEps"),
            "forward_eps": _safe_get(info, "forwardEps"),
            "peg_ratio": _safe_get(info, "pegRatio"),
        }
    except Exception as e:
        return {"error": f"Error fetching growth metrics for {symbol}: {e}"}


def get_balance_sheet_strength(symbol: str) -> dict:
    """Get balance sheet health: cash, debt, equity, debt-to-equity, book value.

    Args:
        symbol (str): Stock ticker symbol (e.g. AAPL, NVDA).
    """
    try:
        info = yf.Ticker(symbol).info or {}
        return {
            "symbol": symbol,
            "total_cash": _fmt_num(_safe_get(info, "totalCash")),
            "total_debt": _fmt_num(_safe_get(info, "totalDebt")),
            "net_cash": _fmt_num((info.get("totalCash") or 0) - (info.get("totalDebt") or 0)),
            "debt_to_equity": _safe_get(info, "debtToEquity"),
            "current_ratio": _safe_get(info, "currentRatio"),
            "book_value_per_share": _safe_get(info, "bookValue"),
        }
    except Exception as e:
        return {"error": f"Error fetching balance sheet for {symbol}: {e}"}


FINANCIAL_ALL_TOOLS = [
    get_financial_statements,
    get_key_financial_metrics,
    get_growth_metrics,
    get_balance_sheet_strength,
]
