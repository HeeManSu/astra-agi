"""
Generate Outline Tool - Writer Agent.
"""

from framework.agents.tool import tool


@tool(
    name="generate_outline",
    description="Generate an article outline for a topic. Returns a structured outline with main sections and subsections.",
)
async def generate_outline(topic: str) -> str:
    """
    Generate an article outline.

    Args:
        topic: Topic for the article

    Returns:
        Structured outline in markdown format
    """
    # This is a simple outline generator
    # In a real implementation, this could use an LLM
    outline = f"""# Article Outline: {topic}

## Introduction
- Hook/opening statement
- Overview of {topic}
- What readers will learn

## Main Content
### Section 1: Key Concepts
- Important points about {topic}
- Definitions and explanations

### Section 2: Practical Applications
- Real-world examples
- Use cases

### Section 3: Best Practices
- Recommendations
- Tips and tricks

## Conclusion
- Summary of key points
- Final thoughts
- Call to action
"""
    return outline
