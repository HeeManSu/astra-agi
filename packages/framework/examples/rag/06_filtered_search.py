"""
Example 6: Search with Metadata Filters
Demonstrates filtering search results by metadata.
"""

import asyncio

from framework.KnowledgeBase import HuggingFaceEmbedder, KnowledgeBase, LanceDB, RecursiveChunking


async def main():
    """Filtered search example."""

    print("=" * 60)
    print("Example 6: Search with Metadata Filters")
    print("=" * 60)

    # Setup knowledge base (using HuggingFace - no API key needed)
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="examples/rag/data/lancedb_filtered", embedder=embedder)

    knowledge_base = KnowledgeBase(
        vector_db=vector_db,
        embedder=embedder,
        chunking=RecursiveChunking(chunk_size=300),
    )

    print("\n📚 Adding content with different metadata...")

    # Add content with different metadata
    await knowledge_base.add_content(
        text="""
        React is a JavaScript library for building user interfaces. It uses a component-based
        architecture and a virtual DOM for efficient rendering. React was developed by Facebook
        and is widely used in modern web development.
        """,
        name="React Guide",
        metadata={"category": "frontend", "language": "javascript", "framework": "react"},
    )

    await knowledge_base.add_content(
        text="""
        Vue.js is a progressive JavaScript framework for building user interfaces. It's designed
        to be incrementally adoptable and focuses on the view layer. Vue provides reactive data
        binding and component composition.
        """,
        name="Vue.js Guide",
        metadata={"category": "frontend", "language": "javascript", "framework": "vue"},
    )

    await knowledge_base.add_content(
        text="""
        Django is a high-level Python web framework that encourages rapid development and clean
        design. It follows the model-view-template (MVT) architectural pattern and includes
        an ORM, authentication, and admin interface out of the box.
        """,
        name="Django Guide",
        metadata={"category": "backend", "language": "python", "framework": "django"},
    )

    await knowledge_base.add_content(
        text="""
        Flask is a lightweight Python web framework. It's called a microframework because it
        doesn't require particular tools or libraries. Flask is simple and flexible, making
        it great for small to medium-sized applications.
        """,
        name="Flask Guide",
        metadata={"category": "backend", "language": "python", "framework": "flask"},
    )

    print("✅ Content added\n")

    # Search without filters
    print("🔍 Search 1: No filters (all content)")
    query = "web framework"
    results = await knowledge_base.search(query, limit=5)
    print(f"Query: {query}")
    print(f"Results: {len(results)}")
    for doc in results:
        print(f"  - {doc.name} ({doc.metadata.get('category')})")
    print()

    # Search with category filter (Note: LanceDB MVP doesn't fully support filters yet)
    # This demonstrates the API, but filters may not work in MVP
    print("🔍 Search 2: With category filter (frontend only)")
    print("Note: Filter support depends on vector database implementation")
    results = await knowledge_base.search(query, limit=5, filters={"category": "frontend"})
    print(f"Query: {query}")
    print(f"Results: {len(results)}")
    for doc in results:
        print(f"  - {doc.name} ({doc.metadata.get('category')})")
    print()

    # List content with filters
    print("📋 Listing content with metadata filters...")
    frontend_content = await knowledge_base.list_contents(filters={"category": "frontend"})
    print(f"Frontend content: {len(frontend_content)}")
    for content in frontend_content:
        print(f"  - {content.name}: {content.metadata}")

    python_content = await knowledge_base.list_contents(filters={"language": "python"})
    print(f"\nPython content: {len(python_content)}")
    for content in python_content:
        print(f"  - {content.name}: {content.metadata}")


if __name__ == "__main__":
    asyncio.run(main())
