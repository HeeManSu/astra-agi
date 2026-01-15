"""
Shared test fixtures using REAL framework objects.

All tests use actual Astra framework components:
- Real Agent with HuggingFaceLocal model
- Real LibSQL storage
- No mocks - true integration testing

Models:
- small_model: SmolLM-135M-Instruct (270MB) - fast, instruction-tuned
- large_model: Qwen2.5-0.5B-Instruct (1GB) - robust, for complex inputs
"""

import asyncio
from pathlib import Path
import tempfile
from typing import ClassVar

import pytest


# ============================================================================
# Real Framework Object Fixtures
# ============================================================================


@pytest.fixture
async def real_storage():
    """Create real AgentStorage with temporary LibSQL database."""
    from framework.storage.databases.libsql import LibSQLStorage
    from framework.storage.memory import AgentStorage

    # Create temp file for database
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_path = temp_file.name
    temp_file.close()

    # Create LibSQL storage with file backend
    storage_backend = LibSQLStorage(url=f"sqlite+aiosqlite:///{temp_path}")
    await storage_backend.connect()
    await storage_backend.create_tables()

    # Wrap in AgentStorage
    agent_storage = AgentStorage(storage=storage_backend)

    yield agent_storage

    # Cleanup
    await agent_storage.stop()
    await storage_backend.disconnect()
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def small_model():
    """
    Create small HuggingFaceLocal model (SmolLM-135M-Instruct - 270MB).

    Fast, lightweight, and supports chat templates (unlike distilgpt2).
    """
    from framework.models.huggingface import HuggingFaceLocal

    return HuggingFaceLocal(
        model_id="HuggingFaceTB/SmolLM-135M-Instruct",
        max_new_tokens=50,
        temperature=0.7,
    )


@pytest.fixture
def large_model():
    """
    Create larger HuggingFaceLocal model (Qwen2.5-0.5B-Instruct - 1GB).

    Robust instruction-tuned model for edge cases and complex inputs.
    """
    from framework.models.huggingface import HuggingFaceLocal

    return HuggingFaceLocal(
        model_id="Qwen/Qwen2.5-0.5B-Instruct",
        max_new_tokens=100,
        temperature=0.7,
    )


@pytest.fixture
async def real_agent(small_model):
    """Create real Agent with small model (for most tests)."""
    from framework.agents import Agent

    return Agent(
        name="test-agent",
        model=small_model,
        instructions="You are a helpful test assistant.",
        description="A test agent for integration testing",
    )


@pytest.fixture
async def real_agent_large(large_model):
    """Create real Agent with large model (for edge case tests)."""
    from framework.agents import Agent

    return Agent(
        name="test-agent-large",
        model=large_model,
        instructions="You are a helpful test assistant.",
        description="A robust test agent for edge cases",
    )


@pytest.fixture
async def real_agent_with_storage(small_model, real_storage):
    """Create real Agent with storage."""
    from framework.agents import Agent

    return Agent(
        name="test-agent-storage",
        model=small_model,
        instructions="You are a helpful test assistant with memory.",
        description="A test agent with storage",
        storage=real_storage,
    )


# ============================================================================
# Test Helper Classes (for error/edge case testing only)
# ============================================================================


class FailingAgent:
    """Agent that raises exceptions (for error testing only)."""

    name: ClassVar[str] = "failing-agent"
    description: ClassVar[str] = "An agent that fails"
    storage: ClassVar[None] = None
    rag_pipeline: ClassVar[None] = None
    tools: ClassVar[list] = []

    async def invoke(self, message: str, **kwargs) -> str:
        raise RuntimeError("Agent invoke failed!")

    async def stream(self, message: str, **kwargs):
        # Proper async generator that raises during iteration
        raise RuntimeError("Agent stream failed!")
        # This yield is unreachable but makes Python treat this as an async generator
        yield  # type: ignore


class EmptyResponseAgent:
    """Agent that returns empty responses (for edge case testing)."""

    name: ClassVar[str] = "empty-agent"
    description: ClassVar[str] = "Returns empty"
    storage: ClassVar[None] = None
    rag_pipeline: ClassVar[None] = None
    tools: ClassVar[list] = []

    async def invoke(self, message: str, **kwargs) -> str:
        return ""

    async def stream(self, message: str, **kwargs):
        yield ""


class FailingStorage:
    """Storage that fails on connect (for error testing)."""

    def __init__(self):
        self.storage_id = "failing-storage"
        self.connected = False
        self.tables_created = False

    async def connect(self):
        raise ConnectionError("Failed to connect to database")

    async def disconnect(self):
        pass

    async def create_tables(self):
        pass


class FailingMCPServer:
    """MCP server that fails to connect (for error testing)."""

    def __init__(self, name: str = "failing-mcp"):
        self.name = name
        self.connected = False

    async def connect(self):
        raise ConnectionError("Failed to connect to MCP server")

    async def start(self):
        raise ConnectionError("Failed to start MCP server")

    async def close(self):
        pass

    async def stop(self):
        pass


# ============================================================================
# Helper Functions (create real objects on-demand)
# ============================================================================


def create_agent(
    name: str = "test-agent",
    description: str | None = None,
    storage=None,
    rag_pipeline=None,
    tools=None,
    use_large_model: bool = False,
):
    """
    Create an agent instance with real HuggingFace model.

    By default uses SmolLM-135M for speed. Set use_large_model=True for
    tests requiring robust handling of complex inputs (uses Qwen2.5-0.5B).

    Args:
        name: Agent identifier
        description: Agent description text
        storage: Storage backend instance
        rag_pipeline: RAG pipeline instance
        tools: List of available tools
        use_large_model: Use Qwen2.5-0.5B instead of SmolLM for better accuracy

    Returns:
        Fully configured Agent instance
    """
    from framework.agents import Agent
    from framework.models.huggingface import HuggingFaceLocal

    model_id = (
        "Qwen/Qwen2.5-0.5B-Instruct" if use_large_model else "HuggingFaceTB/SmolLM-135M-Instruct"
    )
    max_new_tokens = 100 if use_large_model else 50
    model = HuggingFaceLocal(
        model_id=model_id,
        max_new_tokens=max_new_tokens,
        temperature=0.7,
    )

    return Agent(
        name=name,
        model=model,
        instructions="You are a helpful test assistant.",
        description=description or "A test agent",
        storage=storage,
        rag_pipeline=rag_pipeline,
        tools=tools or [],
    )


def create_storage(storage_id: str = "test-storage"):
    """
    Create a REAL AgentStorage with in-memory LibSQL.

    WARNING: Must be used in async context. The storage backend
    needs await connect() and create_tables() before use.
    """
    from framework.storage.databases.libsql import LibSQLStorage
    from framework.storage.memory import AgentStorage

    # In-memory database
    storage_backend = LibSQLStorage(url="sqlite+aiosqlite:///:memory:")

    # Check if we're in an async context
    try:
        loop = asyncio.get_running_loop()
        # We're in async context, return uninitialized (test will await connect)
        return AgentStorage(storage=storage_backend)
    except RuntimeError:
        # Not in async context, initialize synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(storage_backend.connect())
        loop.run_until_complete(storage_backend.create_tables())
        return AgentStorage(storage=storage_backend)


def create_rag_pipeline(name: str = "test-rag"):
    """
    Create a minimal RAG pipeline stub (for testing RAG presence).

    Note: Full RAG requires embeddings, this is a simplified stub.
    """

    class SimpleRagPipeline:
        def __init__(self, pipeline_name: str):
            self.name = pipeline_name

        async def ingest(self, content: str, **kwargs) -> str:
            """Stub ingest that returns content ID."""
            return "content-id-123"

        async def query(self, query: str, **kwargs) -> list[dict]:
            """Stub query that returns empty results."""
            return []

    return SimpleRagPipeline(name)


def create_model(name: str = "test-model", use_large: bool = False):
    """
    Create a HuggingFace model instance for testing.

    Args:
        name: Model name (reserved for future use)
        use_large: Whether to use gpt2 instead of distilgpt2

    Returns:
        Configured HuggingFaceLocal model
    """
    from framework.models.huggingface import HuggingFaceLocal

    model_id = "Qwen/Qwen2.5-0.5B-Instruct" if use_large else "HuggingFaceTB/SmolLM-135M-Instruct"
    max_new_tokens = 100 if use_large else 50

    return HuggingFaceLocal(
        model_id=model_id,
        max_new_tokens=max_new_tokens,
        temperature=0.7,
    )


def create_streaming_agent(
    name: str = "streaming-agent",
    description: str | None = None,
    storage=None,
):
    """
    Create an Agent with Gemini model for streaming tests.

    Gemini's async streaming works properly with AsyncClient,
    unlike HuggingFaceLocal which uses blocking thread-based streaming.

    Requires GOOGLE_API_KEY or GEMINI_API_KEY environment variable.

    Args:
        name: Agent name
        description: Agent description
        storage: Optional storage backend

    Returns:
        Fully configured Agent with Gemini model
    """
    from framework.agents import Agent
    from framework.models.google.gemini import Gemini

    model = Gemini(
        model_id="gemini-2.0-flash-exp",
        max_tokens=100,
        temperature=0.7,
    )

    return Agent(
        name=name,
        model=model,
        instructions="You are a helpful test assistant. Keep responses brief.",
        description=description or "A streaming test agent",
        storage=storage,
    )


def create_streaming_agent_with_tools(
    name: str = "streaming-agent-tools",
    description: str | None = None,
    storage=None,
):
    """
    Create an Agent with Gemini model AND tools for streaming tests.

    Tests the tool execution loop within Agent.stream().

    Args:
        name: Agent name
        description: Agent description
        storage: Optional storage backend

    Returns:
        Agent with Gemini model and a simple tool
    """
    from framework.agents import Agent
    from framework.agents.tool import Tool
    from framework.models.google.gemini import Gemini

    # Simple tool that returns current time
    def get_current_time() -> str:
        """Get the current time."""
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")

    model = Gemini(
        model_id="gemini-2.0-flash-exp",
        max_tokens=100,
        temperature=0.7,
    )

    return Agent(
        name=name,
        model=model,
        instructions="You are a helpful test assistant with tools. Keep responses brief.",
        description=description or "A streaming test agent with tools",
        storage=storage,
        tools=[
            Tool(
                name="get_current_time",
                description="Get the current time",
                func=get_current_time,
            )
        ],
    )


def create_streaming_agent_with_rag(
    name: str = "streaming-agent-rag",
    description: str | None = None,
    storage=None,
):
    """
    Create an Agent with Gemini model AND RAG pipeline for streaming tests.

    Tests RAG integration within Agent.stream().

    Args:
        name: Agent name
        description: Agent description
        storage: Optional storage backend

    Returns:
        Agent with Gemini model and RAG pipeline
    """
    from framework.agents import Agent
    from framework.models.google.gemini import Gemini

    model = Gemini(
        model_id="gemini-2.0-flash-exp",
        max_tokens=100,
        temperature=0.7,
    )

    rag = create_rag_pipeline(f"{name}-rag")

    return Agent(
        name=name,
        model=model,
        instructions="You are a helpful test assistant with RAG. Keep responses brief.",
        description=description or "A streaming test agent with RAG",
        storage=storage,
        rag_pipeline=rag,
    )


class SimpleMCPServer:
    """Minimal MCP server stub for testing (not a real MCPServer)."""

    def __init__(self, name: str = "test-mcp"):
        self.name = name
        self.connected = False

    async def start(self):
        """Start server."""
        self.connected = True

    async def stop(self):
        """Stop server."""
        self.connected = False

    async def connect(self):
        """Connect (compat)."""
        self.connected = True

    async def close(self):
        """Close (compat)."""
        self.connected = False

    async def get_tools(self) -> list:
        """Get tools."""
        return []


# ============================================================================
# Pytest Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
