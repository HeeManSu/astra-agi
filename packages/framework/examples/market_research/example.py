"""Example usage of the Market Research Agent."""

import asyncio
import os
import sys

from packages.framework.examples.market_research.agent import market_research_agent


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))


async def main():
    """Run example queries with the Market Research Agent."""
    # Example 1: Product Analysis
    query1 = "Get me the product details for ASIN B00AP877FS"
    response1 = await market_research_agent.invoke(query1)
    print(f"Query: {query1}")
    print(f"Response: {response1}\n")

    # # Example 2: Market Research
    # query2 = "Research the wireless earbuds market on Amazon US"
    # response2 = await market_research_agent.invoke(query2)
    # print(f"Query: {query2}")
    # print(f"Response: {response2}\n")

    # # Example 3: Keyword Research
    # query3 = "What are popular search terms for 'wireless' on Amazon?"
    # response3 = await market_research_agent.invoke(query3)
    # print(f"Query: {query3}")
    # print(f"Response: {response3}\n")


if __name__ == "__main__":
    asyncio.run(main())
