"""
Risk Officer
------------
Enforces mandate + risk rules.
"""

from agno.agent import Agent
from agno.models.google import Gemini

from context import load_context
from tools.risk_tools import RISK_ALL_TOOLS
from db import db


RISK_CONTEXT = load_context(
    [
        "mandate.md",
        "risk_policy.md",
        "sector_guidelines.md",
    ]
)

instructions = (
    RISK_CONTEXT
    + """
You are the Risk Officer.

Your responsibility is capital preservation.

You must evaluate:

- Beta exposure
- Volatility profile
- Correlation impact
- Position size compliance
- Sector cap compliance
- Drawdown risk

You may veto position size if rules are violated.

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

1. Risk Metrics Summary
2. Mandate Compliance Check
3. Sector Impact
4. Portfolio Impact
5. Recommended Max Position Size
6. Risk Score (1-10)

--------------------------------------------------

Be conservative.
Be precise.
Flag all violations.
"""
)

risk_officer = Agent(
    id="risk-officer",
    db=db,
    name="Risk Officer",
    model=Gemini(id="gemini-2.5-flash", thinking_budget=0, include_thoughts=False, temperature=0.0),
    instructions=instructions,
    tools=RISK_ALL_TOOLS,
    add_datetime_to_context=True,
    markdown=False,
)