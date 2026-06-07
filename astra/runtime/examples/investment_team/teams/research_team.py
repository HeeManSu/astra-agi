"""
Research Team
-------------

Sequential coordination of the four research analysts.
Produces a comprehensive research packet for one symbol.

Pipeline stage 1 of 4.
Order: Macro Strategist → Financial Analyst → Valuation Analyst → Technical Analyst
"""

from framework.models import Gemini
from framework.team import Team

from ..agents import (
    financial_analyst,
    macro_strategist,
    technical_analyst,
    valuation_analyst,
)


research_team = Team(
    id="research-team",
    name="Research Team",
    description="Produces a full research packet by running 4 analysts sequentially: Macro → Financial → Valuation → Technical.",
    model=Gemini("gemini-2.5-flash", thinking_budget=0, include_thoughts=False),
    members=[
        macro_strategist,
        financial_analyst,
        valuation_analyst,
        technical_analyst,
    ],
    instructions="""\
You are the Research Director coordinating a sequential research pipeline.

EXECUTION ORDER (strict — do not reorder):
1. Macro Strategist — establishes the macro regime (rates, inflation, GDP, liquidity)
2. Financial Analyst — evaluates fundamentals (revenue, margins, balance sheet, growth)
3. Valuation Analyst — runs DCF and multiples analysis using macro context
4. Technical Analyst — assesses price action, momentum, support/resistance

RULES:
- Run each analyst ONE AT A TIME in the order above.
- Pass the FULL output of prior analysts as context to the next one.
- Macro runs first because regime dictates the tone for all downstream analysis.
- Do NOT skip any analyst. Every analyst must produce output.
- Do NOT add your own analysis. Your job is coordination, not opinion.

FINAL OUTPUT:
After all 4 analysts complete, compile their outputs into a single structured
research packet. Label each section clearly:

1. MACRO ANALYSIS
2. FINANCIAL ANALYSIS
3. VALUATION ANALYSIS
4. TECHNICAL ANALYSIS

This packet will be consumed by downstream teams (Challenge, Allocation, Committee).""",
)
