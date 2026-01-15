"""
Research Teams for Teams Example.

Demonstrates team coordination with code_mode.
"""

# from framework.models.gemini import Gemini
from examples.teams.agents import analyst_agent, researcher_agent, writer_agent
from framework.models.google.gemini import Gemini
from framework.team import Team


# Research Team - coordinates researcher, analyst, and writer
research_team = Team(
    id="research-team",
    name="Research Team",
    description="Comprehensive research team that researches, analyzes, and produces reports",
    model=Gemini("gemini-2.5-flash"),
    members=[researcher_agent, analyst_agent, writer_agent],
    instructions="""You coordinate a research team with three specialists:

1. **Researcher** (researcher): Searches the web and gathers information
2. **Analyst** (analyst): Analyzes data and extracts insights
3. **Writer** (writer): Creates polished reports

Workflow:
1. First, have the Researcher gather relevant information
2. Then, have the Analyst analyze the findings
3. Finally, have the Writer produce a comprehensive report

Coordinate effectively by:
- Delegating specific tasks to each team member
- Combining their outputs into a coherent response
- Ensuring quality at each step""",
    timeout=120.0,
)


__all__ = [
    "research_team",
]
