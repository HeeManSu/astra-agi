"""Customer Support Agent with RAG

A real-world example demonstrating how to build a customer support agent
that uses RAG to answer questions from product documentation.

This example shows:
- Creating RagContext with shared dependencies
- Building ingest and query Pipelines
- Ingesting product documentation into a knowledge base
- Creating an agent that retrieves relevant information
- Answering customer questions with accurate, grounded responses
"""

import asyncio
from pathlib import Path

from framework.agents import Agent
from framework.models import Gemini
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
    # 1. Create shared context
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="./customer_support_kb", embedder=embedder)

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
            ChunkStage(strategy="recursive", chunk_size=500, chunk_overlap=50),
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

    # 4. Ingest product documentation
    docs_path = Path(__file__).parent / "product_docs.txt"

    print("Ingesting product documentation...")
    try:
        content_id = await rag.ingest(
            path=docs_path,
            name="TechCorp Cloud Storage Documentation",
            metadata={"category": "product_docs", "version": "1.0"},
        )
        print(f"Successfully ingested documentation (ID: {content_id})")
    except Exception as e:
        print(f"Error during ingestion: {e}")
        return

    # 5. Create agent with RAG
    agent = Agent(
        name="TechCorp Support Agent",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="""You are a helpful customer support agent for TechCorp Cloud Storage.

Your role is to assist customers with questions about our product, pricing, troubleshooting, and policies.

When answering questions:
1. Use the retrieve_evidence tool to search the knowledge base for relevant information
2. Provide accurate answers based on the retrieved documentation
3. Be friendly, professional, and concise
4. If a question is outside your knowledge base, politely suggest contacting human support

Always cite the source of your information when providing answers.""",
        rag_pipeline=rag,
    )

    # 6. Run customer queries
    queries = [
        "What are the pricing plans available?",
        "My files are not syncing. What should I do?",
        "What is the refund policy?",
        "How much storage do I get with the Professional plan?",
        "Is my data encrypted?",
    ]

    print("\nCustomer Support Session:")
    print("=" * 80)

    for query in queries:
        print(f"\nCustomer: {query}")
        print("-" * 80)

        try:
            response = await agent.invoke(query)
            print(f"Agent: {response}")
        except Exception as e:
            print(f"Error: {e}")

        print()


if __name__ == "__main__":
    asyncio.run(main())
