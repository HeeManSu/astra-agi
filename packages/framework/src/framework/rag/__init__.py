"""RAG module.

Example:
    from framework.rag import (
        Rag, RagContext, RagConfig, Pipeline,
        LanceDB, HuggingFaceEmbedder
    )
    from framework.rag.stages import (
        ReadStage, ChunkStage, EmbedStage, StoreStage, RetrieveStage
    )

    # 1. Create shared context
    context = RagContext(
        embedder=HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2"),
        vector_db=LanceDB(uri="./my_kb"),
        config=RagConfig(default_top_k=5),
    )

    # 2. Create pipelines
    ingest_pipeline = Pipeline(
        name="ingest",
        stages=[ReadStage(), ChunkStage(...), EmbedStage(), StoreStage()],
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

    # 4. Use it
    await rag.ingest(text="Python is a programming language...")
    results = await rag.query("What is Python?")
"""

from framework.rag.chunking import ChunkingStrategy, RecursiveChunking
from framework.rag.context import RagContext, StageState
from framework.rag.embedders import Embedder, HuggingFaceEmbedder
from framework.rag.pipeline import Pipeline, Rag
from framework.rag.readers import Reader, TextReader
from framework.rag.vectordb import Document, LanceDB, VectorDB


__all__ = [
    # Core
    "Rag",
    "RagContext",
    "Pipeline",
    "StageState",
    # Vector DB
    "LanceDB",
    "VectorDB",
    "Document",
    # Embedders
    "HuggingFaceEmbedder",
    "Embedder",
    # Readers
    "TextReader",
    "Reader",
    # Chunking
    "RecursiveChunking",
    "ChunkingStrategy",
]
