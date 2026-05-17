"""
Technical Analyst — AutoGen version.

Core backstory text is identical to the Astra/Agno/CrewAI sides. AutoGen
adds a small TEAM_CONTEXT footer (see settings.py) to restore parity with
the other frameworks' manager-driven query-reframing behavior, which
AutoGen's `SelectorGroupChat` does not provide.
"""

from autogen_agentchat.agents import AssistantAgent

from tools.technical_tools import TECHNICAL_ALL_TOOLS

from .settings import TEAM_CONTEXT, datetime_context, make_model_client


SYSTEM_MESSAGE = (
    datetime_context()
    + TEAM_CONTEXT
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


technical_analyst = AssistantAgent(
    name="TechnicalAnalyst",
    model_client=make_model_client(),
    tools=TECHNICAL_ALL_TOOLS,
    system_message=SYSTEM_MESSAGE,
    description="Analyzes price action, momentum, support/resistance, and trend structure.",
    reflect_on_tool_use=True,
    max_tool_iterations=15,
)
