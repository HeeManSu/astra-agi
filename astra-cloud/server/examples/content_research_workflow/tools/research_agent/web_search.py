import json

from duckduckgo_search import DDGS
from framework.agents import tool


@tool(
    name="Web Search",
    description="Search the web for information using DuckDuckGo. Returns a list of search results with titles, snippets, and URLs.",
)
async def web_search(query: str, num_results: int = 5) -> str:
    """
    Search the web for information.

    Args:
        query: Search query string
        num_results: Number of results to return (default: 5, max: 20)
    """

    try:
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
