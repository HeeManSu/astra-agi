import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from framework.agents.agent import Agent
from framework.astra import AstraContext

class TestAgent:
    def test_initialization_standalone(self):
        """Test standalone agent initialization."""
        agent = Agent(name="Test", instructions="Test", model="google/gemini-1.5-flash")
        
        assert agent.name == "Test"
        assert agent.instructions == "Test"
        assert agent.model == {'provider': 'google', 'model': 'gemini-1.5-flash'}
        assert agent.id.startswith("agent-")
        
        # Context should be None initially
        assert agent._context is None

    def test_lazy_context_initialization(self):
        """Test that context is lazily initialized for standalone agents."""
        with patch('framework.agents.agent.AstraContext') as mock_context_cls:
            agent = Agent(name="Test", instructions="Test", model="google/gemini-1.5-flash")
            
            # Access context
            context = agent.context
            
            assert context is not None
            mock_context_cls.assert_called_once()
            assert agent._context is context

    @pytest.mark.asyncio
    async def test_startup_shutdown(self):
        """Test startup and shutdown lifecycle."""
        with patch('framework.agents.agent.AstraContext') as mock_context_cls:
            mock_context = MagicMock()
            mock_context_cls.return_value = mock_context
            
            agent = Agent(name="Test", instructions="Test", model="google/gemini-1.5-flash")
            
            # Startup
            await agent.startup()
            assert agent._initialized is True
            # Should have initialized context
            assert agent.context is mock_context
            
            # Shutdown
            await agent.shutdown()
            assert agent._initialized is False
            mock_context.shutdown.assert_called_once()

    def test_model_config_parsing(self):
        """Test model configuration parsing."""
        # String format
        agent1 = Agent(name="A1", instructions="I", model="google/gemini-pro")
        assert agent1.model == {'provider': 'google', 'model': 'gemini-pro'}
        
        # Dict format
        agent2 = Agent(name="A2", instructions="I", model={'provider': 'openai', 'model': 'gpt-4'})
        assert agent2.model == {'provider': 'openai', 'model': 'gpt-4'}
        
        # Default provider
        agent3 = Agent(name="A3", instructions="I", model="gpt-4")
        assert agent3.model == {'provider': 'openai', 'model': 'gpt-4'}
