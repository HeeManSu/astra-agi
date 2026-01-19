import os

from dotenv import load_dotenv


# Load .env from project root before creating Gemini model
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

from framework.agents import Agent
from framework.models import Gemini
from tools import research_tools


model = Gemini("gemini-2.5-flash")


earning_agent = Agent(
    name="Earnings Researcher",
    model=model,
    description="Research company earnings and financial reports. Extracts key metrics like EPS, Revenue, and Guidance.",
    instructions="\n".join(
        [
            "You are a meticulous financial researcher.",
            "Focus on analyzing quarterly earnings reports and 10-K filings.",
            "Use 'get_earnings_report' to find specific financial data.",
            "Use 'search_sec_filings' to find official documents.",
            "Use 'get_competitor_analysis' to benchmark against peers.",
            "Extract key metrics like EPS, Revenue, and Guidance.",
        ]
    ),
    tools=[
        research_tools.get_earnings_report,
        research_tools.search_sec_filings,
        research_tools.get_competitor_analysis,
    ],
)
