"""Advanced RAG Example - Explicit Stage Configuration

Demonstrates all RAG stages with the new architecture.
"""

import asyncio

from framework.rag import (
    HuggingFaceEmbedder,
    LanceDB,
    Pipeline,
    Rag,
    RagConfig,
    RagContext,
)
from framework.rag.stages import (
    ChunkStage,
    EmbedStage,
    ReadStage,
    RetrieveStage,
    StoreStage,
)


async def main():
    print("=" * 60)
    print("Advanced RAG Example")
    print("=" * 60)

    # 1. Create shared context
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="./advanced_rag_kb", embedder=embedder)

    context = RagContext(
        embedder=embedder,
        vector_db=vector_db,
        config=RagConfig(default_top_k=5),
    )

    # 2. Create pipelines
    ingest_pipeline = Pipeline(
        name="ingest",
        stages=[
            ReadStage(),
            ChunkStage(chunk_size=300, chunk_overlap=50),
            EmbedStage(),
            StoreStage(),
        ],
    )

    query_pipeline = Pipeline(
        name="query",
        stages=[RetrieveStage(top_k=5)],
    )

    # 3. Create Rag
    rag = Rag(
        context=context,
        ingest_pipeline=ingest_pipeline,
        query_pipeline=query_pipeline,
    )

    # 4. Ingest
    documents = {
        "Machine Learning": "Machine learning is a subset of AI that learns from data.",
        "Deep Learning": "Deep learning uses neural networks with multiple layers.",
        "Neural Networks": "Neural networks are computing systems inspired by biological brains.",
    }

    print("\nIngesting...")
    for name, content in documents.items():
        await rag.ingest(text=content, name=name)
        print(f"  ✓ {name}")

    # 5. Query
    print("\nQuerying...")
    queries = ["What is machine learning?", "How do neural networks work?"]

    for query in queries:
        results = await rag.query(query, top_k=2)
        print(f"\nQ: {query}")
        for i, doc in enumerate(results, 1):
            print(f"  {i}. {doc.content[:50]}...")

    print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
