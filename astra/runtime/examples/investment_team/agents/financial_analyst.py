"""
Financial Analyst
-----------------
Analyzes company fundamentals: revenue, margins, cash flow, balance sheet.

Does NOT:
- Perform valuation
- Analyze price charts
- Make portfolio allocation decisions
"""

from framework.agents import Agent
from framework.models import Gemini

from ..context import load_context
from ..tools.financial_tools import FINANCIAL_ALL_TOOLS
from .settings import datetime_context


FINANCIAL_CONTEXT = load_context(
    [
        "mandate.md",
        "process.md",
    ]
)


instructions = (
    datetime_context()
    + FINANCIAL_CONTEXT
    + """
You are the Financial Analyst for a $10M US equity fund.

You analyze company fundamentals only.

Do NOT:
- Perform valuation
- Analyze price charts
- Make portfolio allocation decisions

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

1. Revenue & Growth Analysis
2. Profitability (Margins, ROIC)
3. Cash Flow Strength
4. Balance Sheet Quality
5. Earnings Stability
6. Financial Risk Factors
7. Conviction Score (1-10)

--------------------------------------------------

Be structured.
Be concise.
Be numerical where possible.
"""
)


financial_analyst = Agent(
    id="financial-analyst",
    name="Financial Analyst",
    model=Gemini("gemini-2.5-flash", thinking_budget=0, include_thoughts=False),
    instructions=instructions,
    tools=FINANCIAL_ALL_TOOLS,
    code_mode=False,
)
