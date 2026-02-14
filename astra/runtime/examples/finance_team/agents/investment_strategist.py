import os
import sys

from dotenv import load_dotenv


# Load .env from project root before creating Gemini model
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

# Ensure tools package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from framework.agents import Agent
from framework.models import Gemini

# Import SHARED MCP toolkit instances (avoids duplicate slug errors)
from tools import brave_mcp, notion_mcp
from tools.strategy_tools import backtest_strategy, calculate_risk_score, generate_investment_thesis


model = Gemini("gemini-2.5-flash")


investment_agent = Agent(
    name="Investment Strategist",
    model=model,
    description="Provides risk-adjusted recommendations (Buy, Sell, Hold).",
    instructions="\n".join(
        [
            "You are a senior investment strategist.",
            "Review the market conditions and earnings data provided by your team.",
            "If more data is needed, use 'brave_web_search' for final verification.",
            "Finalize a risk-adjusted recommendation (Buy, Sell, Hold).",
            "Use 'API-patch-block-children' to save the final Investment Thesis to Notion (ID: 2ffbd5030ea680b791e1ca41a59c1765).",
            "NOTION SCHEMA: Use {'type': 'paragraph', 'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': '...'}}]}}",
        ]
    ),
    tools=[
        brave_mcp,
        notion_mcp,
        calculate_risk_score,
        generate_investment_thesis,
        backtest_strategy,
    ],
)
