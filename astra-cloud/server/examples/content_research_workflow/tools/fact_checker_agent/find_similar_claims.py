"""
Find Similar Claims Tool - Fact-Checker Agent.
"""

import json

from examples.content_research_workflow.tools.shared.web_search import web_search
from framework.agents.tool import tool


@tool(
    name="find_similar_claims",
    description="Find similar or related claims to a given claim by searching the web.",
)
async def find_similar_claims(claim: str) -> str:
    """
    Find similar claims.

    Args:
        claim: The claim to find similar ones for

    Returns:
        JSON string with similar claims and sources
    """
    # Search for related information
    search_results = await web_search(claim, num_results=10)

    try:
        results_data = json.loads(search_results)
        results = results_data.get("results", [])

        similar_claims = [
            {
                "title": result.get("title", ""),
                "snippet": result.get("snippet", "")[:200],
                "url": result.get("url", ""),
            }
            for result in results[:5]
        ]

        return json.dumps({"original_claim": claim, "similar_claims": similar_claims}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"{e!s}", "similar_claims": []}, indent=2)
