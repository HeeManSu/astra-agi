"""Agent-centric RAG Example

Demonstrates the recommended pattern for production/API scenarios:
- Agent as the singleton with RAG capabilities
- Dynamic ingestion via agent methods
- Suitable for API endpoints where users upload files
"""

import asyncio

from framework.agents import Agent
from framework.models import Gemini
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
    print("=== Agent-Centric RAG Pattern ===\n")

    # 1. Setup RAG pipeline
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="./agent_rag_kb", embedder=embedder)

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
    print("Creating agent...")
    agent = Agent(
        name="Knowledge Assistant",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="""You are a helpful knowledge assistant.
        
When answering questions:
1. Use the retrieve_evidence tool to find relevant information
2. Provide accurate answers based on the retrieved context
3. Be concise and helpful
""",
        rag_pipeline=rag,
    )
    print("✓ Agent created\n")

    # 3. Ingest documents via agent (simulating API uploads)
    print("Ingesting documents via agent...")

    # Single document
    await agent.ingest(
        text="Python is a high-level programming language created by Guido van Rossum in 1991.",
        name="Python Overview",
    )
    print("  ✓ Ingested: Python Overview")

    # Batch ingest (like API file uploads)
    await agent.ingest_batch(
        [
            {
                "text": "JavaScript was created by Brendan Eich in 1995 for web browsers.",
                "name": "JavaScript Overview",
            },
            {
                "text": "Go is a statically typed language designed at Google in 2009.",
                "name": "Go Overview",
            },
        ]
    )
    print("  ✓ Ingested batch: JavaScript, Go\n")

    # 4. Query via agent
    print("Querying agent...\n")
    queries = [
        "Who created Python?",
        "When was JavaScript created?",
        "Tell me about Go",
    ]

    for query in queries:
        print(f"Q: {query}")
        response = await agent.invoke(query)
        print(f"A: {response}\n")

    print("=== Example Complete ===")
    print("\nThis pattern is ideal for:")
    print("  - API endpoints with file uploads")
    print("  - Long-running agent services")
    print("  - Single-object interface for all RAG ops")


if __name__ == "__main__":
    asyncio.run(main())
