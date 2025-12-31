"""Astra Embedded Runtime - Re-exports from framework.

This module provides the embedded runtime entry point for Astra.
Use this for direct Python integration (embedded mode).

All classes and functions are re-exported directly from the framework.

Example:
    from astra.embedded import Agent, Gemini, LibSQLStorage, Rag, RagContext

    # Create model
    model = Gemini("gemini-1.5-flash")

    # Create storage
    storage = LibSQLStorage(url="sqlite+aiosqlite:///./astra.db")
    await storage.connect()

    # Create RAG
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="./my_kb", embedder=embedder)
    context = RagContext(embedder=embedder, vector_db=vector_db, config={"default_top_k": 5})
    ingest_pipeline = Pipeline(name="ingest", stages=[ReadStage(), ChunkStage(), EmbedStage(), StoreStage()])
    query_pipeline = Pipeline(name="query", stages=[RetrieveStage(top_k=5)])
    rag = Rag(context=context, ingest_pipeline=ingest_pipeline, query_pipeline=query_pipeline)

    # Create agent
    agent = Agent(
        model=model,
        instructions="You are helpful",
        name="Assistant",
        storage=storage,
        rag_pipeline=rag,
    )
"""

# Tools - re-export from framework
from framework.agents import Tool, tool

# Guardrails - re-export from framework
from framework.guardrails import (
    ContentAction,
    InputContentFilter,
    InputGuardrail,
    InputGuardrailError,
    InputPIIFilter,
    OutputContentFilter,
    OutputGuardrail,
    OutputGuardrailError,
    OutputPIIFilter,
    PIIAction,
    PromptInjectionFilter,
    SchemaGuardrail,
    SchemaValidationError,
    SecretAction,
    SecretLeakageFilter,
)

# Memory - re-export from framework
from framework.memory import AgentMemory, MemoryScope, PersistentFacts

# Middlewares - re-export from framework
from framework.middlewares import InputMiddleware, MiddlewareContext, OutputMiddleware

# Models - re-export from framework
from framework.models import Gemini, Model, ModelResponse, get_model
from framework.models.aws.bedrock import Bedrock
from framework.models.huggingface import HuggingFaceLocal

# RAG - re-export from framework
from framework.rag import (
    Document,
    Embedder,
    HuggingFaceEmbedder,
    LanceDB,
    Pipeline,
    Rag,
    RagContext,
    Reader,
    RecursiveChunking,
    StageState,
    TextReader,
    VectorDB,
)
from framework.rag.stages import (
    ChunkStage,
    EmbedStage,
    ReadStage,
    RetrieveStage,
    StoreStage,
)

# Storage - re-export from framework
from framework.storage.base import StorageBackend
from framework.storage.databases.libsql import LibSQLStorage
from framework.storage.databases.mongodb import MongoDBStorage

# Teams - re-export from framework
from framework.team import (
    DELEGATION_TOOL,
    DelegationError,
    MemberNotFoundError,
    Team,
    TeamError,
    TeamExecutionContext,
    TeamMember,
    TeamTimeoutError,
)

# Agent - from embedded submodule
from astra.embedded.agent import Agent

__all__ = [
    # Agent
    "Agent",
    # Tools
    "Tool",
    "tool",
    # Models
    "Bedrock",
    "Gemini",
    "HuggingFaceLocal",
    "Model",
    "ModelResponse",
    "get_model",
    # Storage
    "StorageBackend",
    "LibSQLStorage",
    "MongoDBStorage",
    # RAG Core
    "Rag",
    "RagContext",
    "Pipeline",
    "StageState",
    # RAG Vector DB
    "LanceDB",
    "VectorDB",
    "Document",
    # RAG Embedders
    "HuggingFaceEmbedder",
    "Embedder",
    # RAG Readers
    "TextReader",
    "Reader",
    # RAG Chunking
    "RecursiveChunking",
    # RAG Stages
    "ReadStage",
    "ChunkStage",
    "EmbedStage",
    "StoreStage",
    "RetrieveStage",
    # Memory
    "AgentMemory",
    "MemoryScope",
    "PersistentFacts",
    # Middlewares
    "InputMiddleware",
    "OutputMiddleware",
    "MiddlewareContext",
    # Guardrails - Base
    "InputGuardrail",
    "OutputGuardrail",
    "SchemaGuardrail",
    # Guardrails - Content
    "InputContentFilter",
    "OutputContentFilter",
    "ContentAction",
    # Guardrails - PII
    "InputPIIFilter",
    "OutputPIIFilter",
    "PIIAction",
    # Guardrails - Secrets
    "SecretLeakageFilter",
    "SecretAction",
    # Guardrails - Injection
    "PromptInjectionFilter",
    # Guardrails - Exceptions
    "InputGuardrailError",
    "OutputGuardrailError",
    "SchemaValidationError",
    # Teams
    "Team",
    "TeamMember",
    "TeamExecutionContext",
    "DELEGATION_TOOL",
    "TeamError",
    "DelegationError",
    "MemberNotFoundError",
    "TeamTimeoutError",
]
