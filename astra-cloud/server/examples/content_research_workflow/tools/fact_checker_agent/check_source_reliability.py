"""
Check Source Reliability Tool - Fact-Checker Agent.
"""

import json
from urllib.parse import urlparse

from framework.agents.tool import tool


@tool(
    name="check_source_reliability",
    description="Check the reliability of a source URL. Analyzes domain reputation and source type.",
)
async def check_source_reliability(url: str) -> str:
    """
    Check source reliability.

    Args:
        url: URL to check

    Returns:
        JSON string with reliability assessment
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Simple reliability check based on domain
        reliable_domains = [
            "edu",
            "gov",
            "org",
            "wikipedia.org",
            "bbc.com",
            "reuters.com",
            "ap.org",
            "nytimes.com",
            "theguardian.com",
        ]

        is_reliable = any(rd in domain for rd in reliable_domains)

        # Check if it's a news site
        news_domains = ["news", "bbc", "reuters", "ap", "cnn", "npr"]
        is_news = any(nd in domain for nd in news_domains)

        return json.dumps(
            {
                "url": url,
                "domain": domain,
                "reliability_score": "high" if is_reliable else "medium",
                "is_news_source": is_news,
                "note": "This is a basic check. Always verify sources manually.",
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps({"url": url, "error": f"{e!s}"}, indent=2)
