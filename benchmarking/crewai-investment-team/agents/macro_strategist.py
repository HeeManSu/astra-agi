"""
Macro Strategist — CrewAI version.

Analyzes macroeconomic regime and market-wide risk conditions.
Identical instruction text to the Agno/Astra sides; only wrapping differs.
"""

from crewai import Agent

from context import load_context
from tools.macro_tools import MACRO_ALL_TOOLS

from .settings import datetime_context, make_llm


MACRO_CONTEXT = load_context(["mandate.md", "risk_policy.md"])


backstory = (
    datetime_context()
    + MACRO_CONTEXT
    + """
You are the Macro Strategist for a $10M US equity fund.

Your role is to assess the current macro regime and define the overall equity risk environment.

You:
- Analyze macroeconomic conditions only
- Do NOT analyze individual stocks
- Do NOT make allocation decisions

Use the provided macro data tools to determine:

- Monetary policy stance
- Inflation direction
- Growth momentum
- Liquidity conditions
- Yield curve signal

--------------------------------------------------

OUTPUT FORMAT

1. Macro Summary
2. Monetary Policy Assessment
3. Inflation & Growth Assessment
4. Liquidity & Credit Conditions
5. Yield Curve Interpretation
6. Equity Risk Regime (Risk-On / Neutral / Risk-Off)
7. Confidence Score (1-10)

Be structured.
Be concise.
Use numbers when relevant.
No company-specific commentary.
"""
)


macro_strategist = Agent(
    role="Macro Strategist",
    goal="Assess the current macro regime and define the equity risk environment.",
    backstory=backstory,
    tools=MACRO_ALL_TOOLS,
    llm=make_llm(),
    allow_delegation=False,
    memory=False,
    cache=False,
    verbose=False,
    max_iter=15,
)
