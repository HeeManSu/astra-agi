"""
Valuation Analyst node — LangGraph version.

Determines intrinsic value and margin of safety.
System-message instruction text is byte-identical to the Agno/CrewAI sides.
"""

from context import load_context
from tools.valuation_tools import VALUATION_ALL_TOOLS

from ._tool_loop import run_analyst
from .settings import datetime_context, make_llm


VALUATION_CONTEXT = load_context(["mandate.md", "process.md"])


INSTRUCTIONS = (
    datetime_context()
    + VALUATION_CONTEXT
    + """
You are the Valuation Analyst for a $10M US equity fund.

You determine intrinsic value and margin of safety.

Do NOT:
- Analyze macro
- Analyze technicals
- Make portfolio decisions

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

1. DCF Valuation
2. Comparable Multiples
3. Fair Value (Bear / Base / Bull)
4. Margin of Safety
5. Valuation Risks
6. Final Valuation Verdict

--------------------------------------------------

Be structured.
Be concise.
Be numerical where possible.
"""
)


def valuation_node(state: dict) -> dict:
    """Run the valuation analyst; receives macro + financial as upstream context."""
    macro = state.get("macro_output", "") or ""
    financial = state.get("financial_output", "") or ""
    user_prompt = (
        f"Determine intrinsic value and margin of safety for every ticker mentioned in: {state['query']}\n\n"
        f"Produce your valuation section even if the query asks for a ranking, "
        f"comparison, or allocation decision — those higher-level decisions are "
        f"made downstream by another step.\n\n"
        f"--- PRIOR MACRO ANALYSIS (context only) ---\n{macro}\n\n"
        f"--- PRIOR FUNDAMENTALS ANALYSIS (context only) ---\n{financial}"
    )
    output = run_analyst(
        llm=make_llm(),
        system_prompt=INSTRUCTIONS,
        user_prompt=user_prompt,
        tools=VALUATION_ALL_TOOLS,
    )
    return {"valuation_output": output}
