import pytest
from unittest.mock import MagicMock, patch
from framework.astra import Astra, AstraContext, FrameworkSettings
from framework.agents.agent import Agent

class TestAstraContext:
    def test_initialization(self):
        """Test AstraContext initialization."""
        with patch('framework.astra.Observability') as mock_obs:
            context = AstraContext()
            assert context.settings is not None
            assert context.observability is not None
            assert context.logger is not None
            mock_obs.init.assert_called_once()

    def test_shutdown(self):
        """Test AstraContext shutdown."""
        with patch('framework.astra.Observability') as mock_obs:
            context = AstraContext()
            context.shutdown()
            # Check that shutdown was called on the mock observability instance
            mock_obs_instance = context.observability
            if hasattr(mock_obs_instance, 'assert_called_once'):
                mock_obs_instance.shutdown.assert_called_once()  # type: ignore[attr-defined]

class TestAstra:
    def test_initialization(self):
        """Test Astra initialization."""
        with patch('framework.astra.AstraContext') as mock_context_cls:
            astra = Astra()
            assert astra.context is not None
            mock_context_cls.assert_called_once()

    def test_shared_context_usage(self):
        """Test that agents can share Astra context."""
        with patch('framework.astra.AstraContext') as mock_context_cls:
            # Setup mocks
            mock_context = MagicMock()
            mock_context_cls.return_value = mock_context
            
            # Initialize global infra
            astra = Astra()
            
            # Create agent
            agent = Agent(name="Test", instructions="Test", model="google/gemini-1.5-flash")
            
            # Verify agent has no context initially (or lazy default)
            assert agent._context is None
            
            # Manually share context
            agent.set_context(astra.context)
            
            # Verify context was injected
            assert agent.context is mock_context
