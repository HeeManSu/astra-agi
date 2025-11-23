import pytest
import asyncio
import os
from unittest.mock import MagicMock
from framework.agents import Agent
from framework.astra import Astra
from framework.models import Gemini
from framework.storage import SQLiteStorage

@pytest.mark.asyncio
async def test_storage_persistence_flow(tmp_path):
    """Test full storage persistence flow with mocked model."""
    db_path = tmp_path / "test_storage.db"
    storage = SQLiteStorage(f"file:{db_path}")
    await storage.connect()
    
    # Mock API key
    os.environ["GOOGLE_API_KEY"] = "dummy_key"
    
    agent = Agent(
        name="StorageBot",
        model=Gemini("1.5-flash"),
        instructions="You are a helpful assistant.",
        storage=storage
    )
    
    # Mock model response
    mock_response = MagicMock()
    mock_response.text = "I am a mock response."
    mock_response.candidates = [MagicMock(content=MagicMock(parts=[MagicMock(text="I am a mock response.")]))]
    mock_response.usage_metadata = MagicMock()
    mock_response.usage_metadata.prompt_token_count = 10
    mock_response.usage_metadata.candidates_token_count = 20
    
    # We need to mock the internal model instance which is created lazily
    # Accessing _model_instance triggers creation
    # We need to mock the internal model instance which is created lazily
    # Accessing _model_instance triggers creation
    model_instance = agent._model_instance
    # Type check for static analysis
    from framework.models.google.gemini import GeminiModel
    assert isinstance(model_instance, GeminiModel)
    model_instance._model.generate_content = MagicMock(return_value=mock_response)
    
    # Invoke agent
    await agent.invoke("Hello, save this message!")
    
    # Wait for queue to flush (default flush_interval is 0.5s)
    await asyncio.sleep(1.0)
    
    # Verify persistence
    assert agent.memory is not None
    history = await agent.memory.get_history(agent.id)
    assert len(history) == 2
    assert history[0].content == "Hello, save this message!"
    assert history[1].content == "I am a mock response."
    
    await storage.disconnect()

@pytest.mark.asyncio
async def test_astra_storage_integration(tmp_path):
    """Test Astra storage injection into agents."""
    db_path = tmp_path / "astra_storage.db"
    astra_storage = SQLiteStorage(f"file:{db_path}")
    
    # Mock API key
    os.environ["GOOGLE_API_KEY"] = "dummy_key"
    
    agent = Agent(name="AstraBot", model=Gemini("1.5-flash"), instructions="Test")
    assert agent.storage is None
    
    # Initialize Astra with storage
    astra = Astra(agents=[agent], storage=astra_storage)
    
    assert agent.storage == astra_storage
    assert agent.memory is not None
