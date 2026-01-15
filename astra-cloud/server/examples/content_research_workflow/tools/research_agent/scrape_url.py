"""
Scrape URL Tool - Research Agent.
"""

from bs4 import BeautifulSoup  # pyright: ignore[reportMissingModuleSource]
from framework.agents.tool import tool
import httpx


@tool(
    name="scrape_url",
    description="Scrape content from a URL. Extracts main text content from web pages.",
)
async def scrape_url(url: str) -> str:
    """
    Scrape content from a URL.

    Args:
        url: URL to scrape

    Returns:
        Extracted text content from the page
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Extract text
            text = soup.get_text(separator="\n", strip=True)

            # Clean up excessive whitespace
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            cleaned_text = "\n".join(lines)

            return cleaned_text[:10000]  # Limit to 10k characters

    except httpx.TimeoutException:
        return f"Error: Timeout while fetching {url}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} for {url}"
    except Exception as e:
        return f"Error scraping {url}: {e!s}"
