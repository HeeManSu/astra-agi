"""
Extract Key Points Tool - Research Agent.
"""

from examples.content_research_workflow.tools.research_agent.scrape_url import scrape_url
from framework.agents.tool import tool


@tool(
    name="extract_key_points",
    description="Extract key points and main information from a URL. Summarizes the main content.",
)
async def extract_key_points(url: str) -> str:
    """
    Extract key points from a URL.

    Args:
        url: URL to extract key points from

    Returns:
        Summary of key points from the page
    """
    # First scrape the content
    content = await scrape_url(url)

    if content.startswith("Error"):
        return content

    # Simple extraction: take first few paragraphs and headings
    lines = content.split("\n")
    key_points = []

    # Extract headings (lines that are short and likely headings)
    for line in lines[:50]:  # Check first 50 lines
        if len(line) < 100 and len(line) > 10:
            if line[0].isupper() or line.startswith("#"):
                key_points.append(f"• {line}")

    # Add first few substantial paragraphs
    paragraphs = [line for line in lines if len(line) > 100]
    key_points.extend(f"• {para[:200]}..." for para in paragraphs[:3])

    if not key_points:
        # Fallback: return first 500 chars
        return content[:500] + "..."

    return "\n".join(key_points[:10])  # Limit to 10 key points
