import os
import sys

from dotenv import load_dotenv


env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from framework.agents import Agent
from framework.models import Gemini
from tools import brave_mcp, duckduckgo_mcp, github_mcp, notion_mcp
from tools.people_tools import (
    assess_attrition_risk,
    compute_hiring_velocity,
    detect_skills_coverage,
    estimate_offer_acceptance,
    evaluate_interviewer_load,
    identify_training_gaps,
    plan_headcount,
    plan_interview_panel,
    recommend_onboarding_plan,
    score_role_competitiveness,
    screen_candidate_profile,
    summarize_people_kpis,
)


model = Gemini("gemini-2.5-flash")


PEOPLE_OPS_TOOLS = [
    screen_candidate_profile,
    plan_interview_panel,
    identify_training_gaps,
    compute_hiring_velocity,
    estimate_offer_acceptance,
    assess_attrition_risk,
    plan_headcount,
    evaluate_interviewer_load,
    score_role_competitiveness,
    recommend_onboarding_plan,
    detect_skills_coverage,
    summarize_people_kpis,
    brave_mcp,
    duckduckgo_mcp,
    github_mcp,
    notion_mcp,
]


recruiter_agent = Agent(
    id="people-recruiter",
    name="Recruiter",
    model=model,
    description="Screens candidates and recommends next steps.",
    instructions="Evaluate candidate profiles against role requirements and shortlist quality.",
    tools=PEOPLE_OPS_TOOLS,
)


learning_partner_agent = Agent(
    id="people-learning-partner",
    name="Learning Partner",
    model=model,
    description="Owns capability development plans.",
    instructions="Identify training gaps and provide a practical enablement roadmap.",
    tools=PEOPLE_OPS_TOOLS,
)


org_planner_agent = Agent(
    id="people-org-planner",
    name="Org Planner",
    model=model,
    description="Aligns hiring and skills with quarterly goals.",
    instructions="Map skills supply-demand and recommend hiring or upskilling actions.",
    tools=PEOPLE_OPS_TOOLS,
)


people_analyst_agent = Agent(
    id="people-analyst",
    name="People Analyst",
    model=model,
    description="Produces workforce decision support analytics.",
    instructions="Generate concise workforce insights with hiring panel and competency recommendations.",
    tools=PEOPLE_OPS_TOOLS,
)


__all__ = [
    "learning_partner_agent",
    "org_planner_agent",
    "people_analyst_agent",
    "recruiter_agent",
]
