"""
Example 8: Multiple Knowledge Bases
Demonstrates using multiple knowledge bases for different domains.
"""

import asyncio

from framework.KnowledgeBase import HuggingFaceEmbedder, KnowledgeBase, LanceDB, RecursiveChunking
from framework.agents import Agent
from framework.models import Gemini


async def main():
    """Multiple knowledge bases example."""

    print("=" * 60)
    print("Example 8: Multiple Knowledge Bases")
    print("=" * 60)

    # Using HuggingFace - no API key needed
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")

    # 1. Create technical documentation knowledge base
    print("\n📚 Creating Technical Documentation Knowledge Base...")
    tech_vector_db = LanceDB(uri="examples/rag/data/lancedb_tech", embedder=embedder)
    tech_kb = KnowledgeBase(
        vector_db=tech_vector_db,
        embedder=embedder,
        chunking=RecursiveChunking(chunk_size=400),
    )

    await tech_kb.add_content(
        text="""
        API Design Best Practices:
        1. Use RESTful conventions for endpoints
        2. Version your APIs (e.g., /v1/, /v2/)
        3. Return consistent response formats
        4. Use appropriate HTTP status codes
        5. Implement pagination for large datasets
        6. Include rate limiting
        7. Provide comprehensive error messages
        """,
        name="API Design Guide",
        metadata={"domain": "technical", "type": "best_practices"},
    )

    await tech_kb.add_content(
        text="""
        Database Optimization Techniques:
        - Use indexes on frequently queried columns
        - Normalize database schema appropriately
        - Use connection pooling
        - Implement query caching
        - Monitor slow queries
        - Consider read replicas for scaling
        """,
        name="Database Optimization",
        metadata={"domain": "technical", "type": "optimization"},
    )

    print("✅ Technical KB created")

    # 2. Create company policy knowledge base
    print("\n📚 Creating Company Policy Knowledge Base...")
    policy_vector_db = LanceDB(uri="examples/rag/data/lancedb_policy", embedder=embedder)
    policy_kb = KnowledgeBase(
        vector_db=policy_vector_db,
        embedder=embedder,
        chunking=RecursiveChunking(chunk_size=300),
    )

    await policy_kb.add_content(
        text="""
        Company Vacation Policy:
        - Full-time employees receive 20 vacation days per year
        - Vacation days accrue monthly at 1.67 days per month
        - Unused vacation days can be carried over up to 5 days
        - Vacation requests must be submitted at least 2 weeks in advance
        """,
        name="Vacation Policy",
        metadata={"domain": "hr", "type": "policy"},
    )

    await policy_kb.add_content(
        text="""
        Remote Work Policy:
        - Employees can work remotely up to 3 days per week
        - Core hours are 10 AM - 3 PM for team collaboration
        - Home office setup must meet ergonomic standards
        - Internet connection must be at least 25 Mbps
        """,
        name="Remote Work Policy",
        metadata={"domain": "hr", "type": "policy"},
    )

    print("✅ Policy KB created")

    # 3. Create agent with technical knowledge base
    print("\n🤖 Creating Technical Support Agent...")
    tech_agent = Agent(
        name="TechSupport",
        instructions="You are a technical support assistant. Use search_knowledge to find technical documentation and best practices.",
        model=Gemini("gemini-2.5-flash"),
        knowledge_base=tech_kb,
    )

    tech_question = "What are best practices for API design?"
    print(f"❓ Question: {tech_question}")
    tech_response = await tech_agent.invoke(tech_question)
    print(f"💬 Response: {tech_response[:200]}...\n")

    # 4. Create agent with policy knowledge base
    print("🤖 Creating HR Assistant...")
    hr_agent = Agent(
        name="HRAssistant",
        instructions="You are an HR assistant. Use search_knowledge to find company policies and answer employee questions.",
        model=Gemini("gemini-2.5-flash"),
        knowledge_base=policy_kb,
    )

    hr_question = "How many vacation days do I get per year?"
    print(f"❓ Question: {hr_question}")
    hr_response = await hr_agent.invoke(hr_question)
    print(f"💬 Response: {hr_response[:200]}...\n")

    # 5. List content from both knowledge bases
    print("📋 Content Summary:")
    tech_contents = await tech_kb.list_contents()
    policy_contents = await policy_kb.list_contents()

    print(f"  Technical KB: {len(tech_contents)} items")
    for content in tech_contents:
        print(f"    - {content.name}")

    print(f"  Policy KB: {len(policy_contents)} items")
    for content in policy_contents:
        print(f"    - {content.name}")


if __name__ == "__main__":
    asyncio.run(main())
