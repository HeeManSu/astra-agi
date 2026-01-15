"""
Unit tests for Agent middleware configuration.

These tests verify middleware setup and configuration without making any LLM calls.
All tests are fast and have no external dependencies.

Test Cases:
1. test_agent_accepts_input_middleware - Agent can be created with input middleware
2. test_agent_with_no_middleware - Agent works without middleware
3. test_agent_multiple_input_middlewares - Agent can have multiple input middlewares
4. test_agent_accepts_output_middleware - Agent can be created with output middleware
5. test_middleware_context_creation - MiddlewareContext can be created
6. test_middleware_context_extra - MiddlewareContext supports extra data
"""

from framework.agents import Agent
from framework.guardrails import PromptInjectionFilter
from framework.middlewares import MiddlewareContext
import pytest


@pytest.mark.unit
class TestInputMiddleware:
    """Tests for input middleware configuration."""

    def test_agent_accepts_input_middleware(self, hf_model):
        """Agent can be created with input middleware."""
        agent = Agent(
            name="MiddlewareAgent",
            instructions="Be helpful.",
            model=hf_model,
            input_middlewares=[PromptInjectionFilter()],
        )
        assert agent.input_middlewares is not None

    def test_agent_with_no_middleware(self, hf_model):
        """Agent works without middleware."""
        agent = Agent(
            name="NoMiddlewareAgent",
            instructions="Be helpful.",
            model=hf_model,
        )
        assert agent.input_middlewares is None

    def test_agent_multiple_input_middlewares(self, hf_model):
        """Agent can have multiple input middlewares."""
        middleware1 = PromptInjectionFilter()
        middleware2 = PromptInjectionFilter()

        agent = Agent(
            name="MultiMiddlewareAgent",
            instructions="Be helpful.",
            model=hf_model,
            input_middlewares=[middleware1, middleware2],
        )
        assert agent.input_middlewares is not None
        assert isinstance(agent.input_middlewares, list)
        assert len(agent.input_middlewares) == 2


@pytest.mark.unit
class TestOutputMiddleware:
    """Tests for output middleware configuration."""

    def test_agent_accepts_output_middleware(self, hf_model):
        """Agent can be created with output middleware."""
        from framework.guardrails import OutputPIIFilter, PIIAction

        agent = Agent(
            name="OutputMiddlewareAgent",
            instructions="Be helpful.",
            model=hf_model,
            output_middlewares=[OutputPIIFilter(action=PIIAction.REDACT)],
        )
        assert agent.output_middlewares is not None


@pytest.mark.unit
class TestMiddlewareContext:
    """Tests for MiddlewareContext."""

    def test_middleware_context_creation(self, hf_model):
        """MiddlewareContext can be created."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=hf_model,
        )
        ctx = MiddlewareContext(
            agent=agent,
            thread_id="test-thread-123",
        )
        assert ctx.agent is agent
        assert ctx.thread_id == "test-thread-123"

    def test_middleware_context_extra(self, hf_model):
        """MiddlewareContext supports extra data."""
        agent = Agent(
            name="TestAgent",
            instructions="You are helpful.",
            model=hf_model,
        )
        ctx = MiddlewareContext(
            agent=agent,
            thread_id="test-thread",
            extra={"key": "value"},
        )
        assert ctx.extra == {"key": "value"}
