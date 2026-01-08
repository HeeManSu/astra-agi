"""
Web Search Tool - Shared across Research and Fact-Checker agents.
"""

import json

from framework.agents.tool import tool


# Optional import
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


@tool(
    name="web_search",
    description="Search the web for information using DuckDuckGo. Returns a list of search results with titles, snippets, and URLs.",
)
async def web_search(query: str, num_results: int = 5) -> str:
    """
    Search the web for information.

    Args:
        query: Search query string
        num_results: Number of results to return (default: 5, max: 20)

    Returns:
        JSON string with search results containing title, snippet, and url for each result
    """
    if DDGS is None:
        return json.dumps(
            {
                "error": "duckduckgo-search not installed. Install with: pip install duckduckgo-search",
                "results": [],
            }
        )

    try:
        # Limit results to reasonable number
        num_results = min(max(1, num_results), 20)

        ddgs = DDGS()
        results = [
            {
                "title": result.get("title", ""),
                "snippet": result.get("body", ""),
                "url": result.get("href", ""),
            }
            for result in ddgs.text(query, max_results=num_results)
        ]

        return json.dumps({"results": results}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Search failed: {e!s}", "results": []})
