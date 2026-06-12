"""
Valuation Tools for Astra Framework.

Four tools for the Valuation Analyst agent.
- Market data from yfinance
- DCF with internal math
- Multiples comparison
- Margin of safety calculation
"""

from __future__ import annotations

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


try:
    import yfinance as yf
except ImportError as e:
    raise ImportError("`yfinance` not installed. Install with: pip install yfinance") from e


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


# 1. get_current_market_data
class MarketDataInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol (e.g. AAPL, NVDA)")


class MarketDataOutput(BaseModel):
    result: dict = Field(description="Dict with price, market cap, shares outstanding, FCF")


market_data_spec = ToolSpec(
    name="get_current_market_data",
    description=(
        "Get current market data. Returns result dict with keys: current_price (float), "
        "market_cap (str), enterprise_value (str), shares_outstanding (str), free_cashflow (str). "
        "Use current_price as current_price for calculate_margin_of_safety."
    ),
    input_schema=MarketDataInput,
    output_schema=MarketDataOutput,
    examples=[
        {
            "input": {"symbol": "AAPL"},
            "output": {"result": '{"current_price": 178.5, "market_cap": "$2.75T", "free_cashflow": "$105.0B"}'},
        }
    ],
)


@bind_tool(market_data_spec)
def get_current_market_data(input: MarketDataInput) -> MarketDataOutput:
    """Fetch current market data for valuation from yfinance."""
    try:
        info = yf.Ticker(input.symbol).info or {}
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        data = {
            "symbol": input.symbol,
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
        return MarketDataOutput(result=data)
    except Exception as e:
        return MarketDataOutput(result={"error": f"Error fetching market data for {input.symbol}: {e}"})


# 2. calculate_dcf
class DcfInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol")
    growth_rate: float = Field(default=0.10, description="Expected FCF growth rate (e.g. 0.10 for 10%)")
    discount_rate: float = Field(default=0.10, gt=0, description="Discount rate / WACC (e.g. 0.10 for 10%)")
    terminal_growth: float = Field(default=0.03, ge=0, description="Terminal growth rate (e.g. 0.03 for 3%)")
    projection_years: int = Field(default=5, ge=1, description="Number of years to project (default 5)")


class DcfOutput(BaseModel):
    result: dict = Field(
        description=(
            "Dict with exact keys: symbol (str), current_price (float), fcf_used (str), "
            "growth_rate (str), discount_rate (str), bear_case (float), base_case (float), "
            "bull_case (float), base_upside (str). "
            "To get fair value: .get('result', {}).get('base_case'). "
            "To get price: .get('result', {}).get('current_price')."
        )
    )


dcf_spec = ToolSpec(
    name="calculate_dcf",
    description=(
        "Run a DCF valuation. Returns result dict with keys: bear_case (float), "
        "base_case (float), bull_case (float), current_price (float). "
        "Use base_case as fair_value for calculate_margin_of_safety."
    ),
    input_schema=DcfInput,
    output_schema=DcfOutput,
    examples=[
        {
            "input": {"symbol": "AAPL", "growth_rate": 0.08, "discount_rate": 0.10},
            "output": {
                "result": '{"base_case": 165.4, "bear_case": 120.1, "bull_case": 210.8, "current_price": 175.0}'
            },
        }
    ],
)


@bind_tool(dcf_spec)
def calculate_dcf(input: DcfInput) -> DcfOutput:
    """Run a simple DCF valuation using yfinance FCF data."""
    try:
        if input.discount_rate <= input.terminal_growth:
            return DcfOutput(
                result={
                    "error": "discount_rate must be greater than terminal_growth",
                    "discount_rate": input.discount_rate,
                    "terminal_growth": input.terminal_growth,
                }
            )

        info = yf.Ticker(input.symbol).info or {}
        fcf = info.get("freeCashflow")
        shares = info.get("sharesOutstanding")

        if not fcf or not shares:
            return DcfOutput(
                result={
                    "error": f"Missing FCF or shares data for {input.symbol}",
                    "fcf": fcf,
                    "shares": shares,
                }
            )

        fcf_val = float(fcf)
        shares_val = float(shares)

        def _dcf(growth: float) -> float:
            pv_fcfs = 0.0
            projected_fcf = fcf_val
            for year in range(1, input.projection_years + 1):
                projected_fcf *= 1 + growth
                pv_fcfs += projected_fcf / ((1 + input.discount_rate) ** year)
            # Terminal value (Gordon Growth Model)
            terminal_fcf = projected_fcf * (1 + input.terminal_growth)
            terminal_value = terminal_fcf / (input.discount_rate - input.terminal_growth)
            pv_terminal = terminal_value / ((1 + input.discount_rate) ** input.projection_years)
            return round((pv_fcfs + pv_terminal) / shares_val, 2)

        base = _dcf(input.growth_rate)
        bear = _dcf(input.growth_rate * 0.5)
        bull = _dcf(input.growth_rate * 1.5)

        price = info.get("regularMarketPrice") or info.get("currentPrice") or 0

        data = {
            "symbol": input.symbol,
            "current_price": round(float(price), 2) if price else "N/A",
            "fcf_used": _fmt_num(fcf),
            "growth_rate": f"{input.growth_rate * 100:.1f}%",
            "discount_rate": f"{input.discount_rate * 100:.1f}%",
            "bear_case": bear,
            "base_case": base,
            "bull_case": bull,
            "base_upside": f"{((base / float(price)) - 1) * 100:.1f}%" if price else "N/A",
        }
        return DcfOutput(result=data)
    except Exception as e:
        return DcfOutput(result={"error": f"Error calculating DCF for {input.symbol}: {e}"})


# 3. calculate_multiple_valuation
class MultipleValuationInput(BaseModel):
    symbol: str = Field(description="Stock ticker symbol")


class MultipleValuationOutput(BaseModel):
    result: dict = Field(description="Dict with P/E, EV/EBITDA, P/B relative to sector")


multiple_valuation_spec = ToolSpec(
    name="calculate_multiple_valuation",
    description=("Get relative valuation using price multiples: trailing P/E, forward P/E, EV/EBITDA, P/B, PEG ratio."),
    input_schema=MultipleValuationInput,
    output_schema=MultipleValuationOutput,
    examples=[
        {
            "input": {"symbol": "NVDA"},
            "output": {"result": '{"trailing_pe": 65.2, "forward_pe": 30.1}'},
        }
    ],
)


@bind_tool(multiple_valuation_spec)
def calculate_multiple_valuation(input: MultipleValuationInput) -> MultipleValuationOutput:
    """Compute relative valuation multiples from yfinance."""
    try:
        info = yf.Ticker(input.symbol).info or {}

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

        data = {
            "symbol": input.symbol,
            "trailing_pe": round(trailing_pe, 2) if trailing_pe else "N/A",
            "forward_pe": round(forward_pe, 2) if forward_pe else "N/A",
            "peg_ratio": round(peg, 2) if peg else "N/A",
            "ev_to_ebitda": round(info.get("enterpriseToEbitda", 0) or 0, 2) or "N/A",
            "ev_to_revenue": round(info.get("enterpriseToRevenue", 0) or 0, 2) or "N/A",
            "price_to_book": round(info.get("priceToBook", 0) or 0, 2) or "N/A",
            "price_to_sales": round(info.get("priceToSalesTrailing12Months", 0) or 0, 2) or "N/A",
            "assessment": assessment,
        }
        return MultipleValuationOutput(result=data)
    except Exception as e:
        return MultipleValuationOutput(result={"error": f"Error calculating multiples for {input.symbol}: {e}"})


# 4. calculate_margin_of_safety
class MarginOfSafetyInput(BaseModel):
    current_price: float = Field(gt=0, description="Current stock price")
    fair_value: float = Field(gt=0, description="Estimated fair value per share")


class MarginOfSafetyOutput(BaseModel):
    result: dict = Field(description="Dict with margin of safety % and verdict")


margin_of_safety_spec = ToolSpec(
    name="calculate_margin_of_safety",
    description=(
        "Calculate margin of safety given current price and estimated fair value. "
        "Returns percentage and a buy/hold/pass verdict."
    ),
    input_schema=MarginOfSafetyInput,
    output_schema=MarginOfSafetyOutput,
    examples=[
        {
            "input": {"current_price": 150.0, "fair_value": 200.0},
            "output": {"result": '{"margin_of_safety": "25.0%", "verdict": "Attractive"}'},
        }
    ],
)


@bind_tool(margin_of_safety_spec)
def calculate_margin_of_safety(input: MarginOfSafetyInput) -> MarginOfSafetyOutput:
    """Calculate margin of safety and provide verdict."""
    try:
        mos = round((input.fair_value - input.current_price) / input.fair_value * 100, 1)
        upside = round((input.fair_value / input.current_price - 1) * 100, 1)

        if mos >= 30:
            verdict = "Very attractive - strong margin of safety"
        elif mos >= 15:
            verdict = "Attractive - adequate margin of safety"
        elif mos >= 0:
            verdict = "Fairly valued - limited margin of safety"
        else:
            verdict = "Overvalued - negative margin of safety"

        data = {
            "current_price": input.current_price,
            "fair_value": input.fair_value,
            "margin_of_safety": f"{mos}%",
            "upside_potential": f"{upside}%",
            "verdict": verdict,
        }
        return MarginOfSafetyOutput(result=data)
    except Exception as e:
        return MarginOfSafetyOutput(result={"error": f"Error calculating margin of safety: {e}"})


# Export
VALUATION_ALL_TOOLS = [
    get_current_market_data,
    calculate_dcf,
    calculate_multiple_valuation,
    calculate_margin_of_safety,
]
