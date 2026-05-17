"""
Valuation Tools — Agno version.

Four tools for the Valuation Analyst agent.
Same logic as Astra, plain functions.
"""

from __future__ import annotations

from crewai.tools import tool
try:
    import yfinance as yf
except ImportError as e:
    raise ImportError("`yfinance` not installed. pip install yfinance") from e


def _fmt_num(value) -> str:
    if value is None or value == "N/A":
        return "N/A"
    try:
        v = float(value)
        if abs(v) >= 1e9:
            return f"${v / 1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v / 1e6:.1f}M"
        return f"${v:,.2f}"
    except (TypeError, ValueError):
        return "N/A"


@tool
def get_current_market_data(symbol: str) -> dict:
    """Get current market data for valuation: price, market cap, enterprise value, shares outstanding, free cash flow, and key multiples.

    Args:
        symbol (str): Stock ticker symbol (e.g. AAPL, NVDA).
    """
    try:
        info = yf.Ticker(symbol).info or {}
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        return {
            "symbol": symbol,
            "current_price": round(price, 2) if price else "N/A",
            "market_cap": _fmt_num(info.get("marketCap")),
            "enterprise_value": _fmt_num(info.get("enterpriseValue")),
            "shares_outstanding": _fmt_num(info.get("sharesOutstanding")),
            "free_cashflow": _fmt_num(info.get("freeCashflow")),
            "trailing_pe": info.get("trailingPE", "N/A"),
            "forward_pe": info.get("forwardPE", "N/A"),
            "ev_to_ebitda": info.get("enterpriseToEbitda", "N/A"),
            "price_to_book": info.get("priceToBook", "N/A"),
        }
    except Exception as e:
        return {"error": f"Error fetching market data for {symbol}: {e}"}


@tool
def calculate_dcf(
    symbol: str,
    growth_rate: float = 0.10,
    discount_rate: float = 0.10,
    terminal_growth: float = 0.03,
    projection_years: int = 5,
) -> dict:
    """Run a DCF valuation. Returns bear/base/bull intrinsic value per share.

    Args:
        symbol (str): Stock ticker symbol.
        growth_rate (float): Expected FCF growth rate (e.g. 0.10 for 10%).
        discount_rate (float): Discount rate / WACC (e.g. 0.10 for 10%).
        terminal_growth (float): Terminal growth rate (e.g. 0.03 for 3%).
        projection_years (int): Number of years to project (default 5).
    """
    try:
        if discount_rate <= terminal_growth:
            return {
                "error": "discount_rate must be greater than terminal_growth",
                "discount_rate": discount_rate,
                "terminal_growth": terminal_growth,
            }

        info = yf.Ticker(symbol).info or {}
        fcf = info.get("freeCashflow")
        shares = info.get("sharesOutstanding")

        if not fcf or not shares:
            return {
                "error": f"Missing FCF or shares data for {symbol}",
                "fcf": fcf,
                "shares": shares,
            }

        fcf_val = float(fcf)
        shares_val = float(shares)

        def _dcf(growth: float) -> float:
            pv_fcfs = 0.0
            projected_fcf = fcf_val
            for year in range(1, projection_years + 1):
                projected_fcf *= 1 + growth
                pv_fcfs += projected_fcf / ((1 + discount_rate) ** year)
            # Terminal value (Gordon Growth Model)
            terminal_fcf = projected_fcf * (1 + terminal_growth)
            terminal_value = terminal_fcf / (discount_rate - terminal_growth)
            pv_terminal = terminal_value / ((1 + discount_rate) ** projection_years)
            return round((pv_fcfs + pv_terminal) / shares_val, 2)

        base = _dcf(growth_rate)
        bear = _dcf(growth_rate * 0.5)
        bull = _dcf(growth_rate * 1.5)

        price = info.get("regularMarketPrice") or info.get("currentPrice") or 0

        return {
            "symbol": symbol,
            "current_price": round(float(price), 2) if price else "N/A",
            "fcf_used": _fmt_num(fcf),
            "growth_rate": f"{growth_rate * 100:.1f}%",
            "discount_rate": f"{discount_rate * 100:.1f}%",
            "bear_case": bear,
            "base_case": base,
            "bull_case": bull,
            "base_upside": f"{((base / float(price)) - 1) * 100:.1f}%" if price else "N/A",
        }
    except Exception as e:
        return {"error": f"Error calculating DCF for {symbol}: {e}"}


@tool
def calculate_multiple_valuation(symbol: str) -> dict:
    """Get relative valuation using price multiples: trailing P/E, forward P/E, EV/EBITDA, P/B, PEG ratio.

    Args:
        symbol (str): Stock ticker symbol.
    """
    try:
        info = yf.Ticker(symbol).info or {}

        forward_pe = info.get("forwardPE")

        if forward_pe and isinstance(forward_pe, (int, float)):
            if forward_pe < 15:
                assessment = "Potentially undervalued"
            elif forward_pe < 25:
                assessment = "Fairly valued"
            elif forward_pe < 40:
                assessment = "Premium valuation"
            else:
                assessment = "Richly valued"
        else:
            assessment = "N/A"

        trailing_pe = info.get("trailingPE")
        peg = info.get("pegRatio")

        return {
            "symbol": symbol,
            "trailing_pe": round(trailing_pe, 2) if trailing_pe else "N/A",
            "forward_pe": round(forward_pe, 2) if forward_pe else "N/A",
            "peg_ratio": round(peg, 2) if peg else "N/A",
            "ev_to_ebitda": round(info.get("enterpriseToEbitda", 0) or 0, 2) or "N/A",
            "ev_to_revenue": round(info.get("enterpriseToRevenue", 0) or 0, 2) or "N/A",
            "price_to_book": round(info.get("priceToBook", 0) or 0, 2) or "N/A",
            "price_to_sales": round(info.get("priceToSalesTrailing12Months", 0) or 0, 2) or "N/A",
            "assessment": assessment,
        }
    except Exception as e:
        return {"error": f"Error calculating multiples for {symbol}: {e}"}


@tool
def calculate_margin_of_safety(current_price: float, fair_value: float) -> dict:
    """Calculate margin of safety given current price and estimated fair value. Returns percentage and buy/hold/pass verdict.

    Args:
        current_price (float): Current stock price (must be > 0).
        fair_value (float): Estimated fair value per share (must be > 0).
    """
    try:
        mos = round((fair_value - current_price) / fair_value * 100, 1)
        upside = round((fair_value / current_price - 1) * 100, 1)

        if mos >= 30:
            verdict = "Very attractive - strong margin of safety"
        elif mos >= 15:
            verdict = "Attractive - adequate margin of safety"
        elif mos >= 0:
            verdict = "Fairly valued - limited margin of safety"
        else:
            verdict = "Overvalued - negative margin of safety"

        return {
            "current_price": current_price,
            "fair_value": fair_value,
            "margin_of_safety": f"{mos}%",
            "upside_potential": f"{upside}%",
            "verdict": verdict,
        }
    except Exception as e:
        return {"error": f"Error calculating margin of safety: {e}"}


# Export
VALUATION_ALL_TOOLS = [
    get_current_market_data,
    calculate_dcf,
    calculate_multiple_valuation,
    calculate_margin_of_safety,
]
