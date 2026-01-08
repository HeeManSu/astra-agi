"""
Check Readability Tool - Shared across Editor and SEO Optimizer agents.

Uses Flesch Reading Ease formula for readability scoring.
For more accurate scores, consider installing textstat package.
"""

import json
import re

from framework.agents.tool import tool


# Optional: Use textstat for more accurate readability scores
try:
    from textstat import (
        flesch_reading_ease,  # type: ignore[import-untyped]  # pyright: ignore[reportMissingModuleSource]
    )

    HAS_TEXTSTAT = True
except ImportError:
    HAS_TEXTSTAT = False


@tool(
    name="check_readability",
    description="Check readability score of text using Flesch-Kincaid readability test.",
)
async def check_readability(text: str) -> str:
    """
    Check readability score.

    Args:
        text: Text to analyze

    Returns:
        JSON string with readability scores and suggestions
    """
    if HAS_TEXTSTAT:
        # Use textstat for accurate readability scores
        try:
            score = flesch_reading_ease(text)
            score = max(0, min(100, score))

            level = (
                "Very Easy"
                if score >= 80
                else "Easy"
                if score >= 70
                else "Fairly Easy"
                if score >= 60
                else "Standard"
                if score >= 50
                else "Fairly Difficult"
                if score >= 30
                else "Difficult"
            )

            return json.dumps(
                {
                    "readability_score": round(score, 2),
                    "level": level,
                    "note": "Calculated using textstat library.",
                },
                indent=2,
            )
        except Exception:
            # Fall back to simplified calculation if textstat fails
            pass

    # Fallback: simplified Flesch Reading Ease calculation
    sentences = text.count(".") + text.count("!") + text.count("?")
    words = len(text.split())
    syllables = sum(max(1, len(re.findall(r"[aeiou]+", word.lower()))) for word in text.split())

    if sentences == 0 or words == 0:
        score = 0
    else:
        # Simplified Flesch Reading Ease formula
        score = (
            206.835 - (1.015 * (words / max(1, sentences))) - (84.6 * (syllables / max(1, words)))
        )

    score = max(0, min(100, score))

    level = (
        "Very Easy"
        if score >= 80
        else "Easy"
        if score >= 70
        else "Fairly Easy"
        if score >= 60
        else "Standard"
        if score >= 50
        else "Fairly Difficult"
        if score >= 30
        else "Difficult"
    )

    note = (
        "Simplified calculation. Install textstat for more accurate scores."
        if not HAS_TEXTSTAT
        else "Simplified calculation (textstat failed)."
    )

    return json.dumps(
        {
            "readability_score": round(score, 2),
            "level": level,
            "note": note,
        },
        indent=2,
    )
