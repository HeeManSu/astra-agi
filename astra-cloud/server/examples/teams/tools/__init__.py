"""
Research Tools for Teams Example.

Uses the new Pydantic-based tool format with input/output schemas.
"""

from framework.agents.tool import tool
from pydantic import BaseModel, Field


# =============================================================================
# Web Search Tool
# =============================================================================


class WebSearchInput(BaseModel):
    """Input for web search tool."""

    query: str = Field(description="Search query to find information")
    num_results: int = Field(default=5, description="Number of results to return")


class SearchResult(BaseModel):
    """A single search result."""

    title: str = Field(description="Result title")
    snippet: str = Field(description="Text snippet from the result")
    url: str = Field(description="URL of the result")


class WebSearchOutput(BaseModel):
    """Output from web search tool."""

    query: str = Field(description="The original search query")
    results: list[dict] = Field(description="List of search results")


@tool(description="Search the web for information on a topic. Returns relevant search results.")
async def web_search(input: WebSearchInput) -> WebSearchOutput:
    """Search the web for information."""
    return WebSearchOutput(
        query=input.query,
        results=[
            {
                "title": f"Result {i + 1} for: {input.query}",
                "snippet": f"This is a relevant snippet about {input.query}. It contains useful information.",
                "url": f"https://example.com/article-{i + 1}",
            }
            for i in range(min(input.num_results, 5))
        ],
    )


# =============================================================================
# Analyze Data Tool
# =============================================================================


class AnalyzeDataInput(BaseModel):
    """Input for data analysis tool."""

    data: str = Field(description="Data to analyze (text description)")
    analysis_type: str = Field(
        default="summary", description="Type of analysis: summary, trends, or comparison"
    )


class AnalyzeDataOutput(BaseModel):
    """Output from data analysis tool."""

    data_received: str = Field(description="Preview of data received")
    analysis_type: str = Field(description="Type of analysis performed")
    insights: list[str] = Field(description="List of insights discovered")
    confidence: float = Field(description="Confidence score (0-1)")


@tool(description="Analyze data and provide insights. Use for statistical or trend analysis.")
async def analyze_data(input: AnalyzeDataInput) -> AnalyzeDataOutput:
    """Analyze provided data."""
    return AnalyzeDataOutput(
        data_received=input.data[:100] + "..." if len(input.data) > 100 else input.data,
        analysis_type=input.analysis_type,
        insights=[
            f"Key insight 1: Significant pattern detected in {input.analysis_type}",
            "Key insight 2: Data shows positive trend",
            "Key insight 3: Notable correlation found",
        ],
        confidence=0.85,
    )


# =============================================================================
# Summarize Content Tool
# =============================================================================


class SummarizeInput(BaseModel):
    """Input for summarization tool."""

    content: str = Field(description="Content to summarize")
    max_points: int = Field(default=5, description="Maximum number of key points")


class SummarizeOutput(BaseModel):
    """Output from summarization tool."""

    original_length: int = Field(description="Length of original content")
    key_points: list[str] = Field(description="Key points extracted")
    brief_summary: str = Field(description="Brief summary of the content")


@tool(description="Summarize long content into concise key points.")
async def summarize_content(input: SummarizeInput) -> SummarizeOutput:
    """Summarize content into key points."""
    return SummarizeOutput(
        original_length=len(input.content),
        key_points=[
            "Key point 1: Main topic and overview",
            "Key point 2: Important finding or conclusion",
            "Key point 3: Supporting evidence or data",
        ][: input.max_points],
        brief_summary="This content discusses important topics and provides valuable insights.",
    )


# =============================================================================
# Generate Report Tool
# =============================================================================


class GenerateReportInput(BaseModel):
    """Input for report generation tool."""

    title: str = Field(description="Report title")
    findings: str = Field(description="Research findings to include")
    format_type: str = Field(default="markdown", description="Output format: markdown, plain, html")


class GenerateReportOutput(BaseModel):
    """Output from report generation tool."""

    title: str = Field(description="Report title")
    format: str = Field(description="Report format")
    report: str = Field(description="Generated report content")
    word_count: int = Field(description="Word count of the report")


@tool(description="Generate a formatted report from research findings.")
async def generate_report(input: GenerateReportInput) -> GenerateReportOutput:
    """Generate a formatted report."""
    report = f"""# {input.title}

## Executive Summary
{input.findings[:200]}...

## Key Findings
- Finding 1: Important discovery
- Finding 2: Notable pattern
- Finding 3: Recommended action

## Conclusion
Based on the research, we recommend further investigation.
"""
    return GenerateReportOutput(
        title=input.title,
        format=input.format_type,
        report=report,
        word_count=len(report.split()),
    )
