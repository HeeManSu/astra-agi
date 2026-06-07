"""
Portfolio Tools — Agno version.

Four tools for the Portfolio Manager agent.
Same logic as Astra, plain functions.
"""

from __future__ import annotations

try:
    import yfinance as yf
except ImportError as e:
    raise ImportError("`yfinance` not installed.") from e

from ._portfolio import (
    get_cash as _get_cash,
    get_holdings,
    get_nav,
    load_portfolio,
)


def get_portfolio_state() -> dict:
    """Get current portfolio: holdings, cash, NAV, sector weights, position sizes.

    Args:
        No arguments required.
    """
    try:
        portfolio = load_portfolio()
        positions = portfolio.get("positions", [])
        nav = portfolio.get("nav", 0)
        cash = portfolio.get("cash", 0)
        enriched = []
        for pos in positions:
            value = pos["shares"] * pos["avg_cost"]
            enriched.append(
                {
                    **pos,
                    "market_value": round(value, 2),
                    "weight": f"{value / nav * 100:.1f}%" if nav else "N/A",
                }
            )
        return {
            "nav": nav,
            "cash": cash,
            "cash_pct": f"{cash / nav * 100:.1f}%" if nav else "N/A",
            "num_positions": len(positions),
            "max_positions": 15,
            "positions": enriched,
        }
    except Exception as e:
        return {"error": f"Error: {e}"}


def calculate_portfolio_beta() -> dict:
    """Calculate portfolio-weighted beta using current holdings and yfinance betas.

    Args:
        No arguments required.
    """
    try:
        holdings = get_holdings()
        nav = get_nav()
        if not holdings or not nav:
            return {"error": "No holdings"}
        weighted_beta = 0.0
        details = []
        for pos in holdings:
            info = yf.Ticker(pos["symbol"]).info or {}
            beta = info.get("beta", 1.0)
            value = pos["shares"] * pos["avg_cost"]
            weight = value / nav
            weighted_beta += float(beta or 1.0) * weight
            details.append(
                {
                    "symbol": pos["symbol"],
                    "beta": round(float(beta or 1.0), 2),
                    "weight": f"{weight * 100:.1f}%",
                }
            )
        return {
            "portfolio_beta": round(weighted_beta, 3),
            "target_range": "0.8 - 1.2",
            "in_range": 0.8 <= weighted_beta <= 1.2,
            "details": details,
        }
    except Exception as e:
        return {"error": f"Error: {e}"}


def sector_exposure() -> dict:
    """Get sector exposure breakdown and check against sector cap limits.

    Args:
        No arguments required.
    """
    try:
        holdings = get_holdings()
        nav = get_nav()
        if not holdings or not nav:
            return {"error": "No holdings"}
        sector_cap = 0.30
        sectors: dict[str, float] = {}
        for pos in holdings:
            sector = pos.get("sector", "Other")
            value = pos["shares"] * pos["avg_cost"]
            sectors[sector] = sectors.get(sector, 0) + value
        exposure = {}
        violations = []
        for sector, value in sorted(sectors.items(), key=lambda x: -x[1]):
            pct = value / nav * 100
            exposure[sector] = {
                "value": round(value, 2),
                "weight": f"{pct:.1f}%",
                "cap": f"{sector_cap * 100:.0f}%",
                "compliant": pct <= sector_cap * 100,
            }
            if pct > sector_cap * 100:
                violations.append(sector)
        return {"sectors": exposure, "violations": violations, "compliant": len(violations) == 0}
    except Exception as e:
        return {"error": f"Error: {e}"}


def cash_available() -> dict:
    """Calculate cash available for new positions after 5% minimum reserve.

    Args:
        No arguments required.
    """
    try:
        nav = get_nav()
        cash = _get_cash()
        reserve = nav * 0.05
        available = max(0.0, cash - reserve)
        return {
            "total_cash": cash,
            "minimum_reserve": round(reserve, 2),
            "available_for_deployment": round(available, 2),
            "cash_pct": f"{cash / nav * 100:.1f}%" if nav else "N/A",
        }
    except Exception as e:
        return {"error": f"Error: {e}"}


PORTFOLIO_ALL_TOOLS = [
    get_portfolio_state,
    calculate_portfolio_beta,
    sector_exposure,
    cash_available,
]
