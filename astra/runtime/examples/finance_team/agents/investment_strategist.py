import os

from dotenv import load_dotenv


# Load .env from project root before creating Gemini model
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

from framework.agents import Agent
from framework.models import Gemini
from framework.tool.mcp import presets


model = Gemini("gemini-2.5-flash")

# MCP Toolkits from presets
brave_mcp = presets.brave_search(os.getenv("BRAVE_API_KEY", ""))
# Accept either NOTION_TOKEN or NOTION_API_KEY
notion_token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY", "")
notion_mcp = presets.notion(notion_token)


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
    ],
)
