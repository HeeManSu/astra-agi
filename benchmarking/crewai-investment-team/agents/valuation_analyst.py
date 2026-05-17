"""
Valuation Analyst — CrewAI version.

Determines intrinsic value and margin of safety.
Identical instruction text to the Agno/Astra sides; only wrapping differs.
"""

from crewai import Agent

from context import load_context
from tools.valuation_tools import VALUATION_ALL_TOOLS

from .settings import datetime_context, make_llm


VALUATION_CONTEXT = load_context(["mandate.md", "process.md"])


backstory = (
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
    role="Valuation Analyst",
    goal="Determine intrinsic value and margin of safety for the target stock.",
    backstory=backstory,
    tools=VALUATION_ALL_TOOLS,
    llm=make_llm(),
    allow_delegation=False,
    memory=False,
    cache=False,
    verbose=False,
    max_iter=15,
)
