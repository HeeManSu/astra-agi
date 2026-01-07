"""
Amazon Scraping Tools for Market Research Agent.

These tools use the ScrapingDog API to fetch Amazon product data.
All tools are decorated with @tool to make them available to the agent.
"""

import os
from pathlib import Path
import random
import re
import sys
from typing import Any


# Add framework src to path to use inbuilt packages
# This must be done before importing framework modules
current_dir = Path(__file__).parent
runtime_dir = current_dir.parent.parent
framework_dir = runtime_dir.parent / "framework"
workspace_root = runtime_dir.parent.parent

sys.path.insert(0, str(framework_dir / "src"))
sys.path.insert(0, str(runtime_dir / "src"))
sys.path.insert(0, str(workspace_root))

# Import tool decorator from inbuilt framework
# Note: Import after sys.path manipulation to use local packages
from framework.agents.tool import tool  # noqa: E402
import requests  # noqa: E402


# --- Helper Functions ---


def parse_number_with_abbreviation(text: str | None) -> float | None:
    """
    Parses a number from text with abbreviation support (e.g., "1k+", "2.5m+").
    """
    if not text:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)([kmbKMB])?\+?", str(text))
    if not match:
        return None

    number = float(match.group(1))
    suffix = match.group(2)

    multipliers = {
        "k": 1_000,
        "m": 1_000_000,
        "b": 1_000_000_000,
    }

    if suffix:
        number *= multipliers.get(suffix.lower(), 1)

    return number


def calculate_prev_month_revenue(
    number_bought_text: str | None, price: str | float | None
) -> float | None:
    """
    Calculates estimated previous month revenue based on bought text and price.
    """
    if not number_bought_text or not price:
        return None

    current_month_bought = parse_number_with_abbreviation(number_bought_text)
    if current_month_bought is None:
        return None

    # Randomly adjust by ±10% for previous month estimate
    variation = 0.9 if random.random() < 0.5 else 1.1
    prev_month_bought = round(current_month_bought * variation)

    # Extract numeric price
    price_str = str(price)
    # Remove everything except digits and dot
    clean_price = re.sub(r"[^0-9.]", "", price_str)

    try:
        price_num = float(clean_price)
    except ValueError:
        return None

    if price_num <= 0:
        return None

    # Return revenue rounded to 2 decimal places
    return round(prev_month_bought * price_num, 2)


def add_prev_month_revenue(product: dict[str, Any]) -> dict[str, Any]:
    """
    Adds prev_month_revenue field to a product object.
    """
    if not product:
        return product

    revenue = calculate_prev_month_revenue(
        product.get("number_of_people_bought"), product.get("price")
    )

    if revenue is not None:
        product["prev_month_revenue"] = revenue

    return product


def _get_api_key() -> str:
    # Use environment variable for API key
    key = os.getenv("SCRAPINGDOG_API_KEY")
    if not key:
        return "6936dfa9ca3f38c504d29183"  # Fallback/Demo key
    return key


# --- Tools ---


@tool
def amazon_search_scraper(
    query: str,
    domain: str = "in",
    page: int = 1,
    country: str = "in",
    postal_code: str | None = None,
    language: str | None = None,
    premium: bool | None = None,
) -> dict[str, Any]:
    """
    Searches Amazon and returns a list of products matching your query.

    Args:
        query: Search query string
        domain: Amazon TLD, e.g., com, in, de, fr, co.uk (default: in)
        page: Page number
        country: ISO-3166 country code, default in
        postal_code: Optional postal code
        language: ISO 639-1 language code
        premium: Use premium proxies
    """
    api_key = _get_api_key()

    params = {
        "api_key": api_key,
        "domain": domain,
        "query": query,
        "page": page,
        "country": country,
    }

    if postal_code:
        params["postal_code"] = postal_code
    if language:
        params["language"] = language
    if premium is not None:
        params["premium"] = str(premium).lower()

    url = "https://api.scrapingdog.com/amazon/search"

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        # Add revenue calculation
        if data.get("results") and isinstance(data["results"], list):
            data["results"] = [add_prev_month_revenue(p) for p in data["results"]]

        return data
    except requests.RequestException as e:
        return {"error": f"API request failed: {e!s}"}


@tool
def amazon_product_scraper(
    asin: str,
    domain: str = "in",
    country: str = "in",
    postal_code: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """
    Retrieves comprehensive product details from Amazon by ASIN.

    Args:
        asin: Amazon product ASIN
        domain: Amazon TLD, e.g., com, in (default: in)
        country: ISO-3166 country code (default: in)
        postal_code: Optional postal code
        language: ISO 639-1 language code
    """
    api_key = _get_api_key()

    params = {
        "api_key": api_key,
        "domain": domain,
        "asin": asin,
        "country": country,
    }

    if postal_code:
        params["postal_code"] = postal_code
    if language:
        params["language"] = language

    url = "https://api.scrapingdog.com/amazon/product"

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        # Add revenue calculation
        add_prev_month_revenue(data)

        return data
    except requests.RequestException as e:
        return {"error": f"API request failed: {e!s}"}


@tool
def amazon_autocomplete_scraper(
    prefix: str,
    last_prefix: str | None = None,
    mid: str | None = None,
    suffix: str | None = None,
    language: str | None = "en",
) -> dict[str, Any]:
    """
    Generates Amazon search keyword suggestions based on partial search terms.

    Args:
        prefix: Partial search term to generate suggestions
        last_prefix: Optional last prefix
        mid: Merchant ID
        suffix: Optional suffix
        language: ISO 639-1 language code, default en
    """
    api_key = _get_api_key()

    params = {
        "api_key": api_key,
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

    url = "https://api.scrapingdog.com/amazon/autocomplete"

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": f"API request failed: {e!s}"}


@tool
def amazon_offers_scraper(
    asin: str,
    domain: str = "in",
    country: str = "in",
) -> dict[str, Any]:
    """
    Retrieves all available offers for a product.

    Args:
        asin: Amazon product ASIN
        domain: Amazon TLD
        country: ISO-3166 country code
    """
    api_key = _get_api_key()

    params = {
        "api_key": api_key,
        "domain": domain,
        "asin": asin,
        "country": country,
    }

    url = "https://api.scrapingdog.com/amazon/offers"

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": f"API request failed: {e!s}"}
