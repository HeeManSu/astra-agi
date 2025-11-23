import pytest
import asyncio
import os
import time
from unittest.mock import MagicMock
from framework.agents import Agent
from framework.models import Gemini
from framework.storage.databases.sqlite import SQLiteStorage

@pytest.mark.asyncio
async def test_storage_queue_burst(tmp_path):
    """Test high-throughput burst messaging with queue optimization."""
    db_path = tmp_path / "queue_demo.db"
    storage = SQLiteStorage(f"file:{db_path}")
    await storage.connect()
    
    # Mock API key
    os.environ["GOOGLE_API_KEY"] = "dummy"
    
    agent = Agent(
        name="FastBot",
        model=Gemini("1.5-flash"),
        storage=storage
    )
    
    # Mock generation
    mock_response = MagicMock()
    mock_response.text = "Ack."
    mock_response.candidates = [MagicMock(content=MagicMock(parts=[MagicMock(text="Ack.")]))]
    mock_response.usage_metadata = MagicMock()
    mock_response.usage_metadata.prompt_token_count = 5
    mock_response.usage_metadata.candidates_token_count = 5
    
    # Trigger lazy init
    _ = agent._model_instance
    agent._model_instance._model.generate_content = MagicMock(return_value=mock_response)
    
    # Start agent (starts queue worker)
    await agent.startup()
    
    # Burst 50 messages
    for i in range(50):
        await agent.invoke(f"Message {i}")
        
    # Wait for flush (default 0.5s)
    await asyncio.sleep(1.0)
    
    # Verify persistence
    history = await agent.memory.get_history(agent.id, limit=200)
    
    # Should be 100 (50 user + 50 assistant)
    assert len(history) == 100
    
    await agent.shutdown()
    await storage.disconnect()
