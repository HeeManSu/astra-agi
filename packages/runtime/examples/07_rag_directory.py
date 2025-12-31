"""RAG directory ingestion example - demonstrates ingesting entire directories."""

import asyncio
from pathlib import Path
import tempfile

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
    Example of ingesting entire directories into a RAG knowledge base.

    This is useful for:
    - Document collections
    - Code repositories
    - Knowledge bases
    - Documentation sites
    """

    print("=== RAG Directory Ingestion Example ===\n")

    # Create temporary directory with sample files
    with tempfile.TemporaryDirectory() as temp_dir:
        docs_dir = Path(temp_dir) / "docs"
        docs_dir.mkdir()

        # Create sample markdown files
        (docs_dir / "python.md").write_text(
            "# Python Programming\n\n"
            "Python is a versatile programming language used for web development, "
            "data science, machine learning, and automation."
        )

        (docs_dir / "javascript.md").write_text(
            "# JavaScript Programming\n\n"
            "JavaScript is a dynamic programming language primarily used for web development. "
            "It runs in browsers and on servers via Node.js."
        )

        (docs_dir / "rust.md").write_text(
            "# Rust Programming\n\n"
            "Rust is a systems programming language focused on safety and performance. "
            "It prevents memory errors through its ownership system."
        )

        print(f"Created sample documents in: {docs_dir}\n")

        # Setup RAG pipeline
        print("Setting up RAG pipeline...")
        embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
        vector_db = LanceDB(uri="./directory_rag_kb", embedder=embedder)

        context = RagContext(
            embedder=embedder,
            vector_db=vector_db,
            config={"default_top_k": 3},
        )

        ingest_pipeline = Pipeline(
            name="ingest",
            stages=[
                ReadStage(),
                ChunkStage(chunk_size=200, chunk_overlap=30),
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

        # Create agent with RAG
        print("Creating agent with RAG...")
        agent = Agent(
            model=Gemini("gemini-1.5-flash"),
            instructions="""You are a helpful programming language assistant.

Use the retrieve_evidence tool to find information about programming languages.
Provide accurate answers based on the retrieved documentation.""",
            name="lang-assistant",
            rag_pipeline=rag,
        )
        print("✓ Agent created\n")

        # Ingest entire directory
        print("Ingesting directory...")
        print(f"  Directory: {docs_dir}")
        print("  Pattern: *.md")
        print("  Recursive: False\n")

        content_ids = await agent.ingest_directory(
            directory=str(docs_dir),
            pattern="*.md",
            recursive=False,
        )

        print(f"✓ Ingested {len(content_ids)} files")
        print(f"  Content IDs: {content_ids}\n")

        # Query the knowledge base
        print("Querying knowledge base...")
        print("Question: What programming languages are documented?")
        response = await agent.invoke("What programming languages are documented?")
        print(f"Response: {response}\n")

        print("Question: Tell me about Rust")
        response = await agent.invoke("Tell me about Rust")
        print(f"Response: {response}\n")

    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
