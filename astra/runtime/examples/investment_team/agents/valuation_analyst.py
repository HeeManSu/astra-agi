"""
Valuation Analyst
-----------------
Determines intrinsic value and margin of safety.

Does NOT:
- Analyze macro
- Analyze technicals
- Make portfolio decisions
"""

from framework.agents import Agent
from framework.models import Gemini

from ..context import load_context
from ..tools.valuation_tools import VALUATION_ALL_TOOLS
from .settings import datetime_context


VALUATION_CONTEXT = load_context(
    [
        "mandate.md",
        "process.md",
    ]
)


instructions = (
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


valuation_analyst = Agent(
    id="valuation-analyst",
    name="Valuation Analyst",
    model=Gemini("gemini-2.5-flash", thinking_budget=0, include_thoughts=False),
    instructions=instructions,
    tools=VALUATION_ALL_TOOLS,
    code_mode=False,
)
