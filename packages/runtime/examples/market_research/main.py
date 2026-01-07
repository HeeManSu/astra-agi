"""
Market Research Agent Example - Using Inbuilt Packages

This example demonstrates how to create a market research agent using
the inbuilt packages from the codebase (not published packages).

Run with:
    python -m examples.market_research.main

Or:
    cd packages/runtime
    python examples/market_research/main.py
"""

import os
from pathlib import Path
import sys


# Add framework and runtime src to path to use inbuilt packages
# This ensures we're using the local packages, not published ones
current_dir = Path(__file__).parent
runtime_dir = current_dir.parent.parent
framework_dir = runtime_dir.parent / "framework"
workspace_root = runtime_dir.parent.parent

# Add paths in order of priority (local packages first)
sys.path.insert(0, str(framework_dir / "src"))
sys.path.insert(0, str(runtime_dir / "src"))
sys.path.insert(0, str(workspace_root))
# Add examples directory to path so we can import tools
sys.path.insert(0, str(runtime_dir / "examples"))

# Now import from inbuilt packages
# Import server components from runtime
# Import our custom tools
# Import from same directory (works for both script and module execution)
import importlib.util

from astra.server import AstraServer, ServerConfig
from dotenv import load_dotenv
from framework.agents.agent import Agent
from framework.models.aws.bedrock import Bedrock
from framework.storage.databases.mongodb import MongoDBStorage
import uvicorn


tools_path = current_dir / "tools.py"
spec = importlib.util.spec_from_file_location("market_research_tools", tools_path)
if spec and spec.loader:
    tools_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tools_module)

    amazon_autocomplete_scraper = tools_module.amazon_autocomplete_scraper
    amazon_offers_scraper = tools_module.amazon_offers_scraper
    amazon_product_scraper = tools_module.amazon_product_scraper
    amazon_search_scraper = tools_module.amazon_search_scraper
else:
    raise ImportError(f"Could not load tools from {tools_path}")


load_dotenv()

# Define the instructions (exact copy from market-research-agent.ts)
INSTRUCTIONS = """
# Market Research Specialist - SellerGeni

Expert e-commerce advisor for Amazon sellers. Provide clear, actionable insights focused on revenue impact. Default to 🇮🇳 India (amazon.in).

## Tools & Capabilities

1. **Product Analysis** (ASIN): Price, ratings, reviews, monthly revenue, BSR, sentiment, seller info
2. **Market Search** (keyword): Competitive landscape, price ranges, revenue, market leaders
3. **Search Behavior** (autocomplete): Customer search trends, keyword opportunities
4. **Pricing Intel** (offers): Seller competition, pricing dynamics, Buy Box, fulfillment

## Standard Report Format

### Executive Summary
2-3 sentences highlighting key finding and decision impact.

### Performance Metrics
| Metric | Value | Impact |
|--------|-------|--------|
| Price | $XX.XX | Market positioning |
| Rating | X.X/5 (XXX reviews) | Trust level |
| Monthly Revenue | $X,XXX | Demand strength |
| BSR | #XX | Competition level |

### Analysis
Insights organized by theme - explain business meaning, not just data.

### Recommendations
- **This Week**: Immediate actions
- **This Month**: Short-term opportunities
- **This Quarter**: Strategic positioning

### Risks
Challenges and limitations to consider.

## Revenue Guidelines ⚠️ CRITICAL

✅ **Always**:
- Show **monthly revenue** only (never annualize)
- Display: "Monthly Revenue: ₹X,XXX"
- Include in all comparison tables
- Add context: "Indicates [demand level/position]"

❌ **Never**:
- Calculate annual (×12) or project future
- Omit "Monthly" qualifier
- Estimate when unavailable

## Competitive Analysis

| Product | Price | Rating | Reviews | Monthly Revenue | BSR | Advantage |
|---------|-------|--------|---------|----------------|-----|-----------|
| A | $XX | X.X/5 | XXX | $X,XXX | #XX | [Strength] |

**Leaders**: 💰 Revenue | ⭐ Satisfaction | 💵 Value | 🎯 Gap Opportunity

## Customer Sentiment

Show star distribution visually, extract review themes, quote feedback, identify improvement opportunities.

## Market Entry Assessment

Evaluate 3 criteria (✅/❌):
1. **Demand**: Revenue >$10K/mo, rating >4.0, active reviews, BSR <5K
2. **Competition**: No monopoly (>40%), 30%+ margins, differentiation possible
3. **Viability**: TAM >$100K/mo, suppliers available, clear value prop

**Verdict**: GO / CAUTION / NO - [reasoning]

## Supported Marketplaces

🇮🇳 India (₹) DEFAULT | 🇺🇸 USA ($) | 🇬🇧 UK (£) | 🇩🇪 Germany (€) | 🇫🇷 France (€) | 🇨🇦 Canada (C$) | 🇮🇹 Italy (€) | 🇪🇸 Spain (€) | 🇯🇵 Japan (¥)

## Error Handling

When research fails:
1. Acknowledge: "Brief issue gathering [data]"
2. Offer: Retry / Adjust / Try different market / Use partial data
3. After 3 attempts: Suggest alternative or manual verification

## Communication

**Use**: Active voice, specific numbers, business terms, qualifiers ("data indicates...")
**Avoid**: Jargon, certainty, raw data, generic advice

**Symbols**: 📈 Growth | 📉 Decline | 🎯 Goal | ⚠️ Warning | 💡 Insight | ✅ Confirmed | ❌ Problem | 🔥 Urgent | 💰 Financial | ⭐ Quality

## Research Depth

- **Quick** (2-3 queries): Search + top competitors + benchmark
- **Standard** (4-6): Landscape + top 5 deep dive + pricing
- **Deep** (8-12): Multi-segment + top 10 + suppliers + adjacent categories

## Quality Checklist

✅ Revenue shown | Customer sentiment | Competitive context | Specific actions | Marketplace ID | Impact quantified

**Goal**: Transform data into competitive advantage. Insight quality over information quantity.
"""


def create_market_agent():
    """Create the market research agent with Bedrock model and MongoDB storage."""
    # Configure Bedrock model
    # Note: For ap-south-1 region, use "apac." prefix models (not "us." prefix)
    # This matches the TypeScript implementation which uses: apac.amazon.nova-pro-v1:0
    model = Bedrock(
        model_id="apac.amazon.nova-pro-v1:0",  # APAC model for ap-south-1 region
        aws_region="ap-south-1",
    )

    # Initialize storage
    # Agent will wrap this in AgentStorage internally
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongo_storage = MongoDBStorage(
        url=mongo_url,
        db_name="astra_market_research",
    )

    agent = Agent(
        name="Market Research Agent",
        model=model,
        instructions=INSTRUCTIONS,
        storage=mongo_storage,  # Pass StorageBackend directly, Agent wraps it
        tools=[
            amazon_product_scraper,
            amazon_search_scraper,
            amazon_autocomplete_scraper,
            amazon_offers_scraper,
        ],
        code_mode=False,  # Disable code mode - use traditional tool calling
    )
    return agent, mongo_storage


if __name__ == "__main__":
    try:
        print("Creating market research agent...")
        agent, mongo_storage = create_market_agent()
        print("✓ Agent created successfully")

        print("Creating server...")
        server = AstraServer(
            agents={"market-research": agent},
            storage=mongo_storage,  # Pass storage backend explicitly
            config=ServerConfig(
                name="Market Research API",
                description="AI-powered Amazon market research agent",
                version="1.0.0",
                playground_enabled=True,
                cors_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
                jwt_secret=os.getenv("ASTRA_JWT_SECRET", "dev-secret"),
            ),
        )
        print("✓ Server created successfully")

        # Ensure Playground frontend talks to the same host as uvicorn
        os.environ["HOST"] = "127.0.0.1"
        os.environ["PORT"] = "8000"

        print("Creating FastAPI app...")
        app = server.create_app()
        print("✓ FastAPI app created successfully")

        print("\n" + "=" * 60)
        print("🚀 Starting Market Research Agent Server...")
        print("=" * 60)
        print("📊 API available at: http://127.0.0.1:8000/api")
        print("👨‍💻 Playground: http://127.0.0.1:8000/")
        print("📚 API Docs: http://127.0.0.1:8000/docs")
        print("=" * 60)
        print("\nPress Ctrl+C to stop the server\n")

        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        import traceback

        traceback.print_exc()
        raise
