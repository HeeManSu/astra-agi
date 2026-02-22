"""
Market Analyst
--------------

Macro environment, sector trends, and breaking news.
Tools: YFinance (market data) + optional Exa MCP (web search).
"""

from framework.agents import Agent
from framework.models import Gemini

from ..context import COMMITTEE_CONTEXT
from ..tools import YFINANCE_ALL_TOOLS
from .settings import EXA_API_KEY, datetime_context


instructions = (
    datetime_context()
    + f"""\
You are the Market Analyst on a $10M investment team.

## Committee Rules (ALWAYS FOLLOW)

{COMMITTEE_CONTEXT}

## Your Role

You assess the macro environment, identify sector trends, and surface market news
that could impact investment decisions.

### What You Do

- Assess the macro environment (interest rates, GDP, market sentiment)
- Identify sector tailwinds and headwinds
- Surface recent news that could impact the investment thesis
- Provide a market context score: **Bullish** / **Neutral** / **Bearish**

## Workflow

1. Always search learnings before analysis for relevant patterns and past insights.
2. Use Exa web search for recent news and market developments.
3. Use YFinance for sector indices and market data.
4. Save any new patterns, corrections, or insights as learnings.
5. Provide your assessment with a clear market context score.
"""
)

tools: list = list(YFINANCE_ALL_TOOLS)

# Optional: add Exa MCP web search if EXA_API_KEY is set
if EXA_API_KEY:
    from framework.tool.mcp.presets import exa

    tools.insert(0, exa(EXA_API_KEY))

market_analyst = Agent(
    id="market-analyst",
    name="Market Analyst",
    model=Gemini("gemini-2.5-flash"),
    instructions=instructions,
    tools=tools,
    code_mode=True,
)
