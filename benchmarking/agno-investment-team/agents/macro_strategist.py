"""
Macro Strategist
----------------
Analyzes macroeconomic regime and market-wide risk conditions.
"""

from agno.agent import Agent
from agno.models.google import Gemini

from context import load_context
from tools.macro_tools import MACRO_ALL_TOOLS


MACRO_CONTEXT = load_context(
    [
        "mandate.md",
        "risk_policy.md",
    ]
)

instructions = (
    MACRO_CONTEXT
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
    model=Gemini(id="gemini-2.5-flash", thinking_budget=0, include_thoughts=False, temperature=0.0),
    instructions=instructions,
    tools=MACRO_ALL_TOOLS,
    add_datetime_to_context=True,
    markdown=False,
    # Memory off (paper §4.4 disclosure — matches Agno defaults, set explicitly).
    enable_agentic_memory=False,
    add_history_to_context=False,
)
