"""
Macro Strategist — AutoGen version.

Core backstory text is identical to the Astra/Agno/CrewAI sides. AutoGen
adds a small TEAM_CONTEXT footer (see settings.py) because its
`SelectorGroupChat` passes the raw user query through, whereas the other
frameworks' managers reframe compound queries into per-analyst sub-tasks
before delegating; the footer restores that parity. AutoGen's
`AssistantAgent` takes the same prompt as a
`system_message` and the same tools as plain Python functions.
"""

from autogen_agentchat.agents import AssistantAgent

from context import load_context
from tools.macro_tools import MACRO_ALL_TOOLS

from .settings import TEAM_CONTEXT, datetime_context, make_model_client


MACRO_CONTEXT = load_context(["mandate.md", "risk_policy.md"])


SYSTEM_MESSAGE = (
    datetime_context()
    + MACRO_CONTEXT
    + TEAM_CONTEXT
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


macro_strategist = AssistantAgent(
    name="MacroStrategist",
    model_client=make_model_client(),
    tools=MACRO_ALL_TOOLS,
    system_message=SYSTEM_MESSAGE,
    description="Assesses macroeconomic regime and equity risk environment (rates, inflation, growth, liquidity, yield curve).",
    reflect_on_tool_use=True,
    max_tool_iterations=15,
)
