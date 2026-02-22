"""
Broadcast Team
--------------

All four analysts evaluate simultaneously, then Chair synthesizes.
Best for: high-stakes allocation decisions.

Agno equivalent: TeamMode.broadcast
"""

from framework.models import Gemini
from framework.team import Team

from ..agents import (
    financial_analyst,
    market_analyst,
    risk_officer,
    technical_analyst,
)


broadcast_team = Team(
    id="broadcast-team",
    name="Investment Team - Broadcast",
    description="All four analysts evaluate simultaneously, then synthesizes. Best for high-stakes decisions.",
    model=Gemini("gemini-2.5-flash"),
    members=[
        market_analyst,
        financial_analyst,
        technical_analyst,
        risk_officer,
    ],
    instructions=(
        "You are the Committee Chair synthesizing independent analyst views.\n"
        "Send the question to ALL analysts simultaneously and collect their independent evaluations.\n"
        "Synthesize their perspectives into a unified recommendation.\n"
        "Note where analysts agree and disagree.\n"
        "Provide a final BUY/HOLD/PASS decision with a specific dollar allocation.\n"
        "Weight the Risk Officer's concerns heavily in position sizing."
    ),
)
