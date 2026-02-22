"""
Route Team
----------

Routes each question to exactly one specialist.
Best for: quick, targeted questions.

Agno equivalent: TeamMode.route
"""

from framework.models import Gemini
from framework.team import Team

from ..agents import (
    committee_chair,
    financial_analyst,
    knowledge_agent,
    market_analyst,
    memo_writer,
    risk_officer,
    technical_analyst,
)


route_team = Team(
    id="route-team",
    name="Investment Team - Route",
    description="Routes each question to exactly one specialist. Best for quick, targeted questions.",
    model=Gemini("gemini-2.5-flash"),
    members=[
        market_analyst,
        financial_analyst,
        technical_analyst,
        risk_officer,
        knowledge_agent,
        memo_writer,
        committee_chair,
    ],
    instructions=(
        "Route each question to exactly one specialist:\n"
        "- Macro/sector/news questions → Market Analyst\n"
        "- Fundamentals/valuation/financials → Financial Analyst\n"
        "- Price action/charts/momentum → Technical Analyst\n"
        "- Risk/downside/position sizing → Risk Officer\n"
        "- Research/past analysis/company deep dives → Knowledge Agent\n"
        "- Write a memo → Memo Writer\n"
        "- Final decisions/allocations → Committee Chair"
    ),
)
