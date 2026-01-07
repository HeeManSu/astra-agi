import os
from pathlib import Path
import sys


# Add current directory to sys.path to allow importing 'tools'
sys.path.append(str(Path(__file__).parent))

# Import correct storage components
from astra import Agent, AgentStorage, Bedrock, MongoDBStorage
from astra.server import AstraServer, ServerConfig
from dotenv import load_dotenv

# Import our custom tools
from tools import (
    amazon_autocomplete_scraper,
    amazon_offers_scraper,
    amazon_product_scraper,
    amazon_search_scraper,
)
import uvicorn


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
    # Configure Bedrock model
    # Note: We are using "amazon.apac.nova.pro" as requested,
    # but ensure your AWS region (e.g., us-east-1) supports this model ID.
    # Often for Nova Pro it might be "amazon.nova-pro-v1:0" or similar.
    # Using the exact ID from the request.
    model = Bedrock(
        model_id="amazon.apac.nova.pro",  # Changed to standard ID, user provided "amazon.apac.nova.pro" which seems internal/specific
        aws_region="ap-south-1",
    )

    # Initialize storage
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongo_storage = MongoDBStorage(
        url=mongo_url,
        db_name="astra_market_research",
    )
    storage = AgentStorage(storage=mongo_storage)

    agent = Agent(
        name="Market Research Agent",
        model=model,
        instructions=INSTRUCTIONS,
        storage=storage,
        tools=[
            amazon_product_scraper,
            amazon_search_scraper,
            amazon_autocomplete_scraper,
            amazon_offers_scraper,
        ],
    )
    return agent, storage


if __name__ == "__main__":
    agent, storage = create_market_agent()

    server = AstraServer(
        agents={"market-research": agent},
        storage=storage,  # Pass storage generic explicitly
        config=ServerConfig(
            name="Market Research API",
            description="AI-powered Amazon market research agent",
            version="1.0.0",
            playground_enabled=True,
            cors_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
            jwt_secret=os.getenv("ASTRA_JWT_SECRET", "dev-secret"),
        ),
    )

    # Ensure Playground frontend talks to the same host as uvicorn
    os.environ["HOST"] = "127.0.0.1"

    app = server.create_app()

    print("\n🚀 Starting Market Research Agent Server...")
    print("Playground: http://127.0.0.1:8000/playground")

    uvicorn.run(app, host="127.0.0.1", port=8000)
