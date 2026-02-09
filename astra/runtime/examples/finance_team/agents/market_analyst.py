import os

from dotenv import load_dotenv


# Load .env from project root before creating Gemini model
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

from framework.agents import Agent
from framework.models import Gemini
from framework.tool.mcp import presets


# Debug: Verify .env loading
notion_key = os.getenv("NOTION_API_KEY", "")
print(f"DEBUG [MarketAnalyst]: Notion Key found (length={len(notion_key.strip())})")
if notion_key:
    print(f"DEBUG [MarketAnalyst]: Key starts with: {notion_key.strip()[:7]}...")

# Fix: Ensure tools is in path for relative import
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


model = Gemini("gemini-2.5-flash")

# MCP Toolkits from presets
brave_mcp = presets.brave_search(os.getenv("BRAVE_API_KEY", ""))
# Accept either NOTION_TOKEN or NOTION_API_KEY
notion_token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY", "")
notion_mcp = presets.notion(notion_token)


market_agent = Agent(
    name="Market Analyst",
    model=model,
    description="Analyzes market trends and macro-economic factors.",
    instructions="\n".join(
        [
            "You are an expert market analyst.",
            "Your first step MUST be to use 'brave_web_search' to find the latest news and stock price for the company.",
            "Then, use 'API-patch-block-children' to save a summary of current market conditions to the 'Market Research' page (ID: 2ffbd5030ea680b791e1ca41a59c1765).",
            "CRITICAL: Notion has a 2,000 character limit per block. Truncate search results to under 1,800 characters.",
            "NOTION SCHEMA: Use {'type': 'paragraph', 'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': '...'}}]}}",
        ]
    ),
    tools=[
        brave_mcp,
        notion_mcp,
    ],
)
