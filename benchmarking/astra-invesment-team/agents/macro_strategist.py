"""
Macro Strategist
----------------
Analyzes macroeconomic regime and market-wide risk conditions.

Responsibilities:
- Interest rate environment
- Inflation trend
- Liquidity regime
- Yield curve structure
- Risk-on / Risk-off assessment

Does NOT:
- Analyze individual companies
- Do valuation
- Make portfolio allocation decisions
"""

from framework.agents import Agent
from framework.models import Gemini

from context import load_context
from config import DISABLED_MEMORY
from tools.macro_tools import MACRO_ALL_TOOLS
from .settings import datetime_context


MACRO_CONTEXT = load_context(
    [
        "mandate.md",
        "risk_policy.md",
    ]
)


instructions = (
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
    id="macro-strategist",
    name="Macro Strategist",
    model=Gemini("gemini-2.5-flash", thinking_budget=0, include_thoughts=False),
    instructions=instructions,
    tools=MACRO_ALL_TOOLS,
    code_mode=False,
    memory=DISABLED_MEMORY,
)
