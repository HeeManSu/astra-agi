"""
Challenge Team
--------------
Sequential critique and risk validation.
Pipeline stage 2 of 4.
Order: Devil's Advocate → Risk Officer
"""

from agno.models.google import Gemini
from agno.team import Team, TeamMode

from agents import devils_advocate, risk_officer
from db import db


challenge_team = Team(
    id="challenge-team",
    db=db,
    name="Challenge Team",
    description="Attacks the investment thesis and validates risk compliance. Devil's Advocate → Risk Officer.",
    mode=TeamMode.coordinate,
    model=Gemini(id="gemini-2.5-flash", thinking_budget=0, include_thoughts=False, temperature=0.0),
    members=[
        devils_advocate,
        risk_officer,
    ],
    instructions="""\
You are the Challenge Director. Your job is to stress-test the investment thesis.

EXECUTION ORDER (strict):
1. Devil's Advocate — attacks the thesis. Finds weak assumptions, hidden risks,
   over-optimism, macro contradictions, and valuation fragility.
2. Risk Officer — checks mandate compliance, position sizing rules, beta limits,
   sector caps, drawdown risk, and correlation impact.

RULES:
- Devil's Advocate runs FIRST. Its critique must be available to the Risk Officer.
- The Risk Officer should factor in the Devil's weaknesses when assessing risk.
- Neither agent proposes alternatives or modifies the thesis.
- Devil attacks. Risk quantifies. That is the separation of duties.
- Do NOT soften or summarize their findings. Present them as raw as given.

FINAL OUTPUT:
Compile both outputs into a challenge report:

1. DEVIL'S ADVOCATE CRITIQUE
   - Core weaknesses, hidden assumptions, worst-case scenario, fragility score

2. RISK ASSESSMENT
   - Risk metrics, mandate compliance, sector impact, recommended max position size

This report will be consumed by the Allocation Team and Committee Chair.""",
    show_members_responses=False,
    markdown=False,
)