"""
Technical Analyst
-----------------
Analyzes price action and momentum only.

Does NOT:
- Discuss fundamentals
- Discuss valuation
- Discuss macro
"""

from framework.agents import Agent
from framework.models import Gemini

from ..tools.technical_tools import TECHNICAL_ALL_TOOLS
from .settings import datetime_context


instructions = (
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


technical_analyst = Agent(
    id="technical-analyst",
    name="Technical Analyst",
    model=Gemini("gemini-2.5-flash", thinking_budget=0, include_thoughts=False),
    instructions=instructions,
    tools=TECHNICAL_ALL_TOOLS,
    code_mode=False,
)
