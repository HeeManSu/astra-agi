"""
Example 4: Multiple Content Types
Demonstrates adding different types of content (text, files, URLs).
"""

import asyncio
from pathlib import Path

from framework.KnowledgeBase import HuggingFaceEmbedder, KnowledgeBase, LanceDB, RecursiveChunking


async def main():
    """Multiple content types example."""

    print("=" * 60)
    print("Example 4: Multiple Content Types")
    print("=" * 60)

    # Setup knowledge base (using HuggingFace - no API key needed)
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="examples/rag/data/lancedb_multiple", embedder=embedder)

    knowledge_base = KnowledgeBase(
        vector_db=vector_db,
        embedder=embedder,
        chunking=RecursiveChunking(chunk_size=400),
    )

    print("\n📚 Adding different content types...\n")

    # 1. Add text content
    print("1️⃣ Adding text content...")
    text_id = await knowledge_base.add_content(
        text="""
        Docker is a platform for developing, shipping, and running applications in containers.
        Containers package an application with all its dependencies, ensuring it runs consistently
        across different environments. Docker uses images to create containers, and Dockerfiles
        to define image configurations.
        """,
        name="Docker Introduction",
        metadata={"type": "text", "topic": "devops"},
    )
    print(f"   ✅ Added text content: {text_id}")

    # 2. Add file content (if file exists)
    print("\n2️⃣ Adding file content...")
    test_file = Path("examples/rag/data/test_document.txt")
    test_file.parent.mkdir(parents=True, exist_ok=True)

    # Create a test file
    test_file.write_text(
        """
        Kubernetes is an open-source container orchestration platform. It automates the
        deployment, scaling, and management of containerized applications. Key concepts
        include pods, services, deployments, and namespaces. Kubernetes helps manage
        complex distributed systems at scale.
        """
    )

    if test_file.exists():
        file_id = await knowledge_base.add_content(
            path=str(test_file),
            name="Kubernetes Guide",
            metadata={"type": "file", "topic": "devops", "format": "txt"},
        )
        print(f"   ✅ Added file content: {file_id}")
    else:
        print("   ⚠️  Test file not found, skipping file content")

    # 3. List all content
    print("\n3️⃣ Listing all content...")
    contents = await knowledge_base.list_contents()
    print(f"   Total content items: {len(contents)}")

    for content in contents:
        print(f"   - {content.name} ({content.status.value})")
        print(f"     Source: {content.source}")
        print(f"     Metadata: {content.metadata}")

    # 4. Search across all content types
    print("\n🔍 Searching across all content types...")
    query = "container orchestration"
    results = await knowledge_base.search(query, limit=3)

    print(f"\nQuery: {query}")
    print(f"Found {len(results)} results:\n")

    for i, doc in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  Source: {doc.name}")
        print(f"  Content: {doc.content[:120]}...")
        print(f"  Metadata: {doc.metadata}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
