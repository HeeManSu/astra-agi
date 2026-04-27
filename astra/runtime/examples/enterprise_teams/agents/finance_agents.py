import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv


env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

from framework.agents import Agent
from framework.models import Gemini
from tools import (
    brave_mcp,
    duckduckgo_mcp,
    github_mcp,
    notion_mcp,
)
from tools.finance_tools import (
    assess_vendor_risk,
    compute_profit_margin,
    compute_working_capital,
    detect_expense_anomaly,
    evaluate_budget_variance,
    evaluate_cost_center_health,
    forecast_cash_flow,
    model_revenue_scenario,
    plan_capex_priority,
    rank_investment_projects,
    score_credit_exposure,
    summarize_finance_kpis,
)


model = Gemini("gemini-2.5-flash")


FINANCE_TOOLS = [
    evaluate_budget_variance,
    forecast_cash_flow,
    assess_vendor_risk,
    compute_working_capital,
    score_credit_exposure,
    detect_expense_anomaly,
    plan_capex_priority,
    model_revenue_scenario,
    compute_profit_margin,
    evaluate_cost_center_health,
    rank_investment_projects,
    summarize_finance_kpis,
    brave_mcp,
    duckduckgo_mcp,
    github_mcp,
    notion_mcp,
]


finance_forecaster_agent = Agent(
    id="finance-forecaster",
    name="Finance Forecaster",
    model=model,
    description="Forecasts runway and cash flow scenarios.",
    instructions="Estimate cash runway, detect budget drift, and summarize near-term liquidity actions.",
    tools=FINANCE_TOOLS,
)


procurement_risk_agent = Agent(
    id="procurement-risk-analyst",
    name="Procurement Risk Analyst",
    model=model,
    description="Evaluates vendor concentration and SLA risk.",
    instructions="Assess supplier risk, highlight critical vendors, and propose mitigation plans.",
    tools=FINANCE_TOOLS,
)


finance_reporter_agent = Agent(
    id="finance-reporter",
    name="Finance Reporter",
    model=model,
    description="Converts analysis into executive-ready summaries.",
    instructions="Create concise finance narratives and persist final reports in Notion.",
    tools=FINANCE_TOOLS,
)


treasury_control_agent = Agent(
    id="treasury-control",
    name="Treasury Control",
    model=model,
    description="Monitors liquidity controls and vendor exposure.",
    instructions="Review liquidity risk signals and flag decisions requiring executive review.",
    tools=FINANCE_TOOLS,
)


__all__ = [
    "finance_forecaster_agent",
    "finance_reporter_agent",
    "procurement_risk_agent",
    "treasury_control_agent",
]
