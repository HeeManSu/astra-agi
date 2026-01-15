"""
Research Team Example - Code Mode

A simple example demonstrating Team code mode with:
- Multiple specialized agents
- Pydantic-based tools for accurate LLM code generation
- Nested team support

The team researches topics using web search and creates reports.
"""

import asyncio
import os
import sys

from pydantic import BaseModel, Field


# Add framework src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from framework.agents.agent import Agent
from framework.agents.tool import tool
from framework.models.google.gemini import Gemini
from framework.team import Team


# TOOL SCHEMAS (Pydantic models for accurate LLM code generation)
class WebSearchInput(BaseModel):
    """Input for web search tool."""

    query: str = Field(description="Search query")
    max_results: int = Field(default=5, description="Maximum results to return")


class WebSearchResult(BaseModel):
    """A single search result."""

    title: str
    url: str
    snippet: str


class WebSearchOutput(BaseModel):
    """Output from web search tool."""

    results: list[WebSearchResult]
    total_found: int


class CalculatorInput(BaseModel):
    """Input for calculator tool."""

    expression: str = Field(description="Math expression to evaluate (e.g., '2 + 2')")


class CalculatorOutput(BaseModel):
    """Output from calculator tool."""

    result: float
    expression: str


class ReportInput(BaseModel):
    """Input for report generation tool."""

    title: str = Field(description="Report title")
    sections: list[str] = Field(description="List of section contents")


class ReportOutput(BaseModel):
    """Output from report generation tool."""

    report: str
    word_count: int


# TOOLS (Using Pydantic for input/output validation)
@tool(description="Search the web for information")
def web_search(input: WebSearchInput) -> WebSearchOutput:
    """Search the web and return results."""
    # Mock implementation - in production, use actual search API
    mock_results = [
        WebSearchResult(
            title=f"Result {i + 1} for '{input.query}'",
            url=f"https://example.com/article-{i + 1}",
            snippet=f"This is a relevant snippet about {input.query}...",
        )
        for i in range(min(input.max_results, 3))
    ]
    return WebSearchOutput(results=mock_results, total_found=len(mock_results))


@tool(description="Perform mathematical calculations")
def calculate(input: CalculatorInput) -> CalculatorOutput:
    """Evaluate a mathematical expression."""
    try:
        # Safe eval for simple math
        allowed = set("0123456789+-*/.(). ")
        if all(c in allowed for c in input.expression):
            result = eval(input.expression)
        else:
            result = 0.0
    except Exception:
        result = 0.0
    return CalculatorOutput(result=float(result), expression=input.expression)


@tool(description="Generate a formatted report from sections")
def generate_report(input: ReportInput) -> ReportOutput:
    """Generate a report from title and sections."""
    report_lines = [f"# {input.title}", ""]
    for i, section in enumerate(input.sections, 1):
        report_lines.append(f"## Section {i}")
        report_lines.append(section)
        report_lines.append("")

    report = "\n".join(report_lines)
    word_count = len(report.split())
    return ReportOutput(report=report, word_count=word_count)


# AGENTS
model = Gemini("gemini-2.5-flash")

# Research Agent - searches for information
research_agent = Agent(
    name="Researcher",
    model=model,
    instructions="You search the web to find relevant information on topics.",
    tools=[web_search],
)

# Math Agent - performs calculations
math_agent = Agent(
    name="Calculator",
    model=model,
    instructions="You perform mathematical calculations when needed.",
    tools=[calculate],
)

# Writer Agent - creates reports
writer_agent = Agent(
    name="Writer",
    model=model,
    instructions="You write clear and well-structured reports.",
    tools=[generate_report],
)


# TEAM
research_team = Team(
    id="research-team",
    name="Research Team",
    description="A team that researches topics and creates comprehensive reports",
    model=model,
    members=[research_agent, math_agent, writer_agent],
    instructions="""
    You are a research team coordinator. When given a research task:

    1. Use the Researcher to search for relevant information
    2. Use the Calculator if any math is needed
    3. Use the Writer to compile findings into a report

    Always synthesize the final findings using synthesize_response().
    """,
    timeout=120.0,
)


# MAIN
async def main():
    print("=" * 60)
    print("Research Team Example")
    print("=" * 60)

    # Test query
    query = "Research the current state of AI and summarize in 3 key points"
    print(f"\nQuery: {query}\n")

    try:
        # Invoke the team
        result = await research_team.invoke(query)
        print("\n" + "=" * 60)
        print("Result:")
        print("=" * 60)
        print(result)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
