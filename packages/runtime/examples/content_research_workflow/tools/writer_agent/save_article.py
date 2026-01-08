"""
Save Article Tool - Writer Agent.
"""

from pathlib import Path
import re

from framework.agents.tool import tool


@tool(
    name="save_article",
    description="Save an article to a file. Supports markdown and text formats.",
)
async def save_article(title: str, content: str, format: str = "markdown") -> str:
    """
    Save an article to a file.

    Args:
        title: Article title (used for filename)
        content: Article content
        format: File format - "markdown" or "text" (default: "markdown")

    Returns:
        Path to saved file
    """
    try:
        # Create articles directory if it doesn't exist
        articles_dir = Path(__file__).parent.parent.parent / "data" / "articles"
        articles_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize title for filename
        safe_title = re.sub(r"[^\w\s-]", "", title)[:50]
        safe_title = re.sub(r"[-\s]+", "-", safe_title)

        # Determine file extension
        ext = ".md" if format.lower() == "markdown" else ".txt"

        # Create filename
        filename = f"{safe_title}{ext}"
        filepath = articles_dir / filename

        # Handle duplicates
        counter = 1
        while filepath.exists():
            filename = f"{safe_title}_{counter}{ext}"
            filepath = articles_dir / filename
            counter += 1

        # Write content
        filepath.write_text(content, encoding="utf-8")

        return f"Article saved to: {filepath}"

    except Exception as e:
        return f"Error saving article: {e!s}"
