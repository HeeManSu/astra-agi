"""
Risk Tools — Agno version.

Five tools for the Risk Officer agent.
Same logic as Astra, plain functions.
"""

from __future__ import annotations

try:
    import yfinance as yf
except ImportError as e:
    raise ImportError("`yfinance` not installed.") from e

from ._portfolio import get_holdings, load_portfolio


def get_stock_beta(symbol: str) -> dict:
    """Get stock beta (market sensitivity) from yfinance. Beta > 1 = more volatile than market.

    Args:
        symbol (str): Stock ticker symbol.
    """
    try:
        info = yf.Ticker(symbol).info or {}
        beta = info.get("beta")
        if beta is None:
            return {"symbol": symbol, "beta": "N/A"}

        if beta > 1.5:
            risk_level = "high"
        elif beta > 1.0:
            risk_level = "moderate"
        elif beta > 0.5:
            risk_level = "low"
        else:
            risk_level = "defensive"

        return {"symbol": symbol, "beta": round(float(beta), 2), "risk_level": risk_level}
    except Exception as e:
        return {"error": f"Error: {e}"}


def calculate_volatility(symbol: str) -> dict:
    """Calculate annualized volatility from daily returns (1 year). Classifies vol regime.

    Args:
        symbol (str): Stock ticker symbol.
    """
    try:
        df = yf.Ticker(symbol).history(period="1y")
        if df.empty:
            return {"error": f"No data for {symbol}"}

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

        return {"symbol": symbol, "annualized_vol": f"{vol:.1f}%", "regime": regime}
    except Exception as e:
        return {"error": f"Error: {e}"}


def get_correlation_with_portfolio(symbol: str) -> dict:
    """Calculate price correlation of a stock against current portfolio holdings (90-day).

    Args:
        symbol (str): Stock ticker symbol to check correlation against portfolio.
    """
    try:
        holdings = get_holdings()
        if not holdings:
            return {"error": "No portfolio holdings found"}

        symbols = [h["symbol"] for h in holdings[:5]]  # Top 5 only
        all_symbols = [symbol] + symbols

        import pandas as pd

        prices = {}
        for sym in all_symbols:
            hist = yf.Ticker(sym).history(period="3mo")
            if not hist.empty:
                prices[sym] = hist["Close"]

        if symbol not in prices:
            return {"error": f"No price data for {symbol}"}

        df = pd.DataFrame(prices).pct_change().dropna()
        correlations = {}
        target_col = df[symbol]
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

        return {
            "symbol": symbol,
            "correlations": correlations,
            "avg_correlation": avg_corr,
            "diversification_benefit": diversification,
        }
    except Exception as e:
        return {"error": f"Error: {e}"}


def estimate_drawdown_risk(symbol: str) -> dict:
    """Calculate maximum drawdown from 1-year price history. Shows worst peak-to-trough decline.

    Args:
        symbol (str): Stock ticker symbol.
    """
    try:
        df = yf.Ticker(symbol).history(period="1y")
        if df.empty:
            return {"error": f"No data for {symbol}"}

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

        return {
            "symbol": symbol,
            "max_drawdown": f"{max_dd:.1f}%",
            "drawdown_risk": risk,
            "current_from_peak": f"{float(drawdown.iloc[-1]) * 100:.1f}%",
        }
    except Exception as e:
        return {"error": f"Error: {e}"}


def get_risk_portfolio_state() -> dict:
    """Get current portfolio state for risk analysis: holdings, cash, NAV, sector weights.

    Args:
        No arguments required.
    """
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

        return {
            "nav": nav,
            "cash": cash,
            "cash_pct": f"{cash / nav * 100:.1f}%" if nav else "N/A",
            "num_positions": len(positions),
            "positions": positions,
            "sector_weights": sector_weights,
        }
    except Exception as e:
        return {"error": f"Error: {e}"}


RISK_ALL_TOOLS = [
    get_stock_beta,
    calculate_volatility,
    get_correlation_with_portfolio,
    estimate_drawdown_risk,
    get_risk_portfolio_state,
]
