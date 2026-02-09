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


earning_agent = Agent(
    name="Earnings Researcher",
    model=model,
    description="Research company earnings and financial reports.",
    instructions="\n".join(
        [
            "You are a meticulous financial researcher.",
            "Use 'brave_web_search' to find the most recent quarterly earnings and financial insights for the company.",
            "Summarize the findings and use 'API-patch-block-children' to save them to the 'Market Research' page (ID: 2ffbd5030ea680b791e1ca41a59c1765).",
            "CRITICAL: Notion character limit 2,000. Summarize outputs.",
            "NOTION SCHEMA: Use {'type': 'paragraph', 'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': '...'}}]}}",
        ]
    ),
    tools=[
        brave_mcp,
        notion_mcp,
    ],
)
