"""
Example 5: Content Lifecycle Management
Demonstrates content CRUD operations: create, read, update, delete.
"""

import asyncio

from framework.KnowledgeBase import HuggingFaceEmbedder, KnowledgeBase, LanceDB


async def main():
    """Content management example."""

    print("=" * 60)
    print("Example 5: Content Lifecycle Management")
    print("=" * 60)

    # Setup knowledge base (using HuggingFace - no API key needed)
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="examples/rag/data/lancedb_management", embedder=embedder)

    knowledge_base = KnowledgeBase(
        vector_db=vector_db,
        embedder=embedder,
    )

    print("\n📚 Step 1: Adding initial content...")

    # Add content
    content_id = await knowledge_base.add_content(
        text="""
        PostgreSQL is a powerful open-source relational database management system.
        It supports SQL and provides advanced features like transactions, foreign keys,
        and stored procedures. PostgreSQL is known for its reliability and data integrity.
        """,
        name="PostgreSQL Basics",
        metadata={"topic": "database", "type": "rdbms", "version": "1.0"},
    )
    print(f"✅ Created content: {content_id}")

    # 2. List all content
    print("\n📋 Step 2: Listing all content...")
    contents = await knowledge_base.list_contents()
    print(f"Total content: {len(contents)}")

    for content in contents:
        print(f"  - {content.name}")
        print(f"    Status: {content.status.value}")
        print(f"    Created: {content.created_at}")
        print(f"    Metadata: {content.metadata}")

    # 3. Get specific content
    print("\n🔍 Step 3: Getting content by ID...")
    content = await knowledge_base.contents_db.get_content(content_id)
    if content:
        print(f"  Found: {content.name}")
        print(f"  Status: {content.status.value}")
        print(f"  Source: {content.source}")

    # 4. Update metadata
    print("\n✏️  Step 4: Updating content metadata...")
    await knowledge_base.update_content_metadata(
        content_id,
        {"version": "2.0", "updated_by": "admin", "topic": "database"},
    )
    print("✅ Metadata updated")

    # Verify update
    updated_content = await knowledge_base.contents_db.get_content(content_id)
    if updated_content:
        print(f"  New metadata: {updated_content.metadata}")

    # 5. Filter content by status
    print("\n🔎 Step 5: Filtering content by status...")
    completed = await knowledge_base.list_contents(filters={"status": "completed"})
    print(f"  Completed content: {len(completed)}")

    # 6. Delete content
    print("\n🗑️  Step 6: Deleting content...")
    await knowledge_base.delete_content(content_id)
    print(f"✅ Deleted content: {content_id}")

    # Verify deletion
    remaining = await knowledge_base.list_contents()
    print(f"  Remaining content: {len(remaining)}")


if __name__ == "__main__":
    asyncio.run(main())
