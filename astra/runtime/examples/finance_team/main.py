import os
import sys

# CRITICAL: Load .env BEFORE any framework imports that might use API keys
from dotenv import load_dotenv


# Load env from project root (same as Agno example)
# This must happen before any framework imports
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.env"))
load_dotenv(env_path, override=True)  # override=True ensures it replaces any existing values


# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from agents import earning_agent, investment_agent, market_agent
from framework.models import Gemini
from framework.team import Team
from runtime import AstraServer


# Initialize model for the team (using same config as agents)
model = Gemini("gemini-2.5-flash")

# Create the Finance Team
finance_team = Team(
    id="finance-team",
    name="Hedge Fund Team",
    model=model,
    members=[market_agent, earning_agent, investment_agent],
    # storage=AgentStorage(storage=MongoDBStorage("mongodb://localhost:27017", "finance_team")),
    description="A team of elite financial analysts and strategists working together to outperform the market.",
    instructions="\n".join(
        [
            "Collaborate to provide comprehensive investment reports.",
            "The Market Analyst provides the broad context.",
            "The Earnings Researcher provides company-specific data.",
            "The Investment Strategist synthesizes everything into a recommendation.",
        ]
    ),
)

# Create Server
server = AstraServer(
    name="Astra Finance Server",
    agents=[market_agent, earning_agent, investment_agent],
    # teams=[finance_team],
    description="A server hosting a specialized Finance Team.",
)

# Expose App
app = server.get_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


# Example User Queries for Finance Team

# example_queries = [
#     # 1. Single Stock Analysis - Comprehensive
#     "Should I invest in Apple (AAPL)? Provide a complete analysis including current market conditions, recent earnings, and a risk-adjusted recommendation.",
#     # 2. Sector Analysis with Multiple Stocks
#     "Analyze the technology sector and recommend the best investment opportunity. Compare at least 3 tech stocks and provide a detailed investment thesis for your top pick.",
#     # 3. Portfolio Risk Assessment
#     "I'm considering a portfolio with 40% AAPL, 30% GOOGL, and 30% MSFT. Analyze the market conditions, check recent earnings for these companies, and assess the portfolio risk. Should I proceed?",
#     # 4. Earnings-Driven Investment Decision
#     "Microsoft (MSFT) just reported strong Q4 earnings. Analyze the earnings report, check current market sentiment, and determine if this is a good entry point. Include competitor analysis.",
#     # 5. Market Timing Strategy
#     "Given the current market news in the technology sector, identify which tech stock would benefit most and provide a complete investment strategy with risk assessment.",
#     # 6. Comparative Analysis
#     "Compare Tesla (TSLA) and Ford (F) as investment opportunities. Include market analysis, earnings comparison, competitor positioning, and provide a clear recommendation on which to invest in.",
# ]
