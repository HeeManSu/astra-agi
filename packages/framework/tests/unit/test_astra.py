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
            astra = Astra(agents=[])
            assert astra.context is not None
            mock_context_cls.assert_called_once()

    def test_add_agent_injection(self):
        """Test that adding an agent injects the context."""
        with patch('framework.astra.AstraContext') as mock_context_cls:
            # Setup mocks
            mock_context = MagicMock()
            mock_context_cls.return_value = mock_context
            
            astra = Astra(agents=[])
            agent = Agent(name="Test", instructions="Test", model="google/gemini-1.5-flash")
            
            # Verify agent has no context initially (or lazy default)
            assert agent._context is None
            
            # Add agent
            astra.add_agent(agent)
            
            # Verify context was injected
            assert agent.context is mock_context
            assert agent in astra.list_agents()

    def test_get_agent(self):
        """Test retrieving agents."""
        with patch('framework.astra.AstraContext'):
            agent = Agent(id="agent-1", name="Test", instructions="Test", model="google/gemini-1.5-flash")
            astra = Astra(agents=[agent])
            
            retrieved = astra.get_agent("agent-1")
            assert retrieved is agent
            
            with pytest.raises(ValueError):
                astra.get_agent("non-existent")
