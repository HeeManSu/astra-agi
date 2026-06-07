"""
Technical Analyst
-----------------
Analyzes price action and momentum only.
"""

from agno.agent import Agent
from agno.models.google import Gemini

from tools.technical_tools import TECHNICAL_ALL_TOOLS
from db import db


instructions = """
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

technical_analyst = Agent(
    id="technical-analyst",
    db=db,
    name="Technical Analyst",
    model=Gemini(id="gemini-2.5-flash", thinking_budget=0, include_thoughts=False, temperature=0.0),
    instructions=instructions,
    tools=TECHNICAL_ALL_TOOLS,
    add_datetime_to_context=True,
    markdown=False,
    # Memory off (paper §4.4 disclosure — matches Agno defaults, set explicitly).
    enable_agentic_memory=False,
    add_history_to_context=False,
)