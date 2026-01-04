"""
Astra - AI Agents, Teams, and RAG in Pure Python

Entry point for all Astra functionality.
Currently exports embedded runtime (direct Python usage).
Future: Will also export server and client when implemented.

Usage:
    from astra import Agent, Tool, tool
    from astra.models import HuggingFaceLocal

    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are helpful"
    )

    response = await agent.invoke("Hello")
"""

# PHASE 1: Embedded Runtime exports (NOW)
# Re-export Embedded Runtime components for convenience
from astra.embedded import (
    DELEGATION_TOOL,
    Agent,
    AgentMemory,
    Bedrock,  # type: ignore[attr-defined]
    ChunkStage,
    ContentAction,
    DelegationError,
    Document,
    EmbedStage,
    Embedder,
    Gemini,
    HuggingFaceEmbedder,
    HuggingFaceLocal,
    InputContentFilter,
    InputGuardrail,
    InputGuardrailError,
    InputMiddleware,
    InputPIIFilter,
    LanceDB,
    LibSQLStorage,
    MemberNotFoundError,
    MemoryScope,
    MiddlewareContext,
    Model,
    ModelResponse,
    MongoDBStorage,
    OutputContentFilter,
    OutputGuardrail,
    OutputGuardrailError,
    OutputMiddleware,
    OutputPIIFilter,
    PIIAction,
    PersistentFacts,
    Pipeline,
    PromptInjectionFilter,
    Rag,
    RagContext,
    ReadStage,
    Reader,
    RecursiveChunking,
    RetrieveStage,
    SchemaGuardrail,
    SchemaValidationError,
    SecretAction,
    SecretLeakageFilter,
    StageState,
    StorageBackend,
    StoreStage,
    Team,
    TeamError,
    TeamExecutionContext,
    TeamMember,
    TeamTimeoutError,
    TextReader,
    Tool,
    VectorDB,
    get_model,
    tool,
)

# PHASE 2: Server exports
from astra.server import (
    AgentRegistry,
    AstraServer,
    ServerConfig,
    create_app,
)


# PHASE 3: Client SDK exports (FUTURE)
# from astra.client import AstraClient

__version__ = "0.1.0"

# Public API
__all__ = [
    # Agent & Tools
    "Agent",
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
    # RAG Components
    "Document",
    "Embedder",
    "HuggingFaceEmbedder",
    "LanceDB",
    "VectorDB",
    "Reader",
    "TextReader",
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
    # Server
    "create_app",
    "AstraServer",
    "ServerConfig",
    "AgentRegistry",
]
