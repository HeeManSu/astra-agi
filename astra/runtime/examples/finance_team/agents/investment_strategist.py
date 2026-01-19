import os

from dotenv import load_dotenv


# Load .env from project root before creating Gemini model
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.env"))
load_dotenv(env_path, override=True)

from framework.agents import Agent
from framework.models import Gemini
from tools import strategy_tools


model = Gemini("gemini-2.5-flash")


investment_agent = Agent(
    name="Investment Strategist",
    model=model,
    description="Develops investment strategies based on analysis. Provides risk-adjusted recommendations (Buy, Sell, Hold).",
    instructions="\n".join(
        [
            "You are a senior investment strategist.",
            "Combine market analysis and earnings research to form actionable strategies.",
            "Use 'calculate_risk_score' to assess portfolio risk.",
            "Use 'backtest_strategy' to validate your strategy before recommending.",
            "Use 'generate_investment_thesis' to write your final recommendation.",
            "Provide risk-adjusted recommendations (Buy, Sell, Hold).",
        ]
    ),
    tools=[
        strategy_tools.calculate_risk_score,
        strategy_tools.generate_investment_thesis,
        strategy_tools.backtest_strategy,
    ],
)
