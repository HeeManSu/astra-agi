"""
Portfolio Tools for Astra Framework.

Four tools for the Portfolio Manager agent.
Uses local portfolio state + yfinance for live prices.
"""

from __future__ import annotations

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


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


class PortfolioStateInput(BaseModel):
    pass


class PortfolioStateOutput(BaseModel):
    result: dict = Field(description="Dict with full portfolio state")


portfolio_state_spec = ToolSpec(
    name="get_portfolio_state",
    description="Get current portfolio: holdings, cash, NAV, sector weights, position sizes.",
    input_schema=PortfolioStateInput,
    output_schema=PortfolioStateOutput,
    examples=[{"input": {}, "output": {"result": '{"nav": 10000000}'}}],
)


@bind_tool(portfolio_state_spec)
def get_portfolio_state(input: PortfolioStateInput) -> PortfolioStateOutput:
    """Return current portfolio state with position sizes."""
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
        data = {
            "nav": nav,
            "cash": cash,
            "cash_pct": f"{cash / nav * 100:.1f}%" if nav else "N/A",
            "num_positions": len(positions),
            "max_positions": 15,
            "positions": enriched,
        }
        return PortfolioStateOutput(result=data)
    except Exception as e:
        return PortfolioStateOutput(result={"error": f"Error: {e}"})


class PortfolioBetaInput(BaseModel):
    pass


class PortfolioBetaOutput(BaseModel):
    result: dict = Field(description="Dict with weighted portfolio beta")


portfolio_beta_spec = ToolSpec(
    name="calculate_portfolio_beta",
    description="Calculate portfolio-weighted beta using current holdings and yfinance betas.",
    input_schema=PortfolioBetaInput,
    output_schema=PortfolioBetaOutput,
    examples=[{"input": {}, "output": {"result": '{"portfolio_beta": 1.05}'}}],
)


@bind_tool(portfolio_beta_spec)
def calculate_portfolio_beta(input: PortfolioBetaInput) -> PortfolioBetaOutput:
    """Calculate weighted portfolio beta."""
    try:
        holdings = get_holdings()
        nav = get_nav()
        if not holdings or not nav:
            return PortfolioBetaOutput(result={"error": "No holdings"})
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
        data = {
            "portfolio_beta": round(weighted_beta, 3),
            "target_range": "0.8 - 1.2",
            "in_range": 0.8 <= weighted_beta <= 1.2,
            "details": details,
        }
        return PortfolioBetaOutput(result=data)
    except Exception as e:
        return PortfolioBetaOutput(result={"error": f"Error: {e}"})


class SectorExposureInput(BaseModel):
    pass


class SectorExposureOutput(BaseModel):
    result: dict = Field(description="Dict with sector weights and cap compliance")


sector_exposure_spec = ToolSpec(
    name="sector_exposure",
    description="Get sector exposure breakdown and check against sector cap limits.",
    input_schema=SectorExposureInput,
    output_schema=SectorExposureOutput,
    examples=[{"input": {}, "output": {"result": '{"Technology": "35.2%"}'}}],
)


@bind_tool(sector_exposure_spec)
def sector_exposure(input: SectorExposureInput) -> SectorExposureOutput:
    """Calculate sector exposure and compliance."""
    try:
        holdings = get_holdings()
        nav = get_nav()
        if not holdings or not nav:
            return SectorExposureOutput(result={"error": "No holdings"})
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
        data = {"sectors": exposure, "violations": violations, "compliant": len(violations) == 0}
        return SectorExposureOutput(result=data)
    except Exception as e:
        return SectorExposureOutput(result={"error": f"Error: {e}"})


class CashAvailableInput(BaseModel):
    pass


class CashAvailableOutput(BaseModel):
    result: dict = Field(description="Dict with available cash after reserve")


cash_available_spec = ToolSpec(
    name="cash_available",
    description="Calculate cash available for new positions after 5% minimum reserve.",
    input_schema=CashAvailableInput,
    output_schema=CashAvailableOutput,
    examples=[{"input": {}, "output": {"result": '{"available": 1000000}'}}],
)


@bind_tool(cash_available_spec)
def cash_available(input: CashAvailableInput) -> CashAvailableOutput:
    """Calculate deployable cash after reserve."""
    try:
        nav = get_nav()
        cash = _get_cash()
        reserve = nav * 0.05
        available = max(0.0, cash - reserve)
        data = {
            "total_cash": cash,
            "minimum_reserve": round(reserve, 2),
            "available_for_deployment": round(available, 2),
            "cash_pct": f"{cash / nav * 100:.1f}%" if nav else "N/A",
        }
        return CashAvailableOutput(result=data)
    except Exception as e:
        return CashAvailableOutput(result={"error": f"Error: {e}"})


PORTFOLIO_ALL_TOOLS = [
    get_portfolio_state,
    calculate_portfolio_beta,
    sector_exposure,
    cash_available,
]
