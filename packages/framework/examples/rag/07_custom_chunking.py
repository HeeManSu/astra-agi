"""
Example 7: Custom Chunking Strategies
Demonstrates different chunking strategies and their effects.
"""

import asyncio
import os

from framework.KnowledgeBase import KnowledgeBase, LanceDB, OpenAIEmbedder
from framework.KnowledgeBase.chunking.recursive import RecursiveChunking


async def main():
    """Custom chunking example."""

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    print("=" * 60)
    print("Example 7: Custom Chunking Strategies")
    print("=" * 60)

    # Long document for chunking demonstration
    long_document = (
        """
    Chapter 1: Introduction to Machine Learning

    Machine learning is a method of data analysis that automates analytical model building.
    It is a branch of artificial intelligence based on the idea that systems can learn from
    data, identify patterns and make decisions with minimal human intervention.

    Chapter 2: Types of Machine Learning

    There are three main types of machine learning: supervised learning, unsupervised learning,
    and reinforcement learning. Supervised learning uses labeled data to train models.
    Unsupervised learning finds patterns in unlabeled data. Reinforcement learning uses rewards
    and penalties to guide learning.

    Chapter 3: Common Algorithms

    Popular machine learning algorithms include linear regression, decision trees, random forests,
    support vector machines, and neural networks. Each algorithm has its strengths and is suited
    for different types of problems.

    Chapter 4: Applications

    Machine learning is used in many applications including image recognition, natural language
    processing, recommendation systems, fraud detection, and autonomous vehicles. The technology
    continues to evolve and find new applications.
    """
        * 2
    )  # Make it longer

    embedder = OpenAIEmbedder()

    print("\n📚 Testing different chunking strategies...\n")

    # 1. Small chunks
    print("1️⃣ Small chunks (chunk_size=200, overlap=20)")
    vector_db_1 = LanceDB(uri="examples/rag/data/lancedb_chunk_small", embedder=embedder)
    kb_small = KnowledgeBase(
        vector_db=vector_db_1,
        embedder=embedder,
        chunking=RecursiveChunking(chunk_size=200, chunk_overlap=20),
    )

    content_id_1 = await kb_small.add_content(text=long_document, name="ML Guide - Small Chunks")
    results = await kb_small.search("machine learning algorithms", limit=3)
    print(f"   Chunks created: {len(results)} (showing first 3)")
    print(
        f"   Average chunk length: {sum(len(r.content) for r in results) / len(results) if results else 0:.0f} chars"
    )
    print()

    # 2. Medium chunks
    print("2️⃣ Medium chunks (chunk_size=500, overlap=50)")
    vector_db_2 = LanceDB(uri="examples/rag/data/lancedb_chunk_medium", embedder=embedder)
    kb_medium = KnowledgeBase(
        vector_db=vector_db_2,
        embedder=embedder,
        chunking=RecursiveChunking(chunk_size=500, chunk_overlap=50),
    )

    content_id_2 = await kb_medium.add_content(text=long_document, name="ML Guide - Medium Chunks")
    results = await kb_medium.search("machine learning algorithms", limit=3)
    print(f"   Chunks created: {len(results)} (showing first 3)")
    print(
        f"   Average chunk length: {sum(len(r.content) for r in results) / len(results) if results else 0:.0f} chars"
    )
    print()

    # 3. Large chunks
    print("3️⃣ Large chunks (chunk_size=1000, overlap=100)")
    vector_db_3 = LanceDB(uri="examples/rag/data/lancedb_chunk_large", embedder=embedder)
    kb_large = KnowledgeBase(
        vector_db=vector_db_3,
        embedder=embedder,
        chunking=RecursiveChunking(chunk_size=1000, chunk_overlap=100),
    )

    content_id_3 = await kb_large.add_content(text=long_document, name="ML Guide - Large Chunks")
    results = await kb_large.search("machine learning algorithms", limit=3)
    print(f"   Chunks created: {len(results)} (showing first 3)")
    print(
        f"   Average chunk length: {sum(len(r.content) for r in results) / len(results) if results else 0:.0f} chars"
    )
    print()

    # Compare search results
    print("🔍 Comparing search quality across chunk sizes...")
    query = "What are the types of machine learning?"

    print(f"\nQuery: {query}\n")

    for kb, name in [(kb_small, "Small"), (kb_medium, "Medium"), (kb_large, "Large")]:
        results = await kb.search(query, limit=1)
        if results:
            print(f"{name} chunks - Top result:")
            print(f"  {results[0].content[:150]}...")
            print()


if __name__ == "__main__":
    asyncio.run(main())
