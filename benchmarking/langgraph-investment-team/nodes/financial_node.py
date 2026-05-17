"""
Financial Analyst node — LangGraph version.

Analyzes company fundamentals: revenue, margins, cash flow, balance sheet.
System-message instruction text is byte-identical to the Agno/CrewAI sides.
"""

from context import load_context
from tools.financial_tools import FINANCIAL_ALL_TOOLS

from ._tool_loop import run_analyst
from .settings import datetime_context, make_llm


FINANCIAL_CONTEXT = load_context(["mandate.md", "process.md"])


INSTRUCTIONS = (
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


def financial_node(state: dict) -> dict:
    """Run the financial analyst; receives prior macro output as upstream context."""
    macro = state.get("macro_output", "") or ""
    user_prompt = (
        f"Analyze the company fundamentals for every ticker mentioned in: {state['query']}\n\n"
        f"Produce your fundamentals section even if the query asks for a ranking, "
        f"comparison, or allocation decision — those higher-level decisions are "
        f"made downstream by another step.\n\n"
        f"--- PRIOR MACRO ANALYSIS (context only) ---\n{macro}"
    )
    output = run_analyst(
        llm=make_llm(),
        system_prompt=INSTRUCTIONS,
        user_prompt=user_prompt,
        tools=FINANCIAL_ALL_TOOLS,
    )
    return {"financial_output": output}
