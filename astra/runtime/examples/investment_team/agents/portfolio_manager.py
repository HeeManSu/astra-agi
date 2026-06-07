"""
Portfolio Manager
-----------------
Capital allocator. Uses conviction scores, risk assessment, sector exposure,
and cash availability to determine allocation.
"""

from framework.agents import Agent
from framework.models import Gemini

from ..context import load_context
from ..tools.portfolio_tools import PORTFOLIO_ALL_TOOLS
from .settings import datetime_context


PM_CONTEXT = load_context(
    [
        "mandate.md",
        "risk_policy.md",
        "sector_guidelines.md",
        "scoring_framework.md",
    ]
)


instructions = (
    datetime_context()
    + PM_CONTEXT
    + """
You are the Portfolio Manager.

You allocate capital based on:

- Conviction scores
- Risk assessment
- Sector exposure limits
- Portfolio beta limits
- Cash reserve requirement

You must respect:
- Maximum 15 positions
- 5% minimum cash
- Sector caps
- Position size rules

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

1. Allocation Rationale
2. Portfolio Impact
3. Proposed Position Size (% and $)
4. Post-Allocation Portfolio Beta
5. Compliance Confirmation

--------------------------------------------------

Be disciplined.
Be quantitative.
Show your math.
"""
)


portfolio_manager = Agent(
    id="portfolio-manager",
    name="Portfolio Manager",
    model=Gemini("gemini-2.5-flash", thinking_budget=0, include_thoughts=False),
    instructions=instructions,
    tools=PORTFOLIO_ALL_TOOLS,
    code_mode=False,
)
