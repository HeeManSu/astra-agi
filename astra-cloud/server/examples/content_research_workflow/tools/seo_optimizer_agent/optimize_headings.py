"""
Optimize Headings Tool - SEO Optimizer Agent.
"""

import json
import re

from framework.agents.tool import tool


@tool(
    name="optimize_headings",
    description="Analyze and suggest improvements for heading structure in content.",
)
async def optimize_headings(content: str) -> str:
    """
    Optimize headings structure.

    Args:
        content: Content with headings to analyze

    Returns:
        JSON string with heading analysis and suggestions
    """
    # Extract headings (markdown format)
    heading_pattern = r"^(#{1,6})\s+(.+)$"
    headings = re.findall(heading_pattern, content, re.MULTILINE)

    heading_structure = []
    for level, text in headings:
        heading_structure.append(
            {"level": len(level), "text": text.strip(), "length": len(text.strip())}
        )

    # Analyze structure
    issues = []
    if not heading_structure:
        issues.append("No headings found. Consider adding headings for better structure.")

    # Check for proper hierarchy
    prev_level = 0
    for heading in heading_structure:
        level = heading["level"]
        if level > prev_level + 1:
            issues.append(
                f"Heading '{heading['text']}' jumps from level {prev_level} to {level}. Maintain proper hierarchy."
            )
        prev_level = level

    # Check heading length
    for heading in heading_structure:
        if heading["length"] > 60:
            issues.extend(
                [
                    f"Heading '{heading['text'][:30]}...' is too long ({heading['length']} chars). Keep under 60 characters."
                ]
            )

    suggestions = []
    if not issues:
        suggestions.append("Heading structure looks good!")
    else:
        suggestions.extend(issues)

    return json.dumps(
        {
            "headings": heading_structure,
            "total_headings": len(heading_structure),
            "suggestions": suggestions,
        },
        indent=2,
    )
