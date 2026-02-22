"""
Task Team
---------

Chair autonomously decomposes complex tasks with dependencies.
Best for: multi-step portfolio construction and analysis.

Agno equivalent: TeamMode.tasks
"""

from framework.models import Gemini
from framework.team import Team

from ..agents import (
    financial_analyst,
    knowledge_agent,
    market_analyst,
    memo_writer,
    risk_officer,
    technical_analyst,
)


task_team = Team(
    id="task-team",
    name="Investment Team - Tasks",
    description="Decomposes complex investment tasks with dependencies. Best for multi-step portfolio analysis.",
    model=Gemini("gemini-2.5-flash"),
    members=[
        market_analyst,
        financial_analyst,
        technical_analyst,
        risk_officer,
        knowledge_agent,
        memo_writer,
    ],
    instructions=(
        "Decompose complex investment tasks into sub-tasks with dependencies.\n"
        "Assign each sub-task to the most appropriate analyst.\n"
        "Parallelize independent tasks (e.g., fundamentals + technicals can run simultaneously).\n"
        "Ensure risk assessment happens after fundamental + technical analysis.\n"
        "Memo writing should be the final step after all analysis is complete."
    ),
)
