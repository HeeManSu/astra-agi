"""
Pytest configuration and shared fixtures for Astra framework tests.

This module provides reusable fixtures for:
- Flexible HuggingFace model configuration
- Temporary storage (SQLite)
- Agent factories
- Common tools for testing
"""

from collections.abc import Callable
import os
import tempfile
from typing import Any
import uuid

from framework.agents import Agent, tool
from framework.models.huggingface import HuggingFaceLocal, HuggingFaceRemote
from framework.storage.databases.libsql import LibSQLStorage
from framework.storage.memory import AgentStorage
import pytest


# Model Configuration

# Remote Model Server Configuration
# Set this to your laptop's IP address where the remote model server is running
REMOTE_MODEL_URL = os.environ.get("ASTRA_REMOTE_MODEL_URL", "http://localhost:8001")
DEFAULT_MAX_NEW_TOKENS = int(os.environ.get("ASTRA_TEST_MAX_TOKENS", "512"))

# Use remote model by default (7B parameter model with tool calling support)
USE_REMOTE_MODEL = os.environ.get("ASTRA_USE_REMOTE_MODEL", "true").lower() == "true"

# Fallback local model for offline testing
DEFAULT_MODEL_ID = os.environ.get("ASTRA_TEST_MODEL_ID", "HuggingFaceTB/SmolLM2-1.7B-Instruct")


# Alternative models for different test scenarios
AVAILABLE_MODELS = {
    "small": "HuggingFaceTB/SmolLM2-360M-Instruct",  # Fast, small (no tool calling)
    "medium": "HuggingFaceTB/SmolLM2-1.7B-Instruct",  # Tool calling support (~1GB)
    "large": "meta-llama/Llama-3.2-3B-Instruct",  # Better tool calling (~3GB)
    "code": "bigcode/starcoder2-3b",  # Code-focused
}


@pytest.fixture(scope="session")
def hf_model():
    """
    Provides a shared HuggingFace model instance.

    By default, uses HuggingFaceRemote pointing to a remote model server
    running a 7B parameter model with full tool calling support.

    Scope is 'session' to reuse the connection for all tests.

    Configure via environment variables:
    - ASTRA_REMOTE_MODEL_URL: Remote server URL (default: http://localhost:8001)
    - ASTRA_USE_REMOTE_MODEL: Use remote model (default: true)
    - ASTRA_TEST_MODEL_ID: Fallback local model ID
    - ASTRA_TEST_MAX_TOKENS: Max tokens (default: 512)

    To use local model instead:
        ASTRA_USE_REMOTE_MODEL=false pytest ...
    """
    if USE_REMOTE_MODEL:
        print(f"\n🌐 Using remote model server: {REMOTE_MODEL_URL}")
        return HuggingFaceRemote(base_url=REMOTE_MODEL_URL)
    else:
        print(f"\n💻 Using local model: {DEFAULT_MODEL_ID}")
        return HuggingFaceLocal(DEFAULT_MODEL_ID, max_new_tokens=DEFAULT_MAX_NEW_TOKENS)


@pytest.fixture
def make_hf_model():
    """
    Factory fixture to create HuggingFace models with custom settings.

    Usage:
        def test_with_custom_model(make_hf_model):
            model = make_hf_model("microsoft/Phi-3-mini-4k-instruct", max_new_tokens=200)
    """

    def _make_model(
        model_id: str | None = None,
        max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
        **kwargs: Any,
    ) -> HuggingFaceLocal:
        # Support aliases
        if model_id in AVAILABLE_MODELS:
            model_id = AVAILABLE_MODELS[model_id]
        return HuggingFaceLocal(
            model_id or DEFAULT_MODEL_ID,
            max_new_tokens=max_new_tokens,
            **kwargs,
        )

    return _make_model


# Storage Fixtures


@pytest.fixture
def temp_db_path():
    """Creates a temporary SQLite database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
        db_path = temp_file.name

    yield db_path

    # Cleanup after test
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def unique_session_id():
    """Generates a unique session ID for each test."""
    return f"test_session_{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def storage_backend(temp_db_path):
    """
    Creates a temporary LibSQL storage backend for testing.

    Usage:
        async def test_something(storage_backend):
            await storage_backend.connect()
            # ... use storage ...
            await storage_backend.disconnect()
    """
    storage = LibSQLStorage(url=f"sqlite+aiosqlite:///{temp_db_path}")
    await storage.connect()
    yield storage
    await storage.disconnect()


@pytest.fixture
async def agent_storage(storage_backend):
    """
    Creates an AgentStorage instance for testing.

    Usage:
        async def test_something(agent_storage):
            thread = await agent_storage.create_thread(thread_id="test_thread")
            await agent_storage.add_message("test_thread", "user", "Hello")
    """
    storage = AgentStorage(storage=storage_backend, max_messages=100)
    yield storage
    await storage.stop()


# Agent Fixtures


@pytest.fixture
def simple_agent(hf_model):
    """
    Creates a simple agent with the shared HuggingFace model.

    Use this for basic invoke/stream tests.
    """
    return Agent(
        name="TestAgent",
        instructions="You are a helpful assistant. Be concise.",
        model=hf_model,
        temperature=0.7,
        max_tokens=200,
        max_retries=1,
    )


@pytest.fixture
def make_agent(hf_model):
    """
    Factory fixture to create agents with custom settings.

    Usage:
        def test_custom_agent(make_agent):
            agent = make_agent(name="CustomAgent", tools=[my_tool])
    """

    def _make_agent(
        name: str = "TestAgent",
        instructions: str = "You are a helpful assistant.",
        model: Any | None = None,
        tools: list | None = None,
        **kwargs: Any,
    ) -> Agent:
        return Agent(
            name=name,
            instructions=instructions,
            model=model or hf_model,
            tools=tools,
            **kwargs,
        )

    return _make_agent


# =============================================================================
# Common Test Tools
# =============================================================================


@pytest.fixture
def calculator_tool():
    """Provides a calculator tool for testing."""

    @tool
    def calculator(operation: str, a: float, b: float) -> float:
        """
        Perform basic arithmetic operations.

        Args:
            operation: add, subtract, multiply, divide
            a: First number
            b: Second number
        """
        ops: dict[str, Callable[[float, float], float]] = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else float("inf"),
        }
        if operation not in ops:
            raise ValueError(f"Unknown operation: {operation}")
        return ops[operation](a, b)

    return calculator


@pytest.fixture
def weather_tool():
    """Provides a mock weather tool for testing."""

    @tool
    def get_weather(city: str) -> str:
        """Get weather for a city (mock)."""
        data = {
            "london": "Rainy, 15°C",
            "paris": "Sunny, 22°C",
            "tokyo": "Clear, 25°C",
        }
        return data.get(city.lower(), f"No data for {city}")

    return get_weather
