"""
Devil's Advocate
----------------
Attacks the investment thesis. Finds hidden assumptions, over-optimism,
macro contradictions, valuation fragility, and technical weakness.

No tools -- pure reasoning over prior agent outputs.
"""

from framework.agents import Agent
from framework.models import Gemini

from context import load_context
from config import DISABLED_MEMORY
from .settings import datetime_context


DEVIL_CONTEXT = load_context(
    [
        "mandate.md",
        "process.md",
    ]
)


instructions = (
    datetime_context()
    + DEVIL_CONTEXT
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
    name="Devils Advocate",
    model=Gemini("gemini-2.5-flash", thinking_budget=0, include_thoughts=False),
    instructions=instructions,
    tools=[],
    code_mode=False,
    memory=DISABLED_MEMORY,
)
