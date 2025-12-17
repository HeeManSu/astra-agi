"""Amazon Market Research Tools.

This module provides tools for scraping Amazon marketplace data including:
- Product details by ASIN
- Search results
- Customer reviews
- Product offers (pricing from multiple sellers)
- Search autocomplete suggestions
"""

import asyncio
import json
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from framework.agents.tool import tool

from market_research.config import API_KEY


async def _make_request(url: str, timeout_ms: int = 20000) -> dict[str, Any]:
    """Make HTTP GET request with timeout."""

    loop = asyncio.get_event_loop()
    timeout_seconds = timeout_ms / 1000

    try:
        # Run blocking HTTP request in executor
        # urllib timeout handles HTTP connection timeout
        # asyncio.wait_for provides overall timeout safety net
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, lambda: urllib.request.urlopen(url, timeout=timeout_seconds)
            ),
            timeout=timeout_seconds + 5.0,  # Large buffer to let urllib timeout fire first
        )
        if response.status != 200:
            text = response.read().decode("utf-8", errors="replace")
            raise Exception(f"API error {response.status}: {text}") from None
        return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        # urllib timeout - this fires when HTTP request times out
        if isinstance(e.reason, TimeoutError) or "timed out" in str(e).lower():
            raise Exception(f"API timeout after {timeout_ms}ms") from None
        raise Exception(f"API connection error: {e!s}") from e
    except asyncio.TimeoutError:
        # This should rarely fire since urllib timeout fires first
        raise Exception(f"API timeout after {timeout_ms}ms") from None
    except Exception as e:
        # Preserve original error message if it's already formatted
        if "API error" in str(e) or "API timeout" in str(e):
            raise
        raise Exception(f"API error: {e!s}") from e


@tool(module="amazon")
async def get_product(
    domain: str,
    asin: str,
    country: str | None = None,
    postal_code: str | None = None,
    language: str | None = None,
    timeout_ms: int = 20000,
) -> dict[str, Any]:
    """Retrieve comprehensive product details from Amazon.

    Returns title, price, ratings, availability, images, description, features,
    specifications, and seller information for a specific product by ASIN.

    Args:
        domain: Amazon TLD (e.g., 'com', 'in', 'de', 'fr', 'co.uk')
        asin: Amazon product ASIN (required)
        country: ISO-3166 country code (default: 'us')
        postal_code: Postal code for location-specific results
        language: ISO 639-1 language code (e.g., 'en', 'de', 'fr')
        timeout_ms: Request timeout in milliseconds (default: 20000)

    Returns:
        Product details including title, price, ratings, images, etc.
    """

    if "amazon." in domain:
        domain = domain.replace("amazon.", "")

    params = {
        "api_key": API_KEY,
        "domain": domain,
        "asin": asin,
    }
    if country:
        params["country"] = country.lower()
    if postal_code:
        params["postal_code"] = postal_code
    if language:
        params["language"] = language

    url = f"https://api.scrapingdog.com/amazon/product?{urllib.parse.urlencode(params)}"
    return await _make_request(url, timeout_ms)


@tool(module="amazon")
async def search(
    domain: str,
    query: str,
    page: int,
    country: str | None = None,
    postal_code: str | None = None,
    language: str | None = None,
    premium: bool | str | None = None,
    timeout_ms: int = 20000,
) -> dict[str, Any]:
    """Search Amazon and return paginated product listings.

    Returns products matching the search query with key metrics like title,
    price, rating, ASIN, and thumbnail images.

    Args:
        domain: Amazon TLD (e.g., 'com', 'in', 'de', 'fr', 'co.uk')
        query: Search query string (required)
        page: Page number (required, positive integer)
        country: ISO-3166 country code (default: 'us')
        postal_code: Postal code for location-specific results
        language: ISO 639-1 language code
        premium: Use premium proxies (increases credit cost)
        timeout_ms: Request timeout in milliseconds (default: 20000)

    Returns:
        Paginated search results with product listings
    """
    params = {
        "api_key": API_KEY,
        "domain": domain,
        "query": query,
        "page": str(page),
    }
    if country:
        params["country"] = country
    if postal_code:
        params["postal_code"] = postal_code
    if language:
        params["language"] = language
    if premium is not None:
        params["premium"] = str(premium)

    url = f"https://api.scrapingdog.com/amazon/search?{urllib.parse.urlencode(params)}"
    return await _make_request(url, timeout_ms)


@tool(module="amazon")
async def get_reviews(
    domain: str,
    asin: str,
    page: int,
    sort_by: str = "helpful",
    filter_by_star: str = "all_stars",
    format_type: str = "all_formats",
    reviewer_type: str = "all_reviews",
    media_type: str = "all_contents",
    url: str | None = None,
    timeout_ms: int = 20000,
) -> dict[str, Any]:
    """Extract customer reviews for a product.

    Returns reviews with ratings, text, helpfulness votes, reviewer info,
    and media. Supports filtering by star rating and sorting options.

    Args:
        domain: Amazon TLD (e.g., 'com', 'in', 'de', 'fr', 'co.uk')
        asin: Product ASIN (required)
        page: Page number (required)
        sort_by: Sort criteria - 'helpful' or 'recent' (default: 'helpful')
        filter_by_star: Star filter - 'one_star', 'two_star', 'three_star',
            'four_star', 'five_star', 'positive', 'critical', 'all_stars'
            (default: 'all_stars')
        format_type: 'all_formats' or 'current_format' (default: 'all_formats')
        reviewer_type: 'all_reviews' or 'avp_only_reviews' (default: 'all_reviews')
        media_type: 'media_reviews_only' or 'all_contents' (default: 'all_contents')
        url: Alternative direct Amazon reviews URL (optional)
        timeout_ms: Request timeout in milliseconds (default: 20000)

    Returns:
        Reviews data with ratings, text, and metadata
    """
    params = {"api_key": API_KEY}
    if url:
        params["url"] = url
    else:
        params.update(
            {
                "domain": domain,
                "asin": asin,
                "page": str(page),
                "sort_by": sort_by,
                "filter_by_star": filter_by_star,
                "format_type": format_type,
                "reviewer_type": reviewer_type,
                "media_type": media_type,
            }
        )

    url_str = f"https://api.scrapingdog.com/amazon/reviews?{urllib.parse.urlencode(params)}"
    return await _make_request(url_str, timeout_ms)


@tool(module="amazon")
async def get_offers(
    domain: str,
    asin: str,
    country: str | None = None,
    postal_code: str | None = None,
    timeout_ms: int = 20000,
) -> dict[str, Any]:
    """Retrieve all available offers for a product.

    Returns prices from different sellers, shipping costs, seller ratings,
    fulfillment methods (FBA/FBM), stock availability, and condition.

    Args:
        domain: Amazon TLD (e.g., 'com', 'in', 'de', 'fr', 'co.uk')
        asin: Product ASIN (required)
        country: ISO-3166 country code (e.g., 'us')
        postal_code: Postal code for location-specific results
        timeout_ms: Request timeout in milliseconds (default: 20000)

    Returns:
        Offers data with prices, sellers, and fulfillment details
    """
    params = {
        "api_key": API_KEY,
        "domain": domain,
        "asin": asin,
    }
    if country:
        params["country"] = country
    if postal_code:
        params["postal_code"] = postal_code

    url = f"https://api.scrapingdog.com/amazon/offers?{urllib.parse.urlencode(params)}"
    return await _make_request(url, timeout_ms)


@tool(module="amazon")
async def autocomplete(
    prefix: str,
    last_prefix: str | None = None,
    mid: str | None = None,
    suffix: str | None = None,
    language: str = "en",
    timeout_ms: int = 20000,
) -> dict[str, Any]:
    """Generate Amazon search keyword suggestions.

    Returns real-time search suggestions based on partial keywords, revealing
    popular search queries and buyer intent.

    Args:
        prefix: Partial search term to generate suggestions (required)
        last_prefix: Previous prefix (optional)
        mid: Merchant ID (optional)
        suffix: Suffix for search (optional)
        language: ISO 639-1 language code (default: 'en')
        timeout_ms: Request timeout in milliseconds (default: 20000)

    Returns:
        Autocomplete suggestions with search terms
    """
    params = {
        "api_key": API_KEY,
        "prefix": prefix,
    }
    if last_prefix:
        params["last_prefix"] = last_prefix
    if mid:
        params["mid"] = mid
    if suffix:
        params["suffix"] = suffix
    if language:
        params["language"] = language

    url = f"https://api.scrapingdog.com/amazon/autocomplete?{urllib.parse.urlencode(params)}"
    return await _make_request(url, timeout_ms)
