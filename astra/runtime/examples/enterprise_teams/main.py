"""Enterprise Teams example server.

This example expands the old finance-only setup into a multi-domain enterprise.
It includes:
- 5 teams
- 20 agents (4 per team)
- 15 local tools
- 5 shared MCP toolkits
"""

import os
import sys

from dotenv import load_dotenv
from framework.storage.client import StorageClient
from framework.storage.databases.mongodb import MongoDBStorage
from observability.storage.mongodb import TelemetryMongoDB
from runtime import AstraServer, TelemetryConfig


env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.env"))
load_dotenv(env_path, override=True)

sys.path.insert(0, os.path.dirname(__file__))

from agents import (
    brand_operations_agent,
    campaign_strategist_agent,
    change_manager_agent,
    escalation_manager_agent,
    finance_forecaster_agent,
    finance_reporter_agent,
    growth_analyst_agent,
    health_monitor_agent,
    incident_commander_agent,
    learning_partner_agent,
    market_research_agent,
    org_planner_agent,
    people_analyst_agent,
    procurement_risk_agent,
    recruiter_agent,
    reliability_engineer_agent,
    service_observer_agent,
    solution_planner_agent,
    ticket_triage_agent,
    treasury_control_agent,
)
from framework.models import Gemini
from framework.team import Team


team_model = Gemini("gemini-2.5-flash")


finance_team = Team(
    id="team-finance-ops",
    name="Finance Operations Team",
    description="Owns planning, treasury, and vendor risk controls.",
    model=team_model,
    members=[
        finance_forecaster_agent,
        procurement_risk_agent,
        finance_reporter_agent,
        treasury_control_agent,
    ],
    instructions="Coordinate cash forecasting, vendor-risk analysis, and executive finance reporting.",
)


marketing_team = Team(
    id="team-marketing-growth",
    name="Marketing Growth Team",
    description="Runs market analysis, campaigns, and growth optimization.",
    model=team_model,
    members=[
        market_research_agent,
        campaign_strategist_agent,
        growth_analyst_agent,
        brand_operations_agent,
    ],
    instructions="Convert market insight into campaigns and ROI-backed growth recommendations.",
)


customer_success_team = Team(
    id="team-customer-success",
    name="Customer Success Team",
    description="Handles ticket triage, health scoring, and escalations.",
    model=team_model,
    members=[
        ticket_triage_agent,
        solution_planner_agent,
        health_monitor_agent,
        escalation_manager_agent,
    ],
    instructions="Prioritize incidents, resolve blockers, and protect renewals using health signals.",
)


people_ops_team = Team(
    id="team-people-ops",
    name="People Operations Team",
    description="Supports hiring quality, interview planning, and skill development.",
    model=team_model,
    members=[
        recruiter_agent,
        learning_partner_agent,
        org_planner_agent,
        people_analyst_agent,
    ],
    instructions="Align hiring and enablement decisions with quarterly workforce goals.",
)


it_ops_team = Team(
    id="team-it-ops",
    name="IT Operations Team",
    description="Manages incident response and change safety.",
    model=team_model,
    members=[
        incident_commander_agent,
        reliability_engineer_agent,
        change_manager_agent,
        service_observer_agent,
    ],
    instructions="Run structured incident response and enforce safe production changes.",
)


all_agents = [
    finance_forecaster_agent,
    procurement_risk_agent,
    finance_reporter_agent,
    treasury_control_agent,
    market_research_agent,
    campaign_strategist_agent,
    growth_analyst_agent,
    brand_operations_agent,
    ticket_triage_agent,
    solution_planner_agent,
    health_monitor_agent,
    escalation_manager_agent,
    recruiter_agent,
    learning_partner_agent,
    org_planner_agent,
    people_analyst_agent,
    incident_commander_agent,
    reliability_engineer_agent,
    change_manager_agent,
    service_observer_agent,
]


all_teams = [
    finance_team,
    marketing_team,
    customer_success_team,
    people_ops_team,
    it_ops_team,
]


server = AstraServer(
    name="Astra Enterprise Teams Server",
    agents=all_agents,
    teams=all_teams,
    description="Multi-domain enterprise orchestration with 5 teams and shared MCP tooling.",
    storage=StorageClient(storage=MongoDBStorage("mongodb://localhost:27017", "enterprise_teams")),
    telemetry=TelemetryConfig(
        enabled=True,
        db_path=TelemetryMongoDB("mongodb://localhost:27017", "telemetry_enterprise_teams"),
        debug=True,
    ),
)


app = server.get_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
