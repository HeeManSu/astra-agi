"""
Get Recent News Tool - Research Agent.
"""

import json
import os

from framework.agents.tool import tool


# Optional imports
try:
    from newsapi import NewsApiClient
except ImportError:
    NewsApiClient = None

from examples.content_research_workflow.tools.shared.web_search import web_search


@tool(
    name="get_recent_news",
    description="Get recent news articles about a topic. Uses NewsAPI if available, otherwise falls back to web search.",
)
async def get_recent_news(topic: str, days: int = 7) -> str:
    """
    Get recent news about a topic.

    Args:
        topic: Topic to search for
        days: Number of days to look back (default: 7)

    Returns:
        JSON string with news articles
    """
    # Try NewsAPI first if available
    if NewsApiClient is not None:
        api_key = os.getenv("NEWS_API_KEY")
        if api_key:
            try:
                newsapi = NewsApiClient(api_key=api_key)
                articles = newsapi.get_everything(
                    q=topic, language="en", sort_by="relevancy", page_size=10
                )
                if articles.get("status") == "ok":
                    results = [
                        {
                            "title": article.get("title", ""),
                            "snippet": article.get("description", ""),
                            "url": article.get("url", ""),
                        }
                        for article in articles.get("articles", [])
                    ]

                return json.dumps({"articles": results}, indent=2)
            except Exception:
                # Fall back to web search
                pass

    # Fallback to web search
    return await web_search(f"{topic} news", num_results=5)
