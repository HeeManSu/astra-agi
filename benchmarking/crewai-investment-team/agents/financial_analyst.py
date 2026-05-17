"""
Financial Analyst — CrewAI version.

Analyzes company fundamentals: revenue, margins, cash flow, balance sheet.
Identical instruction text to the Agno/Astra sides; only wrapping differs.
"""

from crewai import Agent

from context import load_context
from tools.financial_tools import FINANCIAL_ALL_TOOLS

from .settings import datetime_context, make_llm


FINANCIAL_CONTEXT = load_context(["mandate.md", "process.md"])


backstory = (
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
    role="Financial Analyst",
    goal="Analyze company fundamentals — revenue, margins, cash flow, balance sheet.",
    backstory=backstory,
    tools=FINANCIAL_ALL_TOOLS,
    llm=make_llm(),
    allow_delegation=False,
    memory=False,
    cache=False,
    verbose=False,
    max_iter=15,
)
