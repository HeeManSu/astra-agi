"""
Example 9: Comprehensive RAG Workflow
Demonstrates a complete RAG system with all features: ingestion, search, management, and agent integration.
"""

import asyncio
from pathlib import Path

from framework.KnowledgeBase import HuggingFaceEmbedder, KnowledgeBase, LanceDB, RecursiveChunking
from framework.KnowledgeBase.vectordb.base import SearchType
from framework.agents import Agent
from framework.models import Gemini


async def main():
    """Comprehensive RAG example."""

    print("=" * 60)
    print("Example 9: Comprehensive RAG Workflow")
    print("=" * 60)

    # Setup knowledge base with custom configuration (using HuggingFace - no API key needed)
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(
        uri="examples/rag/data/lancedb_comprehensive",
        table_name="comprehensive_docs",
        embedder=embedder,
    )

    knowledge_base = KnowledgeBase(
        vector_db=vector_db,
        embedder=embedder,
        chunking=RecursiveChunking(chunk_size=500, chunk_overlap=50),
        max_results=10,
    )

    print("\n📚 Phase 1: Content Ingestion")
    print("-" * 60)

    # Add multiple content types with metadata
    content_ids = []

    # Technical content
    content_id_1 = await knowledge_base.add_content(
        text="""
        Microservices Architecture:
        Microservices is an architectural approach where applications are built as a collection
        of small, independent services. Each service runs in its own process and communicates
        via well-defined APIs. Benefits include scalability, technology diversity, and independent
        deployment. Challenges include distributed system complexity and data consistency.
        """,
        name="Microservices Architecture",
        metadata={
            "category": "architecture",
            "difficulty": "advanced",
            "tags": ["microservices", "distributed"],
        },
    )
    content_ids.append(content_id_1)
    print("✅ Added: Microservices Architecture")

    content_id_2 = await knowledge_base.add_content(
        text="""
        GraphQL vs REST:
        GraphQL is a query language for APIs that allows clients to request exactly the data
        they need. REST uses multiple endpoints with fixed data structures. GraphQL provides
        more flexibility but requires more upfront design. REST is simpler and more widely
        adopted. Choose GraphQL for complex data requirements, REST for simplicity.
        """,
        name="GraphQL vs REST",
        metadata={
            "category": "api",
            "difficulty": "intermediate",
            "tags": ["graphql", "rest", "api"],
        },
    )
    content_ids.append(content_id_2)
    print("✅ Added: GraphQL vs REST")

    # Create and add file content
    print("\n📄 Creating and adding file content...")
    data_dir = Path("examples/rag/data")
    data_dir.mkdir(parents=True, exist_ok=True)

    test_file = data_dir / "test_content.txt"
    test_file.write_text(
        """
        Containerization Best Practices:
        1. Use multi-stage builds to reduce image size
        2. Don't run containers as root user
        3. Use .dockerignore to exclude unnecessary files
        4. Leverage layer caching effectively
        5. Keep images minimal with only required dependencies
        6. Use specific version tags, not 'latest'
        7. Scan images for vulnerabilities
        """
    )

    content_id_3 = await knowledge_base.add_content(
        path=str(test_file),
        name="Containerization Best Practices",
        metadata={"category": "devops", "difficulty": "intermediate", "source": "file"},
    )
    content_ids.append(content_id_3)
    print("✅ Added: Containerization Best Practices (from file)")

    print(f"\n📊 Total content added: {len(content_ids)}")

    # Phase 2: Content Management
    print("\n\n📋 Phase 2: Content Management")
    print("-" * 60)

    # List all content
    all_contents = await knowledge_base.list_contents()
    print(f"Total content items: {len(all_contents)}")

    # Filter by category
    architecture_content = await knowledge_base.list_contents(filters={"category": "architecture"})
    print(f"Architecture content: {len(architecture_content)}")

    # Update metadata
    print("\n✏️  Updating metadata...")
    await knowledge_base.update_content_metadata(
        content_id_1,
        {"category": "architecture", "difficulty": "advanced", "reviewed": True, "version": "2.0"},
    )
    print("✅ Metadata updated")

    # Phase 3: Search Operations
    print("\n\n🔍 Phase 3: Search Operations")
    print("-" * 60)

    queries = [
        "What is microservices architecture?",
        "How does GraphQL compare to REST?",
        "What are containerization best practices?",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        results = await knowledge_base.search(query, limit=2, search_type=SearchType.VECTOR)

        if results:
            print(f"Found {len(results)} results:")
            for i, doc in enumerate(results, 1):
                print(f"  {i}. {doc.name}")
                print(f"     {doc.content[:100]}...")
                print(f"     Metadata: {doc.metadata}")
        else:
            print("  No results found")

    # Phase 4: Agent Integration
    print("\n\n🤖 Phase 4: Agent Integration")
    print("-" * 60)

    agent = Agent(
        name="TechExpert",
        instructions="""
        You are a technical expert assistant with access to a comprehensive knowledge base.
        When users ask questions:
        1. Use the search_knowledge tool to find relevant information
        2. Synthesize information from multiple sources if needed
        3. Provide clear, accurate answers with context
        4. Cite sources when possible
        """,
        model=Gemini("gemini-2.5-flash"),
        knowledge_base=knowledge_base,
    )

    agent_questions = [
        "What are the benefits of microservices?",
        "Should I use GraphQL or REST for my API?",
        "What are the key containerization best practices?",
    ]

    for question in agent_questions:
        print(f"\n❓ Question: {question}")
        response = await agent.invoke(question)
        print(f"💬 Response: {response[:300]}...")
        print()

    # Phase 5: Content Lifecycle
    print("\n\n🔄 Phase 5: Content Lifecycle")
    print("-" * 60)

    # Show content status
    contents = await knowledge_base.list_contents()
    print("Content Status Summary:")
    for content in contents:
        print(f"  - {content.name}: {content.status.value}")
        print(f"    Created: {content.created_at}")
        print(f"    Updated: {content.updated_at}")

    # Delete one content item
    print(f"\n🗑️  Deleting content: {content_ids[0]}")
    await knowledge_base.delete_content(content_ids[0])
    print("✅ Content deleted")

    # Verify deletion
    remaining = await knowledge_base.list_contents()
    print(f"Remaining content: {len(remaining)}")

    print("\n" + "=" * 60)
    print("✅ Comprehensive RAG workflow completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
