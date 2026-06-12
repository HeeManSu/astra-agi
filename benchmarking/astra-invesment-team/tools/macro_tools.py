"""
Macro Tools for Astra Framework.

Three compact FRED-based tools for the Macro Strategist agent.
Each returns a single JSON snapshot — no time series, no arrays.

Requires:
    pip install fredapi
    export FRED_API_KEY=<your-key>
"""

from os import getenv

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


try:
    from fredapi import Fred
except ImportError as e:
    raise ImportError("`fredapi` not installed. Install with: pip install fredapi") from e


def _get_fred() -> Fred:
    """Return a Fred client. Fails fast if no API key."""
    key = getenv("FRED_API_KEY", "")
    if not key:
        raise RuntimeError("FRED_API_KEY not set. Get a free key at https://fred.stlouisfed.org")
    return Fred(api_key=key)


def _latest(series_id: str, fred: Fred) -> float:
    """Fetch the most recent value for a FRED series."""
    s = fred.get_series(series_id)
    return round(float(s.dropna().iloc[-1]), 4)


def _previous(series_id: str, fred: Fred, offset: int = 1) -> float:
    """Fetch the Nth-to-last value for a FRED series."""
    s = fred.get_series(series_id)
    clean = s.dropna()
    return round(float(clean.iloc[-(offset + 1)]), 4)


def _trend(current: float, previous: float) -> str:
    """Simple trend classifier: rising / falling / stable."""
    diff = current - previous
    if abs(diff) < 0.05:
        return "stable"
    return "rising" if diff > 0 else "falling"


# 1. get_monetary_policy_data
class MonetaryPolicyInput(BaseModel):
    """No input required — fetches latest snapshot."""


class MonetaryPolicyOutput(BaseModel):
    result: dict = Field(description="Dict with fed_funds_rate, rate_trend, 10y/2y yields, spread, policy_stance")


monetary_policy_spec = ToolSpec(
    name="get_monetary_policy_data",
    description=(
        "Get current monetary policy snapshot: fed funds rate, 10Y/2Y treasury yields, "
        "yield spread, rate trend, and policy stance classification."
    ),
    input_schema=MonetaryPolicyInput,
    output_schema=MonetaryPolicyOutput,
    examples=[
        {
            "input": {},
            "output": {
                "result": '{"fed_funds_rate": 5.33, "rate_trend": "stable", "10y_treasury": 4.25, "2y_treasury": 4.71, "yield_spread_10y_2y": -0.46, "policy_stance": "restrictive"}'
            },
        }
    ],
)


@bind_tool(monetary_policy_spec)
def get_monetary_policy_data(input: MonetaryPolicyInput) -> MonetaryPolicyOutput:
    """Fetch monetary policy data from FRED."""
    try:
        fred = _get_fred()

        fed_funds = _latest("FEDFUNDS", fred)
        fed_funds_prev = _previous("FEDFUNDS", fred)
        treasury_10y = _latest("DGS10", fred)
        treasury_2y = _latest("DGS2", fred)
        spread = round(treasury_10y - treasury_2y, 4)

        # Simple stance classification
        if fed_funds > 4.0:
            stance = "restrictive"
        elif fed_funds < 2.0:
            stance = "accommodative"
        else:
            stance = "neutral"

        data = {
            "fed_funds_rate": fed_funds,
            "rate_trend": _trend(fed_funds, fed_funds_prev),
            "10y_treasury": treasury_10y,
            "2y_treasury": treasury_2y,
            "yield_spread_10y_2y": spread,
            "policy_stance": stance,
        }
        res = data
    except Exception as e:
        res = {"error": f"Error fetching monetary policy data: {e}"}
    return MonetaryPolicyOutput(result=res)


# 2. get_inflation_and_growth_data
class InflationGrowthInput(BaseModel):
    """No input required — fetches latest snapshot."""


class InflationGrowthOutput(BaseModel):
    result: dict = Field(description="Dict with CPI, core CPI, GDP, unemployment data and trends")


inflation_growth_spec = ToolSpec(
    name="get_inflation_and_growth_data",
    description=(
        "Get current inflation and growth snapshot: CPI YoY, core CPI, GDP QoQ growth, "
        "unemployment rate, and trend classifications."
    ),
    input_schema=InflationGrowthInput,
    output_schema=InflationGrowthOutput,
    examples=[
        {
            "input": {},
            "output": {
                "result": '{"cpi_yoy": 3.1, "cpi_trend": "falling", "core_cpi_yoy": 3.4, "gdp_growth_qoq": 2.2, "gdp_trend": "stable", "unemployment_rate": 3.8, "labor_trend": "tight"}'
            },
        }
    ],
)


@bind_tool(inflation_growth_spec)
def get_inflation_and_growth_data(input: InflationGrowthInput) -> InflationGrowthOutput:
    """Fetch inflation and growth data from FRED."""
    try:
        fred = _get_fred()

        # CPI YoY: (latest - 12 months ago) / 12 months ago * 100
        cpi_series = fred.get_series("CPIAUCSL").dropna()
        cpi_latest = float(cpi_series.iloc[-1])
        cpi_12m_ago = float(cpi_series.iloc[-13])
        cpi_yoy = round((cpi_latest - cpi_12m_ago) / cpi_12m_ago * 100, 2)

        cpi_prev_yoy_num = float(cpi_series.iloc[-2])
        cpi_prev_yoy_den = float(cpi_series.iloc[-14])
        cpi_prev_yoy = round((cpi_prev_yoy_num - cpi_prev_yoy_den) / cpi_prev_yoy_den * 100, 2)

        # Core CPI YoY
        core_series = fred.get_series("CPILFESL").dropna()
        core_latest = float(core_series.iloc[-1])
        core_12m_ago = float(core_series.iloc[-13])
        core_cpi_yoy = round((core_latest - core_12m_ago) / core_12m_ago * 100, 2)

        # GDP QoQ: real GDP (GDPC1, quarterly)
        gdp_series = fred.get_series("GDPC1").dropna()
        gdp_latest = float(gdp_series.iloc[-1])
        gdp_prev = float(gdp_series.iloc[-2])
        gdp_growth = round((gdp_latest - gdp_prev) / gdp_prev * 100, 2)

        gdp_prev2 = float(gdp_series.iloc[-3])
        gdp_prev_growth = round((gdp_prev - gdp_prev2) / gdp_prev2 * 100, 2)

        # Unemployment
        unemp = _latest("UNRATE", fred)

        # Labor trend
        if unemp < 4.0:
            labor = "tight"
        elif unemp > 6.0:
            labor = "weakening"
        else:
            labor = "moderate"

        data = {
            "cpi_yoy": cpi_yoy,
            "cpi_trend": _trend(cpi_yoy, cpi_prev_yoy),
            "core_cpi_yoy": core_cpi_yoy,
            "gdp_growth_qoq": gdp_growth,
            "gdp_trend": _trend(gdp_growth, gdp_prev_growth),
            "unemployment_rate": unemp,
            "labor_trend": labor,
        }
        res = data
    except Exception as e:
        res = {"error": f"Error fetching inflation/growth data: {e}"}
    return InflationGrowthOutput(result=res)


# 3. get_liquidity_and_credit_conditions
class LiquidityCreditInput(BaseModel):
    """No input required — fetches latest snapshot."""


class LiquidityCreditOutput(BaseModel):
    result: dict = Field(description="Dict with financial conditions index, credit spread, liquidity/risk regime")


liquidity_credit_spec = ToolSpec(
    name="get_liquidity_and_credit_conditions",
    description=(
        "Get current liquidity and credit conditions: Chicago Fed NFCI, "
        "corporate credit spread, liquidity regime, and risk regime classification."
    ),
    input_schema=LiquidityCreditInput,
    output_schema=LiquidityCreditOutput,
    examples=[
        {
            "input": {},
            "output": {
                "result": '{"financial_conditions_index": -0.42, "credit_spread": 1.8, "liquidity_regime": "easing", "risk_regime": "risk_on"}'
            },
        }
    ],
)


@bind_tool(liquidity_credit_spec)
def get_liquidity_and_credit_conditions(input: LiquidityCreditInput) -> LiquidityCreditOutput:
    """Fetch liquidity and credit conditions from FRED."""
    try:
        fred = _get_fred()

        nfci = _latest("NFCI", fred)
        credit_spread = _latest("BAMLC0A0CM", fred)

        # NFCI: positive = tightening, negative = easing
        if nfci > 0:
            liquidity = "tightening"
        elif nfci < -0.5:
            liquidity = "easing"
        else:
            liquidity = "neutral"

        # Risk regime: combine NFCI + credit spread
        if nfci > 0.5 or credit_spread > 4.0:
            risk = "risk_off"
        elif nfci < -0.3 and credit_spread < 2.0:
            risk = "risk_on"
        else:
            risk = "neutral"

        data = {
            "financial_conditions_index": nfci,
            "credit_spread": credit_spread,
            "liquidity_regime": liquidity,
            "risk_regime": risk,
        }
        res = data
    except Exception as e:
        res = {"error": f"Error fetching liquidity/credit data: {e}"}
    return LiquidityCreditOutput(result=res)


MACRO_ALL_TOOLS = [
    get_monetary_policy_data,
    get_inflation_and_growth_data,
    get_liquidity_and_credit_conditions,
]
