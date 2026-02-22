import os
import sys

from dotenv import load_dotenv


env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from framework.agents import Agent
from framework.models import Gemini
from tools import brave_mcp, duckduckgo_mcp, github_mcp, notion_mcp
from tools.it_tools import (
    assess_release_risk,
    calculate_error_budget,
    classify_incident_severity,
    draft_postmortem_summary,
    estimate_capacity_headroom,
    estimate_mttr_improvement,
    evaluate_monitoring_coverage,
    generate_runbook_tasks,
    map_incident_dependencies,
    prioritize_remediation_items,
    summarize_service_reliability,
    validate_change_window,
)


model = Gemini("gemini-2.5-flash")


IT_OPS_TOOLS = [
    classify_incident_severity,
    generate_runbook_tasks,
    validate_change_window,
    calculate_error_budget,
    assess_release_risk,
    estimate_capacity_headroom,
    draft_postmortem_summary,
    map_incident_dependencies,
    evaluate_monitoring_coverage,
    prioritize_remediation_items,
    estimate_mttr_improvement,
    summarize_service_reliability,
    brave_mcp,
    duckduckgo_mcp,
    github_mcp,
    notion_mcp,
]


incident_commander_agent = Agent(
    id="it-incident-commander",
    name="Incident Commander",
    model=model,
    description="Leads active incident response.",
    instructions="Classify active incidents and execute first-response runbook actions.",
    tools=IT_OPS_TOOLS,
)


reliability_engineer_agent = Agent(
    id="it-reliability-engineer",
    name="Reliability Engineer",
    model=model,
    description="Maintains service reliability and recovery readiness.",
    instructions="Prepare and refine runbook responses and change safety decisions.",
    tools=IT_OPS_TOOLS,
)


change_manager_agent = Agent(
    id="it-change-manager",
    name="Change Manager",
    model=model,
    description="Approves operational changes based on risk windows.",
    instructions="Review maintenance windows and enforce change governance.",
    tools=IT_OPS_TOOLS,
)


service_observer_agent = Agent(
    id="it-service-observer",
    name="Service Observer",
    model=model,
    description="Monitors external signals for service degradation.",
    instructions="Track incident signals and provide concise health updates.",
    tools=IT_OPS_TOOLS,
)


__all__ = [
    "change_manager_agent",
    "incident_commander_agent",
    "reliability_engineer_agent",
    "service_observer_agent",
]
