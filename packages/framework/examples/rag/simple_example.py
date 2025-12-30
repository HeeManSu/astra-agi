"""Simple RAG Example

Demonstrates the RAG architecture:
- RagContext for shared dependencies
- Pipeline for stage composition
- Rag for user-facing API
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
    print("=== Simple RAG Example ===\n")

    # 1. Create shared context
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="./simple_rag_kb", embedder=embedder)

    context = RagContext(
        embedder=embedder,
        vector_db=vector_db,
        config=RagConfig(default_top_k=3),
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
        stages=[RetrieveStage(top_k=3)],
    )

    # 3. Create Rag
    rag = Rag(
        context=context,
        ingest_pipeline=ingest_pipeline,
        query_pipeline=query_pipeline,
    )

    # 4. Ingest documents
    print("Ingesting documents...")
    documents = [
        {
            "text": "The Eiffel Tower is located in Paris, France. It was built in 1889.",
            "name": "Eiffel Tower",
        },
        {"text": "The Great Wall of China is over 13,000 miles long.", "name": "Great Wall"},
        {
            "text": "The Statue of Liberty was a gift from France to the US in 1886.",
            "name": "Statue of Liberty",
        },
    ]

    ids = await rag.ingest_batch(documents)
    print(f"Ingested {len(ids)} documents\n")

    # 5. Query
    print("Querying...")
    queries = ["Where is the Eiffel Tower?", "How long is the Great Wall?"]

    for query in queries:
        results = await rag.query(query, top_k=1)
        if results:
            print(f"Q: {query}")
            print(f"A: {results[0].content[:80]}...\n")

    print("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
