"""
AgentOS entrypoint for the Investment Committee.

Registers all eight analysts plus the four sub-teams and the master pipeline
team under a single AgentOS app. Run with:

    uv run python agentos.py

Then open http://localhost:7777/config to inspect the registered agents and
teams, or use the AgentOS UI / API to invoke them.
"""

from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root before any agno/Gemini client is constructed.
load_dotenv(Path(__file__).resolve().parent / ".env", override=False)

from agno.os import AgentOS

from agents import (
    committee_chair,
    devils_advocate,
    financial_analyst,
    macro_strategist,
    portfolio_manager,
    risk_officer,
    technical_analyst,
    valuation_analyst,
)
from teams import (
    allocation_team,
    challenge_team,
    investment_committee_team,
    pipeline_team,
    research_team,
)


agent_os = AgentOS(
    id="agno-investment-committee",
    name="Agno Investment Committee",
    description=(
        "Institutional investment committee built on Agno. Eight specialist "
        "agents (macro, financial, valuation, technical, devil's advocate, "
        "risk officer, portfolio manager, committee chair) coordinated by "
        "four sub-teams (Research, Challenge, Allocation, Committee) plus a "
        "master Pipeline team that runs them end-to-end for a single symbol."
    ),
    agents=[
        macro_strategist,
        financial_analyst,
        valuation_analyst,
        technical_analyst,
        devils_advocate,
        risk_officer,
        portfolio_manager,
        committee_chair,
    ],
    teams=[
        research_team,
        challenge_team,
        allocation_team,
        investment_committee_team,
        pipeline_team,
    ],
)

app = agent_os.get_app()


if __name__ == "__main__":
    agent_os.serve(app="agentos:app", port=7777, reload=True)
