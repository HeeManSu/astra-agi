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
from pydantic import BaseModel, Field

from market_research.config import API_KEY


# =============================================================================
# COMMON MODELS
# =============================================================================


class AmazonResult(BaseModel):
    """Generic container for Amazon API results."""

    data: dict[str, Any]
    status: str = "success"


async def _make_request(url: str, timeout_ms: int = 20000) -> dict[str, Any]:
    """Make HTTP GET request with timeout."""
    loop = asyncio.get_event_loop()
    timeout_seconds = timeout_ms / 1000

    try:
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, lambda: urllib.request.urlopen(url, timeout=timeout_seconds)
            ),
            timeout=timeout_seconds + 5.0,
        )
        if response.status != 200:
            text = response.read().decode("utf-8", errors="replace")
            raise Exception(f"API error {response.status}: {text}") from None
        return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        # Simplified error handling for brevity
        raise Exception(f"API Request failed: {e}") from e


# =============================================================================
# TOOLS
# =============================================================================

# --- Tool: Get Product ---


class GetProductInput(BaseModel):
    domain: str = Field(description="Amazon TLD (e.g., 'com', 'co.uk')")
    asin: str = Field(description="Amazon product ASIN")
    country: str | None = Field(default=None, description="ISO-3166 country code")
    postal_code: str | None = Field(default=None, description="Postal code")
    language: str | None = Field(default=None, description="ISO 639-1 language code")
    timeout_ms: int = Field(default=20000, description="Request timeout in ms")


@ tool(description="Retrieve product details by ASIN")
async def get_product(input: GetProductInput) -> AmazonResult:
    domain = input.domain
    if "amazon." in domain:
        domain = domain.replace("amazon.", "")

    params = {"api_key": API_KEY, "domain": domain, "asin": input.asin}
    if input.country:
        params["country"] = input.country.lower()
    if input.postal_code:
        params["postal_code"] = input.postal_code
    if input.language:
        params["language"] = input.language

    url = f"https://api.scrapingdog.com/amazon/product?{urllib.parse.urlencode(params)}"
    data = await _make_request(url, input.timeout_ms)
    return AmazonResult(data=data)


# --- Tool: Search ---


class SearchInput(BaseModel):
    domain: str = Field(description="Amazon TLD")
    query: str = Field(description="Search query")
    page: int = Field(default=1, description="Page number")
    country: str | None = Field(default=None, description="Country code")
    timeout_ms: int = Field(default=20000, description="Timeout in ms")


@ tool(description="Search Amazon products")
async def search(input: SearchInput) -> AmazonResult:
    params = {
        "api_key": API_KEY,
        "domain": input.domain,
        "query": input.query,
        "page": str(input.page),
    }
    if input.country:
        params["country"] = input.country

    url = f"https://api.scrapingdog.com/amazon/search?{urllib.parse.urlencode(params)}"
    data = await _make_request(url, input.timeout_ms)
    return AmazonResult(data=data)


# --- Tool: Get Reviews ---


class GetReviewsInput(BaseModel):
    domain: str = Field(description="Amazon TLD")
    asin: str = Field(description="Product ASIN")
    page: int = Field(default=1, description="Page number")
    sort_by: str = Field(default="helpful", description="Sort criteria")
    timeout_ms: int = Field(default=20000, description="Timeout in ms")


@ tool(description="Get product reviews")
async def get_reviews(input: GetReviewsInput) -> AmazonResult:
    params = {
        "api_key": API_KEY,
        "domain": input.domain,
        "asin": input.asin,
        "page": str(input.page),
        "sort_by": input.sort_by,
    }
    url = f"https://api.scrapingdog.com/amazon/reviews?{urllib.parse.urlencode(params)}"
    data = await _make_request(url, input.timeout_ms)
    return AmazonResult(data=data)


# --- Tool: Get Offers ---


class GetOffersInput(BaseModel):
    domain: str = Field(description="Amazon TLD")
    asin: str = Field(description="Product ASIN")
    country: str | None = Field(default=None, description="Country code")
    timeout_ms: int = Field(default=20000, description="Timeout in ms")


@ tool(description="Get product offers")
async def get_offers(input: GetOffersInput) -> AmazonResult:
    params = {"api_key": API_KEY, "domain": input.domain, "asin": input.asin}
    if input.country:
        params["country"] = input.country

    url = f"https://api.scrapingdog.com/amazon/offers?{urllib.parse.urlencode(params)}"
    data = await _make_request(url, input.timeout_ms)
    return AmazonResult(data=data)


# --- Tool: Autocomplete ---


class AutocompleteInput(BaseModel):
    prefix: str = Field(description="Search prefix")
    timeout_ms: int = Field(default=20000, description="Timeout in ms")


@ tool(description="Get search autocomplete suggestions")
async def autocomplete(input: AutocompleteInput) -> AmazonResult:
    params = {"api_key": API_KEY, "prefix": input.prefix}
    url = f"https://api.scrapingdog.com/amazon/autocomplete?{urllib.parse.urlencode(params)}"
    data = await _make_request(url, input.timeout_ms)
    return AmazonResult(data=data)
