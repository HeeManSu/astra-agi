"""Market Research Agent for Amazon Marketplace Intelligence."""

import os
import sys


# Add examples directory to path for absolute imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))

from market_research.agent import market_research_agent
from market_research.tools import autocomplete, get_offers, get_product, get_reviews, search


__all__ = [
    "autocomplete",
    "get_offers",
    "get_product",
    "get_reviews",
    "market_research_agent",
    "search",
]
