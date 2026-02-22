"""
Coordinate Team
---------------

Chair (Gemini) dynamically orchestrates analysts based on the question.
Best for: open-ended investment questions.

Agno equivalent: TeamMode.coordinate
"""

from framework.models import Gemini
from framework.team import Team

from ..agents import (
    financial_analyst,
    knowledge_agent,
    market_analyst,
    memo_writer,
    risk_officer,
    technical_analyst,
)


coordinate_team = Team(
    id="coordinate-team",
    name="Investment Team - Coordinate",
    description="Chair dynamically orchestrates analysts based on the question. Best for open-ended investment questions.",
    model=Gemini("gemini-2.5-flash"),
    members=[
        market_analyst,
        financial_analyst,
        technical_analyst,
        risk_officer,
        knowledge_agent,
        memo_writer,
    ],
    instructions=(
        "You are the Committee Chair of a $10M investment team.\n"
        "Dynamically decide which analysts to consult based on the question.\n"
        "For investment evaluations: start with Financial + Market analysts, then Risk, then Memo Writer.\n"
        "Always consult the Risk Officer before making allocation decisions.\n"
        "Provide a final recommendation with a specific dollar allocation.\n"
        "Ensure all decisions comply with the fund mandate."
    ),
)
