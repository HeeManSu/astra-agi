import pytest
from unittest.mock import MagicMock
import sys
import os

# Mock external dependencies before they are imported by framework
sys.modules["google"] = MagicMock()
sys.modules["google.generativeai"] = MagicMock()
sys.modules["google.generativeai.types"] = MagicMock()

# Mock observability dependencies
mock_otel = MagicMock()
sys.modules["opentelemetry"] = mock_otel
sys.modules["opentelemetry.trace"] = MagicMock()
sys.modules["opentelemetry.trace.status"] = MagicMock()
sys.modules["opentelemetry.trace.propagation"] = MagicMock()
sys.modules["opentelemetry.sdk"] = MagicMock()
sys.modules["opentelemetry.sdk.resources"] = MagicMock()
sys.modules["opentelemetry.sdk.trace"] = MagicMock()
sys.modules["opentelemetry.sdk.trace.export"] = MagicMock()
sys.modules["opentelemetry.exporter"] = MagicMock()
sys.modules["opentelemetry.exporter.otlp"] = MagicMock()
sys.modules["opentelemetry.exporter.otlp.proto"] = MagicMock()
sys.modules["opentelemetry.exporter.otlp.proto.http"] = MagicMock()
sys.modules["opentelemetry.exporter.otlp.proto.http.trace_exporter"] = MagicMock()

@pytest.fixture(scope="session", autouse=True)
def mock_deps():
    """Ensure dependencies are mocked for all tests."""
    pass

@pytest.fixture
def mock_observability():
    """Mock the Observability class."""
    mock = MagicMock()
    mock.logger = MagicMock()
    mock.tracer = MagicMock()
    mock.metrics = MagicMock()
    
    # Mock trace decorators
    def trace_mock(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    mock.trace_agent_run = trace_mock
    mock.trace_tool_call = trace_mock
    mock.trace_model_call = trace_mock
    
    return mock

@pytest.fixture
def mock_context(mock_observability):
    """Mock AstraContext."""
    mock = MagicMock()
    mock.observability = mock_observability
    mock.logger = mock_observability.logger
    return mock
