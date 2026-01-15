"""
Research Agents for Teams Example.

Provides specialized agents for research, analysis, and writing.
"""

from examples.teams.tools import (
    analyze_data,
    generate_report,
    summarize_content,
    web_search,
)
from framework.agents.agent import Agent
from framework.models.google.gemini import Gemini


# Research Agent - focuses on gathering information
researcher_agent = Agent(
    id="researcher",
    name="Researcher",
    description="Gathers and compiles research from various sources",
    model=Gemini("gemini-2.5-flash"),
    instructions="""You are a Research Specialist.

Your role is to:
1. Search for relevant information using the web_search tool
2. Organize findings in a clear structure
3. Identify key facts and data points
4. Provide source citations

Always use the web_search tool to find information before responding.""",
    tools=[web_search],
)

# Analyst Agent - focuses on analyzing data
analyst_agent = Agent(
    id="analyst",
    name="Analyst",
    description="Analyzes data and extracts insights",
    model=Gemini("gemini-2.5-flash"),
    instructions="""You are a Data Analyst.

Your role is to:
1. Analyze provided data using the analyze_data tool
2. Identify patterns and trends
3. Draw meaningful conclusions
4. Quantify findings when possible

Always use the analyze_data tool to process information.""",
    tools=[analyze_data, summarize_content],
)

# Writer Agent - focuses on producing content
writer_agent = Agent(
    id="writer",
    name="Writer",
    description="Creates polished reports and summaries",
    model=Gemini("gemini-2.5-flash"),
    instructions="""You are a Technical Writer.

Your role is to:
1. Create clear, well-structured reports using the generate_report tool
2. Summarize complex information accessibly
3. Ensure proper formatting and organization
4. Tailor content to the target audience

Always use the generate_report tool to create final deliverables.""",
    tools=[summarize_content, generate_report],
)


__all__ = [
    "analyst_agent",
    "researcher_agent",
    "writer_agent",
]
