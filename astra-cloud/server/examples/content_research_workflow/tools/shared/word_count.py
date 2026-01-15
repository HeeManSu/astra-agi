"""
Word Count Tool - Shared across Writer and Editor agents.
"""

import json

from framework.agents.tool import tool


@tool(
    name="word_count",
    description="Count words and characters in text. Returns word count, character count, and reading time estimate.",
)
async def word_count(text: str) -> str:
    """
    Count words and characters in text.

    Args:
        text: Text to analyze

    Returns:
        JSON string with word count, character count, and reading time
    """
    words = text.split()
    word_count = len(words)
    char_count = len(text)
    char_count_no_spaces = len(text.replace(" ", ""))

    # Estimate reading time (average 200 words per minute)
    reading_time_minutes = max(1, round(word_count / 200))

    return json.dumps(
        {
            "word_count": word_count,
            "character_count": char_count,
            "character_count_no_spaces": char_count_no_spaces,
            "reading_time_minutes": reading_time_minutes,
        },
        indent=2,
    )
