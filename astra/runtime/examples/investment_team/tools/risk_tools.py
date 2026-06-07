"""
Risk Tools for Astra Framework.

Five tools for the Risk Officer agent.
Uses yfinance for market data + local portfolio state.
"""

from __future__ import annotations

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


try:
    import yfinance as yf
except ImportError as e:
    raise ImportError("`yfinance` not installed.") from e

from ._portfolio import get_holdings, load_portfolio


# 1. get_stock_beta
class BetaInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol")


class BetaOutput(BaseModel):
    result: dict = Field(description="Dict with beta value and interpretation")


beta_spec = ToolSpec(
    name="get_stock_beta",
    description="Get stock beta (market sensitivity) from yfinance. Beta > 1 = more volatile than market.",
    input_schema=BetaInput,
    output_schema=BetaOutput,
    examples=[{"input": {"symbol": "AAPL"}, "output": {"result": '{"beta": 1.24}'}}],
)


@bind_tool(beta_spec)
def get_stock_beta(input: BetaInput) -> BetaOutput:
    """Fetch beta from yfinance."""
    try:
        info = yf.Ticker(input.symbol).info or {}
        beta = info.get("beta")
        if beta is None:
            return BetaOutput(result={"symbol": input.symbol, "beta": "N/A"})

        if beta > 1.5:
            risk_level = "high"
        elif beta > 1.0:
            risk_level = "moderate"
        elif beta > 0.5:
            risk_level = "low"
        else:
            risk_level = "defensive"

        data = {"symbol": input.symbol, "beta": round(float(beta), 2), "risk_level": risk_level}
        return BetaOutput(result=data)
    except Exception as e:
        return BetaOutput(result={"error": f"Error: {e}"})


# 2. calculate_volatility
class VolatilityInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol")


class VolatilityOutput(BaseModel):
    result: dict = Field(description="Dict with annualized volatility and regime")


volatility_spec = ToolSpec(
    name="calculate_volatility",
    description="Calculate annualized volatility from daily returns (1 year). Classifies vol regime.",
    input_schema=VolatilityInput,
    output_schema=VolatilityOutput,
    examples=[{"input": {"symbol": "AAPL"}, "output": {"result": '{"annualized_vol": "28.5%"}'}}],
)


@bind_tool(volatility_spec)
def calculate_volatility(input: VolatilityInput) -> VolatilityOutput:
    """Calculate annualized volatility."""
    try:
        df = yf.Ticker(input.symbol).history(period="1y")
        if df.empty:
            return VolatilityOutput(result={"error": f"No data for {input.symbol}"})

        daily_returns = df["Close"].pct_change().dropna()
        std_val = daily_returns.std()
        vol = float(std_val) * (252**0.5) * 100  # type: ignore[arg-type]

        if vol > 40:
            regime = "very high"
        elif vol > 25:
            regime = "high"
        elif vol > 15:
            regime = "moderate"
        else:
            regime = "low"

        data = {"symbol": input.symbol, "annualized_vol": f"{vol:.1f}%", "regime": regime}
        return VolatilityOutput(result=data)
    except Exception as e:
        return VolatilityOutput(result={"error": f"Error: {e}"})


# 3. get_correlation_with_portfolio
class CorrelationInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol to check correlation against portfolio")


class CorrelationOutput(BaseModel):
    result: dict = Field(description="Dict with correlation values against top holdings")


correlation_spec = ToolSpec(
    name="get_correlation_with_portfolio",
    description="Calculate price correlation of a stock against current portfolio holdings (90-day).",
    input_schema=CorrelationInput,
    output_schema=CorrelationOutput,
    examples=[{"input": {"symbol": "GOOG"}, "output": {"result": '{"avg_correlation": 0.65}'}}],
)


@bind_tool(correlation_spec)
def get_correlation_with_portfolio(input: CorrelationInput) -> CorrelationOutput:
    """Calculate correlation against portfolio holdings."""
    try:
        holdings = get_holdings()
        if not holdings:
            return CorrelationOutput(result={"error": "No portfolio holdings found"})

        symbols = [h["symbol"] for h in holdings[:5]]  # Top 5 only
        all_symbols = [input.symbol] + symbols

        import pandas as pd

        prices = {}
        for sym in all_symbols:
            hist = yf.Ticker(sym).history(period="3mo")
            if not hist.empty:
                prices[sym] = hist["Close"]

        if input.symbol not in prices:
            return CorrelationOutput(result={"error": f"No price data for {input.symbol}"})

        df = pd.DataFrame(prices).pct_change().dropna()
        correlations = {}
        target_col = df[input.symbol]
        for sym in symbols:
            if sym in df.columns:
                corr_val = target_col.corr(df[sym])  # type: ignore[arg-type]
                correlations[sym] = round(float(corr_val), 3)  # type: ignore[arg-type]

        avg_corr = round(sum(correlations.values()) / len(correlations), 3) if correlations else 0

        if avg_corr > 0.7:
            diversification = "poor - high concentration risk"
        elif avg_corr > 0.4:
            diversification = "moderate"
        else:
            diversification = "good - adds diversification"

        data = {
            "symbol": input.symbol,
            "correlations": correlations,
            "avg_correlation": avg_corr,
            "diversification_benefit": diversification,
        }
        return CorrelationOutput(result=data)
    except Exception as e:
        return CorrelationOutput(result={"error": f"Error: {e}"})


# 4. estimate_drawdown_risk
class DrawdownInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol")


class DrawdownOutput(BaseModel):
    result: dict = Field(description="Dict with max drawdown and recovery info")


drawdown_spec = ToolSpec(
    name="estimate_drawdown_risk",
    description="Calculate maximum drawdown from 1-year price history. Shows worst peak-to-trough decline.",
    input_schema=DrawdownInput,
    output_schema=DrawdownOutput,
    examples=[{"input": {"symbol": "AAPL"}, "output": {"result": '{"max_drawdown": "-18.5%"}'}}],
)


@bind_tool(drawdown_spec)
def estimate_drawdown_risk(input: DrawdownInput) -> DrawdownOutput:
    """Calculate max drawdown from 1-year history."""
    try:
        df = yf.Ticker(input.symbol).history(period="1y")
        if df.empty:
            return DrawdownOutput(result={"error": f"No data for {input.symbol}"})

        close = df["Close"]
        peak = close.cummax()
        drawdown = (close - peak) / peak
        max_dd = float(drawdown.min()) * 100

        if max_dd > -10:
            risk = "low"
        elif max_dd > -20:
            risk = "moderate"
        elif max_dd > -30:
            risk = "high"
        else:
            risk = "severe"

        data = {
            "symbol": input.symbol,
            "max_drawdown": f"{max_dd:.1f}%",
            "drawdown_risk": risk,
            "current_from_peak": f"{float(drawdown.iloc[-1]) * 100:.1f}%",
        }
        return DrawdownOutput(result=data)
    except Exception as e:
        return DrawdownOutput(result={"error": f"Error: {e}"})


# 5. get_risk_portfolio_state
class PortfolioStateInput(BaseModel):
    pass


class PortfolioStateOutput(BaseModel):
    result: dict = Field(description="Dict with current portfolio state")


portfolio_state_spec = ToolSpec(
    name="get_risk_portfolio_state",
    description="Get current portfolio state for risk analysis: holdings, cash, NAV, sector weights.",
    input_schema=PortfolioStateInput,
    output_schema=PortfolioStateOutput,
    examples=[{"input": {}, "output": {"result": '{"nav": 10000000}'}}],
)


@bind_tool(portfolio_state_spec)
def get_risk_portfolio_state(input: PortfolioStateInput) -> PortfolioStateOutput:
    """Return current portfolio state."""
    try:
        portfolio = load_portfolio()
        positions = portfolio.get("positions", [])
        nav = portfolio.get("nav", 0)
        cash = portfolio.get("cash", 0)

        # Compute sector weights
        sectors: dict[str, float] = {}
        for pos in positions:
            sector = pos.get("sector", "Other")
            value = pos["shares"] * pos["avg_cost"]
            sectors[sector] = sectors.get(sector, 0) + value

        sector_weights = {s: f"{v / nav * 100:.1f}%" for s, v in sectors.items()} if nav else {}

        data = {
            "nav": nav,
            "cash": cash,
            "cash_pct": f"{cash / nav * 100:.1f}%" if nav else "N/A",
            "num_positions": len(positions),
            "positions": positions,
            "sector_weights": sector_weights,
        }
        return PortfolioStateOutput(result=data)
    except Exception as e:
        return PortfolioStateOutput(result={"error": f"Error: {e}"})


RISK_ALL_TOOLS = [
    get_stock_beta,
    calculate_volatility,
    get_correlation_with_portfolio,
    estimate_drawdown_risk,
    get_risk_portfolio_state,
]
