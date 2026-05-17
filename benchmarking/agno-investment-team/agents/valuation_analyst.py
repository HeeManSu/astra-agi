"""
Valuation Analyst
-----------------
Determines intrinsic value and margin of safety.
"""

from agno.agent import Agent
from agno.models.google import Gemini

from context import load_context
from tools.valuation_tools import VALUATION_ALL_TOOLS


VALUATION_CONTEXT = load_context(
    [
        "mandate.md",
        "process.md",
    ]
)

instructions = (
    VALUATION_CONTEXT
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

valuation_analyst = Agent(
    id="valuation-analyst",
    name="Valuation Analyst",
    model=Gemini(id="gemini-2.5-flash", thinking_budget=0, include_thoughts=False, temperature=0.0),
    instructions=instructions,
    tools=VALUATION_ALL_TOOLS,
    add_datetime_to_context=True,
    markdown=False,
    # Memory off (paper §4.4 disclosure — matches Agno defaults, set explicitly).
    enable_agentic_memory=False,
    add_history_to_context=False,
)
