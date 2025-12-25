"""
E-commerce Product Launch Team Example.

This example demonstrates a complex multi-agent team that coordinates product launches
on e-commerce platforms. The team includes specialized agents for market research,
content creation, SEO optimization, pricing analysis, and quality assurance.

Features demonstrated:
- Multiple specialized agents with distinct roles
- Sequential and parallel delegation
- Tool integration (Amazon marketplace tools)
- Memory and context management
- Real-world workflow orchestration
"""

import asyncio
import os
import sys


# Add framework src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))

from framework.agents.agent import Agent
from framework.agents.tool import tool
from framework.models.aws.bedrock import Bedrock
from framework.models.google.gemini import Gemini
from framework.storage.databases.libsql import LibSQLStorage
from framework.storage.memory import AgentStorage
from framework.team import Team, TeamMember

# Import Amazon marketplace tools (from market_research example)
from market_research.tools import (
    autocomplete,
    get_offers,
    get_product,
    get_reviews,
    search,
)


@tool(module="content")
def generate_product_description(
    product_name: str,
    features: list[str],
    target_audience: str,
    tone: str = "professional",
) -> str:
    """Generate a compelling product description.

    Args:
        product_name: Name of the product
        features: List of key product features
        target_audience: Target customer segment
        tone: Writing tone (professional, casual, technical)

    Returns:
        Generated product description
    """
    # In a real implementation, this would call an LLM or template engine
    features_text = ", ".join(features)
    return f"""
    {product_name}

    Perfect for {target_audience}, this product offers:
    {features_text}

    Experience the difference with our premium quality {product_name.lower()}.
    """


@tool(module="seo")
def analyze_keywords(query: str, domain: str = "com") -> dict:
    """Analyze keyword competitiveness and search volume.

    Args:
        query: Search query to analyze
        domain: Amazon domain (com, co.uk, etc.)

    Returns:
        Keyword analysis with suggestions
    """
    # In a real implementation, this would call a keyword research API
    return {
        "primary_keyword": query,
        "suggestions": [f"{query} review", f"best {query}", f"{query} price"],
        "competition": "medium",
        "search_volume": "high",
    }


@tool(module="pricing")
def calculate_optimal_price(
    competitor_prices: list[float],
    cost: float,
    margin_target: float = 0.30,
) -> dict:
    """Calculate optimal pricing based on competitors and cost.

    Args:
        competitor_prices: List of competitor prices
        cost: Product cost
        margin_target: Target profit margin (default: 0.30 = 30%)

    Returns:
        Pricing recommendations
    """
    if not competitor_prices:
        optimal = cost * (1 + margin_target)
        return {
            "recommended_price": round(optimal, 2),
            "min_price": round(cost * 1.15, 2),
            "max_price": round(cost * 1.50, 2),
            "margin": margin_target,
        }

    avg_competitor = sum(competitor_prices) / len(competitor_prices)
    min_competitor = min(competitor_prices)
    max_competitor = max(competitor_prices)

    # Price competitively but maintain margin
    recommended = max(cost * (1 + margin_target), min_competitor * 0.95)

    return {
        "recommended_price": round(recommended, 2),
        "min_price": round(cost * 1.15, 2),
        "max_price": round(max_competitor * 0.98, 2),
        "avg_competitor_price": round(avg_competitor, 2),
        "margin": round((recommended - cost) / recommended, 2),
    }


@tool(module="qa")
def validate_product_info(
    title: str,
    description: str,
    price: float,
    features: list[str],
) -> dict:
    """Validate product information for completeness and quality.

    Args:
        title: Product title
        description: Product description
        price: Product price
        features: List of features

    Returns:
        Validation results with issues and recommendations
    """
    issues = []
    recommendations = []

    # Validate title
    if len(title) < 10:
        issues.append("Title is too short (minimum 10 characters)")
    if len(title) > 200:
        issues.append("Title is too long (maximum 200 characters)")

    # Validate description
    if len(description) < 100:
        issues.append("Description is too short (minimum 100 characters)")
    if len(description) < 500:
        recommendations.append("Consider expanding description for better SEO")

    # Validate price
    if price <= 0:
        issues.append("Price must be greater than 0")
    if price > 10000:
        recommendations.append("Verify high price is correct")

    # Validate features
    if len(features) < 3:
        issues.append("Add at least 3 product features")
    if len(features) > 20:
        recommendations.append("Consider grouping similar features")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "recommendations": recommendations,
        "score": max(0, 100 - len(issues) * 20),
    }


# Initialize models
bedrock_model = Bedrock(
    model_id="us.amazon.nova-pro-v1:0",
    region="ap-south-1",
)

gemini_model = Gemini("gemini-2.5-flash")


# 1. Market Researcher Agent
market_researcher = Agent(
    name="Market Researcher",
    model=bedrock_model,
    instructions="""
    You are an expert market researcher specializing in e-commerce market analysis.

    Your responsibilities:
    - Research competitor products and pricing
    - Analyze customer reviews and sentiment
    - Identify market trends and opportunities
    - Provide data-driven insights for product positioning

    Use the Amazon tools to:
    - Search for similar products
    - Get detailed product information
    - Analyze customer reviews
    - Check competitor pricing and offers

    Always provide structured, actionable insights with specific data points.
    """,
    tools=[get_product, search, get_reviews, get_offers, autocomplete],
    code_mode=False,
)

# 2. Content Writer Agent
content_writer = Agent(
    name="Content Writer",
    model=gemini_model,
    instructions="""
    You are a professional e-commerce content writer specializing in product descriptions
    and marketing copy.

    Your responsibilities:
    - Write compelling product titles and descriptions
    - Create marketing copy that converts
    - Adapt tone and style for target audience
    - Ensure clarity and persuasiveness

    Guidelines:
    - Use clear, benefit-focused language
    - Include relevant keywords naturally
    - Highlight unique selling points
    - Maintain brand voice consistency
    - Optimize for both customers and search engines
    """,
    tools=[generate_product_description],
    code_mode=False,
)

# 3. SEO Specialist Agent
seo_specialist = Agent(
    name="SEO Specialist",
    model=gemini_model,
    instructions="""
    You are an SEO expert specializing in e-commerce optimization.

    Your responsibilities:
    - Research and identify high-value keywords
    - Optimize product titles and descriptions for search
    - Analyze keyword competitiveness
    - Provide SEO recommendations

    Focus on:
    - Long-tail keywords with commercial intent
    - Search volume and competition balance
    - Natural keyword integration
    - Amazon A9 algorithm best practices
    """,
    tools=[autocomplete, analyze_keywords],
    code_mode=False,
)

# 4. Pricing Analyst Agent
pricing_analyst = Agent(
    name="Pricing Analyst",
    model=gemini_model,
    instructions="""
    You are a pricing strategist specializing in competitive pricing analysis.

    Your responsibilities:
    - Analyze competitor pricing
    - Calculate optimal pricing strategies
    - Balance profitability with competitiveness
    - Provide pricing recommendations

    Consider:
    - Product cost and target margins
    - Competitor pricing landscape
    - Market positioning goals
    - Price elasticity factors
    """,
    tools=[calculate_optimal_price],
    code_mode=False,
)

# 5. Quality Assurance Agent
qa_specialist = Agent(
    name="Quality Assurance",
    model=gemini_model,
    instructions="""
    You are a quality assurance specialist ensuring product information accuracy
    and completeness.

    Your responsibilities:
    - Validate product information completeness
    - Check for errors and inconsistencies
    - Ensure compliance with platform guidelines
    - Provide improvement recommendations

    Check for:
    - Complete product details
    - Accurate pricing and specifications
    - Proper formatting and grammar
    - Platform guideline compliance
    """,
    tools=[validate_product_info],
    code_mode=False,
)


# Initialize storage for conversation history
# Create LibSQL storage backend
db_url = "sqlite+aiosqlite:///./product_launch_team.db"
libsql_storage = LibSQLStorage(url=db_url, echo=False)

# Wrap in AgentStorage for team use
# Note: Storage will auto-connect on first use, but you can also connect explicitly:
# await libsql_storage.connect()
storage = AgentStorage(storage=libsql_storage)

# Create the team
product_launch_team = Team(
    name="Product Launch Team",
    model=bedrock_model,  # Leader uses powerful model for coordination
    members=[
        TeamMember(
            id="market-researcher",
            name="Market Researcher",
            description=(
                "Researches competitor products, analyzes customer reviews, "
                "and provides market insights. Use for competitive analysis, "
                "market validation, and trend identification."
            ),
            agent=market_researcher,
        ),
        TeamMember(
            id="content-writer",
            name="Content Writer",
            description=(
                "Creates compelling product descriptions and marketing copy. "
                "Use for writing titles, descriptions, and promotional content."
            ),
            agent=content_writer,
        ),
        TeamMember(
            id="seo-specialist",
            name="SEO Specialist",
            description=(
                "Optimizes content for search engines and researches keywords. "
                "Use for SEO optimization, keyword research, and search visibility."
            ),
            agent=seo_specialist,
        ),
        TeamMember(
            id="pricing-analyst",
            name="Pricing Analyst",
            description=(
                "Analyzes competitor pricing and calculates optimal pricing strategies. "
                "Use for pricing decisions, competitive analysis, and margin optimization."
            ),
            agent=pricing_analyst,
        ),
        TeamMember(
            id="qa-specialist",
            name="Quality Assurance",
            description=(
                "Validates product information for accuracy and completeness. "
                "Use for quality checks, compliance verification, and final review."
            ),
            agent=qa_specialist,
        ),
    ],
    instructions="""
    You are the Product Launch Team Leader coordinating a team of specialists
    to prepare products for e-commerce launch.

    ## Your Team Members:
    - Market Researcher: Provides competitive analysis and market insights
    - Content Writer: Creates compelling product descriptions and copy
    - SEO Specialist: Optimizes for search visibility
    - Pricing Analyst: Determines optimal pricing strategies
    - Quality Assurance: Validates information quality and completeness

    ## Workflow:
    1. **Research Phase**: Delegate to Market Researcher to analyze competitors and market
    2. **Content Phase**: Delegate to Content Writer to create product descriptions
    3. **SEO Phase**: Delegate to SEO Specialist to optimize keywords and content
    4. **Pricing Phase**: Delegate to Pricing Analyst to determine optimal pricing
    5. **QA Phase**: Delegate to Quality Assurance for final validation

    ## Guidelines:
    - Coordinate members sequentially for complex launches
    - Use parallel delegation when tasks are independent (e.g., SEO + Pricing)
    - Synthesize all results into a comprehensive launch package
    - Ensure all information is validated before finalizing
    - Provide clear, actionable recommendations

    ## Output Format:
    Present the final launch package with:
    - Product title and description
    - SEO-optimized keywords
    - Pricing recommendations
    - Quality assurance report
    - Market insights summary
    """,
    description=(
        "A coordinated team of specialists that prepares products for e-commerce launch "
        "through market research, content creation, SEO optimization, pricing analysis, "
        "and quality assurance."
    ),
    allow_parallel=True,  # Enable parallel execution when appropriate
    max_parallel=3,  # Max 3 concurrent delegations
    max_delegations=15,  # Safety limit
    timeout=600.0,  # 10 minutes for complex launches
    member_timeout=120.0,  # 2 minutes per member
    storage=storage,  # Enable conversation history
)


async def example_simple_launch():
    """Example: Simple product launch request."""
    print("=" * 80)
    print("Example 1: Simple Product Launch")
    print("=" * 80)

    query = """
    Help me launch a new wireless Bluetooth earbuds product on Amazon.

    Product details:
    - Name: ProSound Wireless Earbuds
    - Key features: Noise cancellation, 30-hour battery, water-resistant
    - Target audience: Active professionals and fitness enthusiasts
    - Cost: $25 per unit
    - Target margin: 35%
    """

    response = await product_launch_team.invoke(query)
    print("\n" + "=" * 80)
    print("TEAM RESPONSE:")
    print("=" * 80)
    print(response)
    print("\n")


async def example_complex_launch():
    """Example: Complex product launch with specific requirements."""
    print("=" * 80)
    print("Example 2: Complex Product Launch")
    print("=" * 80)

    query = """
    I need to launch a premium smartwatch product. Here's what I need:

    1. Research the smartwatch market on Amazon - find top competitors and their pricing
    2. Analyze customer reviews of top 3 competitors to identify pain points
    3. Create a compelling product title and description for "TechWatch Pro"
    4. Research and suggest 10 high-value keywords for SEO
    5. Calculate optimal pricing (my cost is $80, target margin 40%)
    6. Validate all product information before finalizing

    Product features:
    - Heart rate monitoring
    - GPS tracking
    - 7-day battery life
    - Water resistant (50m)
    - Sleep tracking
    - Smart notifications

    Target audience: Health-conscious professionals and athletes
    """

    response = await product_launch_team.invoke(query)
    print("\n" + "=" * 80)
    print("TEAM RESPONSE:")
    print("=" * 80)
    print(response)
    print("\n")


async def example_with_memory():
    """Example: Using conversation history for iterative refinement."""
    print("=" * 80)
    print("Example 3: Iterative Refinement with Memory")
    print("=" * 80)

    thread_id = "product-launch-001"

    # First request
    query1 = """
    Research the wireless speaker market on Amazon. Find top 5 competitors
    and analyze their pricing and customer reviews.
    """
    print("Request 1: Market Research")
    response1 = await product_launch_team.invoke(query1, thread_id=thread_id)
    print(f"Response: {response1[:200]}...\n")

    # # Follow-up request (uses conversation history)
    # query2 = """
    # Based on the research, create a product description for a new wireless
    # speaker that addresses the pain points you found. Also calculate optimal
    # pricing if my cost is $45 and I want 30% margin.
    # """
    # print("Request 2: Content + Pricing (uses previous context)")
    # response2 = await product_launch_team.invoke(query2, thread_id=thread_id)
    # print(f"Response: {response2[:200]}...\n")


async def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("E-commerce Product Launch Team - Examples")
    print("=" * 80)
    print("\nThis example demonstrates:")
    print("- Multi-agent coordination")
    print("- Sequential and parallel delegation")
    print("- Tool integration")
    print("- Memory and context management")
    print("- Real-world workflow orchestration")
    print("\n")

    # Run examples
    try:
        # Uncomment the example you want to run:
        # await example_simple_launch()
        # await example_complex_launch()
        await example_with_memory()
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
