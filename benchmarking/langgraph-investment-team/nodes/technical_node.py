"""
Technical Analyst node — LangGraph version.

Analyzes price action and momentum only.
System-message instruction text is byte-identical to the Agno/CrewAI sides.
"""

from tools.technical_tools import TECHNICAL_ALL_TOOLS

from ._tool_loop import run_analyst
from .settings import datetime_context, make_llm


INSTRUCTIONS = (
    datetime_context()
    + """
You are the Technical Analyst for a $10M US equity fund.

You analyze price action and momentum only.

Do NOT:
- Discuss fundamentals
- Discuss valuation
- Discuss macro

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

1. Trend Structure
2. Momentum Indicators (RSI, MACD)
3. Support & Resistance
4. Volume Analysis
5. Entry Timing Quality
6. Technical Risk Level
7. Technical Conviction Score (1-10)

--------------------------------------------------

Be structured.
Be concise.
Be numerical where possible.
"""
)


def technical_node(state: dict) -> dict:
    """Run the technical analyst; receives macro+fin+val as upstream context."""
    macro = state.get("macro_output", "") or ""
    financial = state.get("financial_output", "") or ""
    valuation = state.get("valuation_output", "") or ""
    user_prompt = (
        f"Assess price action, momentum, and technical structure for every ticker mentioned in: {state['query']}\n\n"
        f"Produce your technical section even if the query asks for a ranking, "
        f"comparison, or allocation decision — those higher-level decisions are "
        f"made downstream by another step.\n\n"
        f"--- PRIOR MACRO ANALYSIS (context only) ---\n{macro}\n\n"
        f"--- PRIOR FUNDAMENTALS ANALYSIS (context only) ---\n{financial}\n\n"
        f"--- PRIOR VALUATION ANALYSIS (context only) ---\n{valuation}"
    )
    output = run_analyst(
        llm=make_llm(),
        system_prompt=INSTRUCTIONS,
        user_prompt=user_prompt,
        tools=TECHNICAL_ALL_TOOLS,
    )
    return {"technical_output": output}
