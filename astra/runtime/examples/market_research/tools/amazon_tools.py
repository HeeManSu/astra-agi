"""
Market Research Tools for Amazon.

Tools that interact with ScrapingDog API to fetch Amazon product data.
"""

import json
import os
import random
import re
from typing import Any

from framework.tool import ToolSpec, bind_tool
import httpx
from pydantic import BaseModel, Field, RootModel


# Get API key from environment
SCRAPINGDOG_API_KEY = os.getenv("SCRAPINGDOG_API_KEY", "")


def parse_number_with_abbreviation(text: str | None) -> float | None:
    """Parse number from text like '700+', '1k+', '2.5m+'."""
    if not text:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)([kmbKMB])?\+?", str(text))
    if not match:
        return None

    number = float(match.group(1))
    suffix = match.group(2).lower() if match.group(2) else ""
    multipliers = {"k": 1000, "m": 1_000_000, "b": 1_000_000_000}

    return number * multipliers.get(suffix, 1)


# Helper function for revenue calculation
def calculate_monthly_revenue(data: dict) -> dict:
    """Add prev_month_revenue calculation to product data (Mastra Logic)."""
    try:
        bought_text = data.get("number_of_people_bought")
        price = data.get("price")

        if not bought_text or not price:
            return data

        current_month_bought = parse_number_with_abbreviation(bought_text)
        if current_month_bought is None:
            return data

        # Randomly adjust by ±10% for previous month estimate (matching Mastra)
        variation = 0.9 if random.random() < 0.5 else 1.1
        prev_month_bought = round(current_month_bought * variation)

        # Clean price string
        price_str = str(price).replace(",", "").replace("$", "").replace("₹", "").strip()
        price_value = float(price_str)

        if price_value > 0:
            data["prev_month_revenue"] = round(prev_month_bought * price_value, 2)
            data["estimated_monthly_sales"] = prev_month_bought

    except (ValueError, TypeError):
        pass

    return data


class DictOutput(RootModel):
    root: dict[str, Any]


class ListOutput(RootModel):
    root: list[Any]


class ProductInput(BaseModel):
    """Input for Amazon product scraper."""

    asin: str = Field(..., description="Amazon product ASIN")
    domain: str = Field(
        default="in", description="Amazon TLD, e.g., com, in, de, fr, co.uk (default: in)"
    )
    country: str = Field(default="in", description="ISO-3166 country code, default in")
    postal_code: str = Field(default="", description="Postal code for localized results")
    language: str = Field(default="en", description="ISO 639-1 language code, e.g., en, de, fr")


PRODUCT_SPEC = ToolSpec(
    name="amazon_product_scraper",
    description=(
        "Retrieves comprehensive product details from Amazon including title, price, ratings, "
        "availability, images, description, features, specifications, and seller information. "
        "Use this when you need detailed information about a specific product by ASIN. "
        "Ideal for competitive analysis, product research, and pricing intelligence."
    ),
    input_model=ProductInput,
    output_model=DictOutput,
    examples=[
        {
            "input": {"asin": "B00AP877FS", "domain": "com"},
            "output": {
                "title": "Cosmetic Brush Kit 5 Pcs Makeup Brush Travel Set Princessa - Pink",
                "price": "$6.95",
                "average_rating": 5,
                "availability_status": "In Stock",
                "images": ["https://m.media-amazon.com/images/I/41BWGQGj93L.jpg"],
            },
        }
    ],
)


@bind_tool(PRODUCT_SPEC)
async def amazon_product_scraper(input: ProductInput) -> DictOutput:
    """Get detailed Amazon product information by ASIN."""
    params = {
        "api_key": SCRAPINGDOG_API_KEY,
        "domain": input.domain,
        "asin": input.asin,
        "country": input.country,
    }
    print(params)
    if input.postal_code:
        params["postal_code"] = input.postal_code
    if input.language:
        params["language"] = input.language

    url = "https://api.scrapingdog.com/amazon/product"

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    result = calculate_monthly_revenue(data)
    return DictOutput(root=result)


# ============== AMAZON SEARCH SCRAPER ==============


class SearchInput(BaseModel):
    """Input for Amazon search scraper."""

    query: str = Field(..., description="Search query string")
    domain: str = Field(default="com", description="Amazon TLD, e.g., com, in, de, fr, co.uk")
    page: int = Field(default=1, description="Page number")
    country: str = Field(default="in", description="ISO-3166 country code")
    postal_code: str | None = Field(default=None, description="Postal code for localized results")
    language: str | None = Field(default=None, description="ISO 639-1 language code")
    premium: str | None = Field(default=None, description="Use premium proxies (true/false)")


SEARCH_SPEC = ToolSpec(
    name="amazon_search_scraper",
    description=(
        "Searches Amazon and returns a list of products matching your query with key data "
        "like title, price, rating, ASIN, and thumbnail. Perfect for discovering products in a niche, "
        "analyzing market landscape, identifying top competitors, and finding trending products. "
        "Returns paginated results for thorough market exploration."
    ),
    input_model=SearchInput,
    output_model=ListOutput,
    examples=[
        {
            "input": {"query": "spoon", "domain": "com", "page": 1},
            "output": [
                {
                    "title": "Amazon Basics Stainless Steel Dinner Spoons...",
                    "price_string": "$12.",
                    "stars": 4,
                    "total_reviews": "7,647",
                    "position": 1,
                }
            ],
        }
    ],
)


@bind_tool(SEARCH_SPEC)
async def amazon_search_scraper(input: SearchInput) -> ListOutput:
    """Search Amazon for products matching a query."""
    params = {
        "api_key": SCRAPINGDOG_API_KEY,
        "domain": input.domain,
        "query": input.query,
        "page": str(input.page),
        "country": input.country,
    }
    if input.postal_code:
        params["postal_code"] = input.postal_code
    if input.language:
        params["language"] = input.language
    if input.premium is not None:
        params["premium"] = str(input.premium).lower()

    url = "https://api.scrapingdog.com/amazon/search"

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        with open("amazon_search_scraper.json", "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    results = []

    # Handle dict response: {"search_message": "", "location": "...", "results": [...]}
    if isinstance(data, dict) and "results" in data:
        results = data.get("results", [])
    # Handle list response: [[results...], [pagination...]] or [results...]
    elif isinstance(data, list):
        for item in data:
            if (
                isinstance(item, list)
                and len(item) > 0
                and isinstance(item[0], dict)
                and "title" in item[0]
            ):
                results = item
                break
        if not results and len(data) > 0 and isinstance(data[0], dict):
            results = data

    if results:
        results = [calculate_monthly_revenue(p) for p in results]
        return ListOutput(root=results)

    # Fallback to empty list
    return ListOutput(root=[])


# ============== AMAZON AUTOCOMPLETE SCRAPER ==============


class AutocompleteInput(BaseModel):
    """Input for Amazon autocomplete scraper."""

    prefix: str = Field(..., description="Partial search term to generate suggestions")
    language: str = Field(default="en", description="ISO 639-1 language code, default en")


AUTOCOMPLETE_SPEC = ToolSpec(
    name="amazon_autocomplete_scraper",
    description=(
        "Generates Amazon search keyword suggestions based on partial search terms, "
        "revealing popular search queries and customer intent. Invaluable for keyword research, "
        "discovering long-tail keywords, identifying seasonal trends, optimizing product listings, "
        "and uncovering untapped market opportunities."
    ),
    input_model=AutocompleteInput,
    output_model=ListOutput,
    examples=[
        {
            "input": {"prefix": "spoon"},
            "output": [
                {"type": "KEYWORD", "keyword": "cricket noise maker prank"},
                {"type": "KEYWORD", "keyword": "cricket printer"},
            ],
        }
    ],
)


@bind_tool(AUTOCOMPLETE_SPEC)
async def amazon_autocomplete_scraper(input: AutocompleteInput) -> ListOutput:
    """Get Amazon autocomplete suggestions for a search prefix."""
    params = {
        "api_key": SCRAPINGDOG_API_KEY,
        "prefix": input.prefix,
        "language": input.language,
    }

    url = "https://api.scrapingdog.com/amazon/autocomplete"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return ListOutput(root=response.json())


# ============== AMAZON OFFERS SCRAPER ==============


class OffersInput(BaseModel):
    """Input for Amazon offers scraper."""

    asin: str = Field(..., description="Amazon product ASIN")
    domain: str = Field(
        default="in", description="Amazon TLD, e.g., com, in, de, fr, co.uk (default: in)"
    )
    country: str = Field(default="in", description="ISO-3166 country code, default in")
    postal_code: str | None = Field(default=None, description="Postal code for localized results")


OFFERS_SPEC = ToolSpec(
    name="amazon_offers_scraper",
    description=(
        "Retrieves all available offers for a product including prices from different sellers, "
        "shipping costs, seller ratings, fulfillment methods (FBA/FBM), stock availability, and condition. "
        "Crucial for competitive pricing strategy, identifying Buy Box opportunities, monitoring competitor pricing, "
        "and supplier discovery."
    ),
    input_model=OffersInput,
    output_model=DictOutput,
    examples=[
        {
            "input": {"asin": "B0CHX3QBCH", "domain": "in"},
            "output": {"offers": [{"price": 1999, "seller": "Amazon", "fulfillment": "FBA"}]},
        }
    ],
)


@bind_tool(OFFERS_SPEC)
async def amazon_offers_scraper(input: OffersInput) -> DictOutput:
    """Get all seller offers for an Amazon product."""
    params = {
        "api_key": SCRAPINGDOG_API_KEY,
        "domain": input.domain,
        "asin": input.asin,
        "country": input.country,
    }
    if input.postal_code:
        params["postal_code"] = input.postal_code

    url = "https://api.scrapingdog.com/amazon/offers"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return DictOutput(root=response.json())
