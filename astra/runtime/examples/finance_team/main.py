import os
import sys

# CRITICAL: Load .env BEFORE any framework imports that might use API keys
from dotenv import load_dotenv
from runtime import AstraServer, TelemetryConfig


# Load env from project root (same as Agno example)
# This must happen before any framework imports
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.env"))
load_dotenv(env_path, override=True)  # override=True ensures it replaces any existing values


# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from agents import earning_agent, investment_agent, market_agent
from framework.models import Gemini
from framework.team import Team


# Initialize model for the team (using same config as agents)
model = Gemini("gemini-2.5-flash")

# Token usage tracking (without modifying framework code)
_token_usage_data = []


def _track_token_usage(original_invoke):
    """Wrapper to track token usage from model calls."""

    async def tracked_invoke(*args, **kwargs):
        response = await original_invoke(*args, **kwargs)
        if hasattr(response, "usage") and response.usage:
            _token_usage_data.append(response.usage.copy())
        return response

    return tracked_invoke


# Monkey-patch model.invoke to track usage
model.invoke = _track_token_usage(model.invoke)

# Create the Finance Team
finance_team = Team(
    id="finance-team",
    name="Hedge Fund Team",
    model=model,
    members=[market_agent, earning_agent, investment_agent],
    # storage=StorageClient(storage=MongoDBStorage("mongodb://localhost:27017", "finance_team")),
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
    teams=[finance_team],  # Register the team so it's available via API
    description="A server hosting a specialized Finance Team.",
    telemetry=TelemetryConfig(
        enabled=True,
        db_path="./finance_obs.db",
        debug=True,
    ),
)


# Token usage helper functions (defined before app setup)
def get_token_usage_summary() -> dict:
    """Get aggregated token usage summary."""
    if not _token_usage_data:
        return {
            "total_calls": 0,
            "total_input": 0,
            "total_output": 0,
            "total_thoughts": 0,
            "total_tokens": 0,
        }

    total_input = sum(usage.get("input_tokens", 0) for usage in _token_usage_data)
    total_output = sum(usage.get("output_tokens", 0) for usage in _token_usage_data)
    total_thoughts = sum(usage.get("thoughts_tokens", 0) for usage in _token_usage_data)
    total_tokens = sum(usage.get("total_tokens", 0) for usage in _token_usage_data)

    return {
        "total_calls": len(_token_usage_data),
        "total_input": total_input,
        "total_output": total_output,
        "total_thoughts": total_thoughts,
        "total_tokens": total_tokens,
    }


def print_token_usage_summary():
    """Print aggregated token usage summary."""
    summary = get_token_usage_summary()
    if summary["total_calls"] == 0:
        return

    print("\n" + "=" * 70)
    print("💰 TOTAL TOKEN USAGE SUMMARY (All API Calls)")
    print("=" * 70)
    print(f"  Total API Calls:        {summary['total_calls']:>6}")
    print(f"  Total Input Tokens:     {summary['total_input']:>6,}")
    print(f"  Total Output Tokens:    {summary['total_output']:>6,}")
    print(f"  Total Thoughts Tokens:  {summary['total_thoughts']:>6,}")
    print(f"  ⭐ TOTAL TOKENS:        {summary['total_tokens']:>6,}")
    print("=" * 70)
    print()


# Expose App
app = server.get_app()


# Add custom route to show token usage (without modifying framework)
@app.get("/token-usage")
async def get_token_usage():
    """Get current token usage summary."""
    from fastapi.responses import JSONResponse

    summary = get_token_usage_summary()
    return JSONResponse(content=summary)


# Add middleware to print token usage after team requests
@app.middleware("http")
async def print_token_usage_middleware(request, call_next):
    """Print token usage summary after team requests complete."""
    response = await call_next(request)

    # Print summary after team invoke/stream requests
    if request.url.path.startswith("/teams/") and request.method == "POST":
        # Small delay to ensure all model calls are tracked
        import asyncio

        await asyncio.sleep(0.1)
        print_token_usage_summary()

    return response


if __name__ == "__main__":
    import atexit

    import uvicorn

    # Register token usage summary to print on exit
    atexit.register(print_token_usage_summary)

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
