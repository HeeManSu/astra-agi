"""
Example 1: Basic RAG with Text Content
Demonstrates the simplest RAG setup - adding text content and searching.
"""

import asyncio
import os

from framework.KnowledgeBase import KnowledgeBase, LanceDB, OpenAIEmbedder, RecursiveChunking
from framework.agents import Agent
from framework.models import Gemini


async def main():
    """Basic RAG example with text content."""

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    print("=" * 60)
    print("Example 1: Basic RAG with Text Content")
    print("=" * 60)

    # 1. Create embedder
    embedder = OpenAIEmbedder(model="text-embedding-3-small")

    # 2. Create vector database
    vector_db = LanceDB(uri="examples/rag/data/lancedb_basic", embedder=embedder)

    # 3. Create knowledge base
    knowledge_base = KnowledgeBase(
        vector_db=vector_db,
        embedder=embedder,
        chunking=RecursiveChunking(chunk_size=500, chunk_overlap=50),
    )

    print("\n📚 Adding content to knowledge base...")

    # 4. Add some text content
    content_id_1 = await knowledge_base.add_content(
        text="""
        Python is a high-level programming language known for its simplicity and readability.
        It was created by Guido van Rossum and first released in 1991. Python supports multiple
        programming paradigms including procedural, object-oriented, and functional programming.
        It has a large standard library and is widely used in web development, data science,
        artificial intelligence, and automation.
        """,
        name="Python Introduction",
        metadata={"topic": "programming", "language": "python"},
    )
    print(f"✅ Added content: {content_id_1}")

    content_id_2 = await knowledge_base.add_content(
        text="""
        Machine Learning is a subset of artificial intelligence that enables computers to
        learn and make decisions from data without being explicitly programmed. It uses algorithms
        to identify patterns in data and make predictions or classifications. Common types include
        supervised learning, unsupervised learning, and reinforcement learning.
        """,
        name="Machine Learning Basics",
        metadata={"topic": "ai", "category": "ml"},
    )
    print(f"✅ Added content: {content_id_2}")

    # 5. Search the knowledge base
    print("\n🔍 Searching knowledge base...")

    query = "What is Python used for?"
    results = await knowledge_base.search(query, limit=3)

    print(f"\nQuery: {query}")
    print(f"Found {len(results)} results:\n")

    for i, doc in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  Content: {doc.content[:100]}...")
        print(f"  Source: {doc.name}")
        print(f"  Metadata: {doc.metadata}")
        print()

    # 6. Use with agent
    print("\n🤖 Using knowledge base with agent...")

    agent = Agent(
        name="RAGAssistant",
        instructions="You are a helpful assistant with access to a knowledge base. Use the search_knowledge tool to find relevant information before answering questions.",
        model=Gemini("gemini-2.5-flash"),
        knowledge_base=knowledge_base,
    )

    response = await agent.invoke("What can you tell me about Python?")
    print(f"\nAgent Response:\n{response}\n")


if __name__ == "__main__":
    asyncio.run(main())
