import os

from dotenv import load_dotenv


# Load .env from project root before creating Gemini model
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

from framework.agents import Agent
from framework.models import Gemini
from tools import market_tools


model = Gemini("gemini-2.5-flash")


market_agent = Agent(
    name="Market Analyst",
    model=model,
    description="Analyzes market trends and stock data. Focuses on technical analysis and macro-economic factors.",
    instructions="\n".join(
        [
            "You are an expert market analyst.",
            "Your goal is to provide deep insights into market trends.",
            "Use the 'get_stock_price' tool to check current valuations.",
            "Use 'get_market_news' to understand the macro environment.",
            "Focus on technical analysis and macro-economic factors.",
        ]
    ),
    tools=[market_tools.get_stock_price, market_tools.get_market_news],
)
