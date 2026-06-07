"""
Financial Analyst
-----------------
Analyzes company fundamentals: revenue, margins, cash flow, balance sheet.
"""

from agno.agent import Agent
from agno.models.google import Gemini

from context import load_context
from tools.financial_tools import FINANCIAL_ALL_TOOLS
from db import db


FINANCIAL_CONTEXT = load_context(
    [
        "mandate.md",
        "process.md",
    ]
)

instructions = (
    FINANCIAL_CONTEXT
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
    db=db,
    name="Financial Analyst",
    model=Gemini(id="gemini-2.5-flash", thinking_budget=0, include_thoughts=False, temperature=0.0),
    instructions=instructions,
    tools=FINANCIAL_ALL_TOOLS,
    add_datetime_to_context=True,
    markdown=False,
    # Memory off (paper §4.4 disclosure — matches Agno defaults, set explicitly).
    enable_agentic_memory=False,
    add_history_to_context=False,
)