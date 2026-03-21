"""
Risk Officer
------------
Enforces mandate + risk rules. Checks position size, beta, correlation,
drawdown risk, and sector cap compliance.
"""

from framework.agents import Agent
from framework.models import Gemini

from ..context import load_context
from ..tools.risk_tools import RISK_ALL_TOOLS
from .settings import datetime_context


RISK_CONTEXT = load_context(
    [
        "mandate.md",
        "risk_policy.md",
        "sector_guidelines.md",
    ]
)


instructions = (
    datetime_context()
    + RISK_CONTEXT
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
    name="Risk Officer",
    model=Gemini("gemini-2.5-flash", thinking_budget=0, include_thoughts=False),
    instructions=instructions,
    tools=RISK_ALL_TOOLS,
    code_mode=False,
)
