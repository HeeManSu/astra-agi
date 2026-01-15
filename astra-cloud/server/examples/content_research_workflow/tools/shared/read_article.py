"""
Read Article Tool - Shared across Writer, Editor, and SEO Optimizer agents.
"""

from pathlib import Path

from framework.agents.tool import tool


@tool(
    name="read_article",
    description="Read an article from a file path.",
)
async def read_article(file_path: str) -> str:
    """
    Read an article from a file.

    Args:
        file_path: Path to the article file (relative to data/articles/ or absolute)

    Returns:
        Article content
    """
    try:
        path = Path(file_path)

        # If relative path, check in articles directory
        if not path.is_absolute():
            articles_dir = Path(__file__).parent.parent.parent / "data" / "articles"
            path = articles_dir / path

        if not path.exists():
            return f"Error: File not found: {file_path}"

        content = path.read_text(encoding="utf-8")
        return content

    except Exception as e:
        return f"Error reading article: {e!s}"
