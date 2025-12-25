"""
Example 3: Agent with Knowledge Base Integration
Shows how agents automatically use knowledge base via search_knowledge tool.
"""

import asyncio
import os

from framework.KnowledgeBase import KnowledgeBase, LanceDB, OpenAIEmbedder
from framework.agents import Agent
from framework.models import Gemini


async def main():
    """Agent with knowledge base example."""

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    print("=" * 60)
    print("Example 3: Agent with Knowledge Base")
    print("=" * 60)

    # Setup knowledge base with company information
    embedder = OpenAIEmbedder()
    vector_db = LanceDB(uri="examples/rag/data/lancedb_agent", embedder=embedder)

    knowledge_base = KnowledgeBase(
        vector_db=vector_db,
        embedder=embedder,
        max_results=5,
    )

    print("\n📚 Populating knowledge base with company information...")

    # Add company information
    company_info = """
    Our company, TechCorp, was founded in 2020 and specializes in AI solutions.
    We have 50 employees across engineering, sales, and operations teams.
    Our main products include AI chatbots, data analytics platforms, and automation tools.
    We serve clients in healthcare, finance, and retail industries.
    Our headquarters is located in San Francisco, California.
    """

    await knowledge_base.add_content(
        text=company_info,
        name="Company Information",
        metadata={"type": "company_info", "department": "general"},
    )

    # Add product information
    product_info = """
    Our flagship product is an AI chatbot platform that helps businesses automate
    customer support. It supports multiple languages, integrates with popular CRM systems,
    and provides analytics dashboards. Pricing starts at $99/month for small businesses
    and scales up for enterprise customers.
    """

    await knowledge_base.add_content(
        text=product_info,
        name="Product Information",
        metadata={"type": "product", "category": "chatbot"},
    )

    print("✅ Knowledge base populated\n")

    # Create agent with knowledge base
    agent = Agent(
        name="CompanyAssistant",
        instructions="""
        You are a helpful assistant for TechCorp. You have access to a knowledge base
        containing company and product information. When users ask questions, use the
        search_knowledge tool to find relevant information before answering.
        Always cite your sources when possible.
        """,
        model=Gemini("gemini-2.5-flash"),
        knowledge_base=knowledge_base,
    )

    # Test questions
    questions = [
        "What does your company do?",
        "How many employees does TechCorp have?",
        "What is the pricing for your chatbot product?",
        "Where is your company located?",
    ]

    for question in questions:
        print(f"❓ Question: {question}")
        print("🤖 Agent is searching knowledge base and responding...\n")

        response = await agent.invoke(question)
        print(f"💬 Response: {response}\n")
        print("-" * 60)
        print()


if __name__ == "__main__":
    asyncio.run(main())
