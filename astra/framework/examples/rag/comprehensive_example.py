"""Comprehensive RAG Example - All Stages

This example demonstrates all RAG pipeline stages with the new architecture:
- RagContext for shared dependencies
- Pipeline for stage composition
- Rag for user-facing API
- Integration with Agent

A simple knowledge base about programming languages.
"""

import asyncio

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
    print("=== Comprehensive RAG Pipeline Example ===\n")

    # 1. Create shared context
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="./programming_kb", embedder=embedder)

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
            ChunkStage(strategy="recursive", chunk_size=300, chunk_overlap=30),
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

    # 4. Prepare documents
    documents = {
        "Python Overview": """Python is a high-level, interpreted programming language created by Guido van Rossum in 1991.
        It emphasizes code readability with significant whitespace. Python supports multiple programming paradigms including
        procedural, object-oriented, and functional programming. It has a comprehensive standard library and is widely used
        for web development, data science, artificial intelligence, and automation.""",
        "JavaScript Overview": """JavaScript is a high-level, interpreted programming language that conforms to the ECMAScript
        specification. Created by Brendan Eich in 1995, it was initially designed to make web pages interactive. JavaScript
        is a prototype-based, multi-paradigm language supporting event-driven, functional, and imperative programming styles.
        It runs in web browsers and on servers via Node.js.""",
        "Go Overview": """Go, also known as Golang, is a statically typed, compiled programming language designed at Google
        by Robert Griesemer, Rob Pike, and Ken Thompson in 2009. Go is syntactically similar to C but with memory safety,
        garbage collection, structural typing, and CSP-style concurrency. It's designed for building simple, reliable, and
        efficient software, particularly for networked and multicore machines.""",
    }

    # Stage 1: Ingest
    print("Stage 1: Reading & Ingesting Content")
    print("-" * 50)
    for name, content in documents.items():
        try:
            content_id = await rag.ingest(
                text=content,
                name=name,
                metadata={"category": "programming_language"},
            )
            print(f"  Ingested: {name} (ID: {content_id[:8]}...)")
        except Exception as e:
            print(f"  Failed to ingest {name}: {e}")

    # Stage 2: Query
    print("\nStage 2: Querying Knowledge Base")
    print("-" * 50)
    queries = [
        "Who created Python?",
        "What year was JavaScript created?",
        "What is Go used for?",
    ]

    for query in queries:
        try:
            results = await rag.query(query, top_k=2)
            print(f"\nQuery: {query}")
            print(f"Found {len(results)} results:")
            for i, doc in enumerate(results, 1):
                preview = doc.content[:100].replace("\n", " ")
                print(f"  {i}. {preview}...")
        except Exception as e:
            print(f"  Query failed: {e}")

    # Stage 3: Agent integration
    print("\n" + "=" * 50)
    print("Stage 3: Agent with RAG")
    print("=" * 50)

    agent = Agent(
        name="Programming Expert",
        model=Gemini("gemini-2.0-flash-exp"),
        instructions="""You are a programming language expert assistant.

When asked about programming languages:
1. Use the retrieve_evidence tool to find relevant information
2. Provide accurate, concise answers based on the retrieved context
3. If information is not in the knowledge base, state that clearly

Keep answers brief and to the point.""",
        rag_pipeline=rag,
    )

    agent_queries = [
        "Tell me about Python",
        "When was JavaScript created and by whom?",
        "What makes Go different from other languages?",
    ]

    for query in agent_queries:
        print(f"\nUser: {query}")
        print("-" * 50)
        try:
            response = await agent.invoke(query)
            print(f"Agent: {response}")
        except Exception as e:
            print(f"Error: {e}")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
