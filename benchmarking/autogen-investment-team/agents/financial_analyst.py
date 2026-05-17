"""
Financial Analyst — AutoGen version.

Core backstory text is identical to the Astra/Agno/CrewAI sides. AutoGen
adds a small TEAM_CONTEXT footer (see settings.py) to restore parity with
the other frameworks' manager-driven query-reframing behavior, which
AutoGen's `SelectorGroupChat` does not provide.
"""

from autogen_agentchat.agents import AssistantAgent

from context import load_context
from tools.financial_tools import FINANCIAL_ALL_TOOLS

from .settings import TEAM_CONTEXT, datetime_context, make_model_client


FINANCIAL_CONTEXT = load_context(["mandate.md", "process.md"])


SYSTEM_MESSAGE = (
    datetime_context()
    + FINANCIAL_CONTEXT
    + TEAM_CONTEXT
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


financial_analyst = AssistantAgent(
    name="FinancialAnalyst",
    model_client=make_model_client(),
    tools=FINANCIAL_ALL_TOOLS,
    system_message=SYSTEM_MESSAGE,
    description="Analyzes company fundamentals: revenue, margins, cash flow, balance sheet, financial risk.",
    reflect_on_tool_use=True,
    max_tool_iterations=15,
)
