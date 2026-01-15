"""
Verify Fact Tool - Fact-Checker Agent.
"""

import json

from examples.content_research_workflow.tools.shared.web_search import web_search
from framework.agents.tool import tool


@tool(
    name="verify_fact",
    description="Verify a factual claim by searching the web for supporting evidence.",
)
async def verify_fact(claim: str) -> str:
    """
    Verify a factual claim.

    Args:
        claim: The claim to verify

    Returns:
        JSON string with verification status, sources, and evidence
    """
    # Search for the claim
    search_results = await web_search(f"{claim} verification fact check", num_results=5)

    try:
        results_data = json.loads(search_results)
        results = results_data.get("results", [])

        if not results:
            return json.dumps(
                {
                    "claim": claim,
                    "status": "unverified",
                    "reason": "No sources found",
                    "sources": [],
                },
                indent=2,
            )

        # Extract sources
        sources = [{"title": r.get("title", ""), "url": r.get("url", "")} for r in results]

        return json.dumps(
            {
                "claim": claim,
                "status": "needs_review",  # Always needs human review
                "sources": sources,
                "note": "Please review sources to verify claim accuracy",
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps({"claim": claim, "status": "error", "error": f"{e!s}"}, indent=2)
