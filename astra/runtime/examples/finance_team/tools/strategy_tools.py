"""
Strategy Tools for Finance Team.

Tools for risk assessment, investment thesis generation, and strategy backtesting.
"""

import random

from framework.tool import ToolSpec, bind_tool
from pydantic import BaseModel, Field


# CALCULATE RISK SCORE TOOL
class CalculateRiskScoreInput(BaseModel):
    """Input for risk score calculation."""

    portfolio_allocation: str = Field(
        description='JSON string describing portfolio allocation (e.g., {"AAPL": 0.5, "GOOGL": 0.5})'
    )


class CalculateRiskScoreOutput(BaseModel):
    """Output from risk score calculation."""

    assessment: str = Field(description="Risk score and detailed assessment")


CALCULATE_RISK_SCORE_SPEC = ToolSpec(
    name="calculate_risk_score",
    description="Calculate the risk score of a given portfolio allocation",
    input_model=CalculateRiskScoreInput,
    output_model=CalculateRiskScoreOutput,
    examples=[
        {
            "input": {"portfolio_allocation": '{"AAPL": 0.5, "GOOGL": 0.5}'},
            "output": {
                "assessment": "Risk Score: 7.5/10 (High Volatility) - Concentration in technology sector increases beta exposure."
            },
        }
    ],
)


@bind_tool(CALCULATE_RISK_SCORE_SPEC)
async def calculate_risk_score(input: CalculateRiskScoreInput) -> CalculateRiskScoreOutput:
    """
    Calculate portfolio risk score on a 0-10 scale.

    Constraints:
    - Portfolio allocation must sum to 1.0
    - Simplified risk model for demo

    Notes:
    - Use for portfolio risk assessment
    - Advanced risk modeling in production

    Tags: risk-management, portfolio, strategy
    """
    result = "Risk Score: 7.5/10 (High Volatility) - Concentration in technology sector increases beta exposure."

    return CalculateRiskScoreOutput(assessment=result)


# GENERATE INVESTMENT THESIS TOOL
class GenerateInvestmentThesisInput(BaseModel):
    """Input for investment thesis generation."""

    symbol: str = Field(description="Stock ticker symbol")
    recommendation: str = Field(description="Investment recommendation (Buy, Sell, Hold)")


class GenerateInvestmentThesisOutput(BaseModel):
    """Output from investment thesis generation."""

    thesis: str = Field(description="Formatted investment thesis document")


GENERATE_INVESTMENT_THESIS_SPEC = ToolSpec(
    name="generate_investment_thesis",
    description="Generate a formatted investment thesis document",
    input_model=GenerateInvestmentThesisInput,
    output_model=GenerateInvestmentThesisOutput,
    examples=[
        {
            "input": {"symbol": "AAPL", "recommendation": "Buy"},
            "output": {
                "thesis": "INVESTMENT THESIS FOR AAPL\\nRECOMMENDATION: BUY\\n\\nRationale:\\nBased on strong earnings growth and favorable market conditions..."
            },
        }
    ],
)


@bind_tool(GENERATE_INVESTMENT_THESIS_SPEC)
async def generate_investment_thesis(
    input: GenerateInvestmentThesisInput,
) -> GenerateInvestmentThesisOutput:
    """
    Generate structured investment thesis document.

    Constraints:
    - Recommendation must be: Buy, Sell, or Hold
    - Includes rationale section

    Notes:
    - Use for presenting investment ideas
    - Template-based generation

    Tags: investment-thesis, documentation, strategy
    """
    result = f"INVESTMENT THESIS FOR {input.symbol}\\nRECOMMENDATION: {input.recommendation.upper()}\\n\\nRationale:\\nBased on strong earnings growth and favorable market conditions..."

    return GenerateInvestmentThesisOutput(thesis=result)


# BACKTEST STRATEGY TOOL
class BacktestStrategyInput(BaseModel):
    """Input for strategy backtesting."""

    strategy_name: str = Field(description="Name of the strategy (e.g., Momentum, Value)")
    duration_months: int = Field(default=12, description="Number of months to backtest")


class BacktestStrategyOutput(BaseModel):
    """Output from strategy backtest."""

    strategy: str = Field(description="Strategy name")
    duration_months: int = Field(description="Backtest duration")
    annualized_return_percent: float = Field(description="Annualized return percentage")
    max_drawdown_percent: float = Field(description="Maximum drawdown percentage")
    sharpe_ratio: float = Field(description="Sharpe ratio")


BACKTEST_STRATEGY_SPEC = ToolSpec(
    name="backtest_strategy",
    description="Run a simulation backtest for a given investment strategy",
    input_model=BacktestStrategyInput,
    output_model=BacktestStrategyOutput,
    examples=[
        {
            "input": {"strategy_name": "Momentum", "duration_months": 12},
            "output": {
                "strategy": "Momentum",
                "duration_months": 12,
                "annualized_return_percent": 15.75,
                "max_drawdown_percent": 8.5,
                "sharpe_ratio": 1.85,
            },
        }
    ],
)


@bind_tool(BACKTEST_STRATEGY_SPEC)
async def backtest_strategy(input: BacktestStrategyInput) -> BacktestStrategyOutput:
    """
    Run historical backtest simulation for investment strategy.

    Constraints:
    - Maximum 60 months backtest period
    - Returns simulated results for demo

    Notes:
    - Use for strategy validation
    - Real historical data in production

    Tags: backtesting, strategy-validation, performance
    """
    return_val = round(random.uniform(5, 25), 2)
    drawdown = round(random.uniform(2, 15), 2)
    sharpe = round(random.uniform(0.5, 2.5), 2)

    return BacktestStrategyOutput(
        strategy=input.strategy_name,
        duration_months=input.duration_months,
        annualized_return_percent=return_val,
        max_drawdown_percent=drawdown,
        sharpe_ratio=sharpe,
    )
