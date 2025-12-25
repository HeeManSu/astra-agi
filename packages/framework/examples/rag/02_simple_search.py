"""
Example 2: Simple Knowledge Base Search
Demonstrates basic search functionality with different queries.
"""

import asyncio
import os

from framework.KnowledgeBase import KnowledgeBase, LanceDB, OpenAIEmbedder, RecursiveChunking


async def main():
    """Simple search example."""

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    print("=" * 60)
    print("Example 2: Simple Knowledge Base Search")
    print("=" * 60)

    # Setup knowledge base
    embedder = OpenAIEmbedder()
    vector_db = LanceDB(uri="examples/rag/data/lancedb_search", embedder=embedder)

    knowledge_base = KnowledgeBase(
        vector_db=vector_db,
        embedder=embedder,
        chunking=RecursiveChunking(chunk_size=300),
    )

    # Add content
    print("\n📚 Adding content...")

    await knowledge_base.add_content(
        text="""
        FastAPI is a modern web framework for building APIs with Python. It's based on
        standard Python type hints and is designed to be fast, easy to use, and production-ready.
        FastAPI automatically generates OpenAPI documentation and supports async operations.
        """,
        name="FastAPI Info",
    )

    await knowledge_base.add_content(
        text="""
        Async programming in Python allows you to write concurrent code using async/await syntax.
        The asyncio library provides the foundation for asynchronous I/O operations. This is
        particularly useful for I/O-bound tasks like network requests and database operations.
        """,
        name="Async Python",
    )

    await knowledge_base.add_content(
        text="""
        Vector databases are specialized databases designed to store and query high-dimensional
        vectors efficiently. They use similarity search algorithms to find vectors that are
        close to a query vector. This is essential for RAG systems and semantic search.
        """,
        name="Vector Databases",
    )

    print("✅ Content added\n")

    # Test different search queries
    queries = [
        "What is FastAPI?",
        "How does async work in Python?",
        "What are vector databases used for?",
    ]

    for query in queries:
        print(f"🔍 Query: {query}")
        results = await knowledge_base.search(query, limit=2)

        if results:
            print(f"   Top result: {results[0].content[:80]}...")
        else:
            print("   No results found")
        print()


if __name__ == "__main__":
    asyncio.run(main())
