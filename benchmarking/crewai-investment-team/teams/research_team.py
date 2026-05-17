"""
Research Team — CrewAI version (hierarchical / manager-LLM orchestration).

A manager agent (auto-created from `manager_llm`) reads each task description,
picks the most suitable member from the agent pool, and delegates. The manager
itself runs a ReAct loop using CrewAI's built-in delegation tools — this is
CrewAI's analog of Agno's `TeamMode.coordinate` and is the apples-to-apples
ReAct comparison for the benchmark (model-in-the-orchestration-loop on both
sides).

Members are not bound to specific tasks. Tasks describe the work; the manager
decides who runs what.
"""

from crewai import Crew, Process, Task

from agents import (
    financial_analyst,
    macro_strategist,
    technical_analyst,
    valuation_analyst,
)
from agents.settings import make_llm


# One task per analyst. {query} is substituted at crew.kickoff(inputs={"query":...}) time.
# Tasks intentionally do NOT pin an `agent=` — the manager picks based on
# description + the agent's role/backstory in the pool.

macro_task = Task(
    description=(
        "Assess the macro regime and equity risk environment relevant to: {query}\n\n"
        "Use the macro data tools to gather current readings on monetary policy, "
        "inflation, growth, liquidity, and the yield curve. Produce the structured "
        "output specified in the assigned analyst's backstory. Focus on the macro "
        "signal, do not discuss individual company details."
    ),
    expected_output=(
        "A structured macro assessment with sections: Macro Summary, Monetary Policy, "
        "Inflation & Growth, Liquidity & Credit, Yield Curve, Equity Risk Regime, "
        "and a Confidence Score (1-10)."
    ),
)

financial_task = Task(
    description=(
        "Analyze the company fundamentals for the target in: {query}\n\n"
        "Using the financial tools, evaluate revenue, margins, profitability, "
        "cash flow, balance sheet, and growth. Produce the structured output "
        "specified in the assigned analyst's backstory. Focus on company "
        "fundamentals only."
    ),
    expected_output=(
        "A structured fundamentals report with sections: Revenue & Growth, "
        "Profitability, Cash Flow, Balance Sheet, Earnings Stability, Financial Risk, "
        "and a Conviction Score (1-10)."
    ),
)

valuation_task = Task(
    description=(
        "Determine intrinsic value and margin of safety for the target in: {query}\n\n"
        "Use the valuation tools to run DCF and comparable multiples. Produce the "
        "structured output specified in the assigned analyst's backstory."
    ),
    expected_output=(
        "A structured valuation packet with sections: DCF Valuation, Comparable "
        "Multiples, Fair Value (Bear/Base/Bull), Margin of Safety, Valuation Risks, "
        "and a Final Valuation Verdict."
    ),
)

technical_task = Task(
    description=(
        "Assess price action, momentum, and technical structure for the target in: {query}\n\n"
        "Use the technical tools to compute indicators (RSI, MACD, moving averages) "
        "and identify trend, support, and resistance. Produce the structured output "
        "specified in the assigned analyst's backstory. Do not discuss fundamentals, "
        "valuation, or macro."
    ),
    expected_output=(
        "A structured technical report with sections: Trend Structure, Momentum "
        "Indicators, Support & Resistance, Volume Analysis, Entry Timing Quality, "
        "Technical Risk Level, and a Technical Conviction Score (1-10)."
    ),
)


research_team = Crew(
    agents=[macro_strategist, financial_analyst, valuation_analyst, technical_analyst],
    tasks=[macro_task, financial_task, valuation_task, technical_task],
    process=Process.hierarchical,
    manager_llm=make_llm(),
    memory=False,
    cache=False,
    planning=False,
    verbose=False,
    full_output=False,
)
