import os
import sys

from dotenv import load_dotenv


env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from framework.agents import Agent
from framework.models import Gemini
from tools import brave_mcp, duckduckgo_mcp, github_mcp, notion_mcp
from tools.support_tools import (
    classify_churn_risk,
    compute_backlog_pressure,
    compute_customer_health,
    draft_resolution_steps,
    estimate_resolution_effort,
    generate_qbr_outline,
    predict_sla_breach,
    prioritize_support_ticket,
    route_ticket_queue,
    suggest_escalation_path,
    suggest_success_playbook,
    summarize_account_risks,
)


model = Gemini("gemini-2.5-flash")


CUSTOMER_SUCCESS_TOOLS = [
    prioritize_support_ticket,
    draft_resolution_steps,
    compute_customer_health,
    classify_churn_risk,
    estimate_resolution_effort,
    generate_qbr_outline,
    suggest_success_playbook,
    route_ticket_queue,
    predict_sla_breach,
    compute_backlog_pressure,
    suggest_escalation_path,
    summarize_account_risks,
    brave_mcp,
    duckduckgo_mcp,
    github_mcp,
    notion_mcp,
]


ticket_triage_agent = Agent(
    id="support-ticket-triage",
    name="Support Ticket Triage",
    model=model,
    description="Prioritizes incoming issues and SLA urgency.",
    instructions="Classify severity, set SLA, and identify cases requiring escalation.",
    tools=CUSTOMER_SUCCESS_TOOLS,
)


solution_planner_agent = Agent(
    id="support-solution-planner",
    name="Support Solution Planner",
    model=model,
    description="Builds resolution plans for complex incidents.",
    instructions="Generate practical resolution steps and identify responsible teams.",
    tools=CUSTOMER_SUCCESS_TOOLS,
)


health_monitor_agent = Agent(
    id="customer-health-monitor",
    name="Customer Health Monitor",
    model=model,
    description="Tracks account health and churn risk signals.",
    instructions="Compute account health score and propose retention actions.",
    tools=CUSTOMER_SUCCESS_TOOLS,
)


escalation_manager_agent = Agent(
    id="support-escalation-manager",
    name="Escalation Manager",
    model=model,
    description="Owns high-priority escalations end-to-end.",
    instructions="Coordinate P1/P2 support escalations and provide leadership-ready updates.",
    tools=CUSTOMER_SUCCESS_TOOLS,
)


__all__ = [
    "escalation_manager_agent",
    "health_monitor_agent",
    "solution_planner_agent",
    "ticket_triage_agent",
]
