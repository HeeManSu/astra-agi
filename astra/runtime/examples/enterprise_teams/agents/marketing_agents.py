import os
import sys

from dotenv import load_dotenv


env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from framework.agents import Agent
from framework.models import Gemini
from tools import brave_mcp, duckduckgo_mcp, github_mcp, notion_mcp
from tools.marketing_tools import (
    allocate_channel_budget,
    assess_landing_page_quality,
    build_campaign_brief,
    estimate_cac,
    estimate_campaign_roi,
    evaluate_brand_sentiment,
    forecast_pipeline_from_mql,
    generate_content_calendar,
    profile_audience_segment,
    recommend_creative_variant,
    score_channel_mix,
    summarize_campaign_kpis,
)


model = Gemini("gemini-2.5-flash")


MARKETING_TOOLS = [
    profile_audience_segment,
    build_campaign_brief,
    estimate_campaign_roi,
    generate_content_calendar,
    score_channel_mix,
    estimate_cac,
    evaluate_brand_sentiment,
    forecast_pipeline_from_mql,
    recommend_creative_variant,
    assess_landing_page_quality,
    allocate_channel_budget,
    summarize_campaign_kpis,
    brave_mcp,
    duckduckgo_mcp,
    github_mcp,
    notion_mcp,
]


market_research_agent = Agent(
    id="marketing-research",
    name="Marketing Researcher",
    model=model,
    description="Finds segments and channel opportunities.",
    instructions="Profile audience segments and collect market signals for campaign planning.",
    tools=MARKETING_TOOLS,
)


campaign_strategist_agent = Agent(
    id="campaign-strategist",
    name="Campaign Strategist",
    model=model,
    description="Designs campaign plans and messaging.",
    instructions="Draft campaign briefs with clear message hierarchy and CTA.",
    tools=MARKETING_TOOLS,
)


growth_analyst_agent = Agent(
    id="growth-analyst",
    name="Growth Analyst",
    model=model,
    description="Evaluates growth performance and expected ROI.",
    instructions="Estimate funnel outcomes and recommend budget optimization paths.",
    tools=MARKETING_TOOLS,
)


brand_operations_agent = Agent(
    id="brand-operations",
    name="Brand Operations",
    model=model,
    description="Ensures campaign execution quality and consistency.",
    instructions="Turn strategic campaign outputs into execution-ready briefs.",
    tools=MARKETING_TOOLS,
)


__all__ = [
    "brand_operations_agent",
    "campaign_strategist_agent",
    "growth_analyst_agent",
    "market_research_agent",
]
