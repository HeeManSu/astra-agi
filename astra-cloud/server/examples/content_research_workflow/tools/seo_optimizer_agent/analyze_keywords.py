"""
Analyze Keywords Tool - SEO Optimizer Agent.
"""

import json
import re

from framework.agents.tool import tool


@tool(
    name="analyze_keywords",
    description="Analyze keywords in text. Extracts keywords, calculates frequency, and ranks them.",
)
async def analyze_keywords(text: str) -> str:
    """
    Analyze keywords in text.

    Args:
        text: Text to analyze

    Returns:
        JSON string with keyword analysis
    """
    # Simple keyword extraction
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())

    # Common stop words to exclude
    stop_words = {
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "all",
        "can",
        "was",
        "one",
        "our",
        "out",
        "day",
        "get",
        "has",
        "him",
        "his",
        "how",
        "its",
        "may",
        "new",
        "now",
        "old",
        "see",
        "two",
        "way",
        "who",
        "boy",
        "did",
        "man",
        "try",
        "use",
        "she",
        "many",
        "some",
        "time",
        "very",
    }

    # Count word frequency
    word_freq = {}
    for word in words:
        if word not in stop_words and len(word) > 3:
            word_freq[word] = word_freq.get(word, 0) + 1

    # Sort by frequency
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

    keywords = [{"word": word, "frequency": freq} for word, freq in sorted_keywords[:20]]

    return json.dumps(
        {"total_words": len(words), "unique_keywords": len(word_freq), "top_keywords": keywords},
        indent=2,
    )
