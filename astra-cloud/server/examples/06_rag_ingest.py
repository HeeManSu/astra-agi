"""RAG ingestion example - demonstrates RAG knowledge base ingestion."""

import asyncio

from astra import Agent
from framework.models.google.gemini import Gemini
from framework.rag import (
    HuggingFaceEmbedder,
    LanceDB,
    Pipeline,
    Rag,
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
    """
    Example of using RAG (Retrieval-Augmented Generation) with an agent.

    This demonstrates:
    - Setting up a RAG pipeline
    - Ingesting documents via agent.ingest()
    - Ingesting multiple documents via agent.ingest_batch()
    - Querying the knowledge base through the agent
    """

    print("=== RAG Ingestion Example ===\n")

    # 1. Setup RAG pipeline
    print("Setting up RAG pipeline...")
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="./rag_kb", embedder=embedder)

    context = RagContext(
        embedder=embedder,
        vector_db=vector_db,
        config={"default_top_k": 3},
    )

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

    rag = Rag(
        context=context,
        ingest_pipeline=ingest_pipeline,
        query_pipeline=query_pipeline,
    )

    # 2. Create agent with RAG
    print("Creating agent with RAG...")
    agent = Agent(
        model=Gemini("gemini-1.5-flash"),
        instructions="""You are a helpful knowledge assistant.

When answering questions:
1. Use the retrieve_evidence tool to find relevant information
2. Provide accurate answers based on the retrieved context
3. Be concise and helpful
""",
        name="knowledge-assistant",
        rag_pipeline=rag,
    )
    print("✓ Agent created\n")

    # 3. Ingest documents via agent
    print("Ingesting documents...")

    # Single document ingestion
    print("  - Ingesting single document (text)")
    content_id = await agent.ingest(
        text="Python is a high-level programming language known for its simplicity and readability. "
        "It supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
        name="Python Introduction",
    )
    print(f"    Content ID: {content_id}")

    # Batch ingestion
    print("  - Ingesting batch documents")
    content_ids = await agent.ingest_batch(
        [
            {
                "text": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
                "name": "ML Introduction",
            },
            {
                "text": "Async/await in Python allows for concurrent execution of code using coroutines.",
                "name": "Python Async",
            },
        ]
    )
    print(f"    Content IDs: {content_ids}")

    print("\n✓ Documents ingested\n")

    # 4. Query the knowledge base
    print("Querying knowledge base...")
    print("Question: What is Python?")
    response = await agent.invoke("What is Python?")
    print(f"Response: {response}\n")

    print("Question: What is machine learning?")
    response = await agent.invoke("What is machine learning?")
    print(f"Response: {response}\n")

    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
