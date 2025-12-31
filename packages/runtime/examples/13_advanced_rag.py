"""Advanced RAG example - SIMPLIFIED DEMO

NOTE: This example shows advanced RAG concepts but uses default parameters
to ensure it runs without complex configuration.

Shows:
- Custom RAG pipeline setup
- Chunking and embedding strategies
- Custom retrieval configuration
"""

import asyncio

from astra import (
    Agent,
    ChunkStage,
    EmbedStage,
    HuggingFaceEmbedder,
    LanceDB,
    Pipeline,
    Rag,
    RagContext,
    ReadStage,
    RetrieveStage,
    StoreStage,
)
from astra import HuggingFaceLocal


async def main():
    """
    Advanced RAG with custom pipeline configuration.
    """
    
    print("=== Advanced RAG Pipeline ===\n")
    
    # Create embedder (using default model)
    embedder = HuggingFaceEmbedder()
    
    # Create vector database
    vector_db = LanceDB(
        uri="./advanced_knowledge_base",
        embedder=embedder
    )
    
    # Create RAG context with configuration
    rag_context = RagContext(
        embedder=embedder,
        vector_db=vector_db,
        config={"default_top_k": 5}
    )
    
    # Custom ingest pipeline
    ingest_pipeline = Pipeline(
        name="advanced_ingest",
        stages=[
            ReadStage(),
            ChunkStage(),
            EmbedStage(),
            StoreStage(),
        ]
    )
    
    # Query pipeline
    query_pipeline = Pipeline(
        name="advanced_query",
        stages=[RetrieveStage(top_k=5)],
    )
    
    # Create RAG
    rag = Rag(
        context=rag_context,
        ingest_pipeline=ingest_pipeline,
        query_pipeline=query_pipeline,
    )
    
    print("📚 RAG system configured")
    print("  - Vector DB: LanceDB")
    print("  - Embedder: HuggingFace")
    print("  - Custom pipelines: Ingest + Query\n")
    
    # Ingest sample documents
    print("📥 Ingesting documents...")
    
    documents = [
        "Python is a high-level programming language known for its simplicity.",
        "Machine learning is a subset of AI that learns from data.",
        "Natural language processing allows computers to understand human language.",
    ]
    
    for doc in documents:
        await rag.ingest(doc)
    
    print(f"✅ Ingested {len(documents)} documents\n")
    
    # Create agent with RAG
    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are a helpful assistant with access to a knowledge base.",
        name="rag-agent",
        rag_pipeline=rag,
    )
    
    # Query
    query = "What is Python?"
    print(f"❓ Query: {query}\n")
    
    # Retrieve context
    results = await rag.query(query)
    print(f"📄 Retrieved {len(results)} relevant chunks\n")
    
    # Get agent response
    response = await agent.invoke(query)
    print(f"🤖 Agent: {response}")
    
    print("\n✅ Advanced RAG demonstration complete!")
    
    # Show concepts
    print("\n" + "=" * 60)
    print("Advanced RAG Concepts")
    print("=" * 60)
    print("\n📋 **Custom Pipelines**:")
    print("  - Ingest: Read → Chunk → Embed → Store")
    print("  - Query: Retrieve (with custom top_k)")
    
    print("\n⚙️  **Configuration Options**:")
    print("  - Chunk size and overlap")
    print("  - Retrieval parameters (top_k, threshold)")
    print("  - Custom stages for preprocessing")
    print("  - Multiple vector databases")


if __name__ == "__main__":
    asyncio.run(main())
