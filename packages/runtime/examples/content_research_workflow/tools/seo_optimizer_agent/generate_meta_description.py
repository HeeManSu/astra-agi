"""
Generate Meta Description Tool - SEO Optimizer Agent.
"""

import re

from framework.agents.tool import tool


@tool(
    name="generate_meta_description",
    description="Generate a meta description for content. Creates SEO-friendly meta descriptions (150-160 characters).",
)
async def generate_meta_description(content: str) -> str:
    """
    Generate meta description.

    Args:
        content: Content to generate meta description for

    Returns:
        Meta description (150-160 characters)
    """
    # Simple extraction: take first sentence or first 155 characters
    sentences = re.split(r"[.!?]", content)
    first_sentence = sentences[0].strip() if sentences else ""

    if len(first_sentence) <= 160:
        meta = first_sentence
    else:
        # Truncate to 155 chars and add ellipsis
        meta = content[:155].rsplit(" ", 1)[0] + "..."

    # Ensure it's between 120-160 chars
    if len(meta) < 120:
        meta = content[:157].rsplit(" ", 1)[0] + "..."

    return meta[:160]  # Hard limit at 160
