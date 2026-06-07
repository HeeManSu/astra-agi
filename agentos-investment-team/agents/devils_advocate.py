"""
Devil's Advocate
----------------
Attacks the investment thesis. No tools — pure reasoning.
"""

from agno.agent import Agent
from agno.models.google import Gemini

from context import load_context
from db import db


DEVIL_CONTEXT = load_context(
    [
        "mandate.md",
        "process.md",
    ]
)

instructions = (
    DEVIL_CONTEXT
    + """
You are the Devil's Advocate.

Your role is to challenge the investment thesis.

You must:
- Identify weak assumptions
- Highlight macro contradictions
- Expose valuation fragility
- Question growth sustainability
- Identify risk concentration

You do NOT propose alternatives.
You only attack the thesis.

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

1. Core Weaknesses (Top 5)
2. Hidden Assumptions
3. Worst-Case Scenario
4. Thesis Break Conditions
5. Overall Fragility Score (1-10)

--------------------------------------------------

Be ruthless.
Be specific.
Use evidence from prior analyses.
"""
)

devils_advocate = Agent(
    id="devils-advocate",
    db=db,
    name="Devils Advocate",
    model=Gemini(id="gemini-2.5-flash", thinking_budget=0, include_thoughts=False, temperature=0.0),
    instructions=instructions,
    tools=[],
    add_datetime_to_context=True,
    markdown=False,
)