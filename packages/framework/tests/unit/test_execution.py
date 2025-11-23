import pytest
from unittest.mock import MagicMock
from framework.agents.execution import (
    ExecutionContext,
    prepare_tools_step,
    prepare_memory_step,
    execute_tool
)
from framework.agents.tool import tool

class TestExecution:
    @pytest.mark.asyncio
    async def test_prepare_tools_step(self):
        """Test tool preparation."""
        @tool
        def test_tool(a: int):
            pass
            
        context = ExecutionContext(messages=[])
        context = await prepare_tools_step(context, [test_tool])
        
        assert context.converted_tools is not None
        assert len(context.converted_tools) == 1
        assert context.converted_tools[0]["name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_prepare_memory_step(self):
        """Test memory preparation (instructions)."""
        context = ExecutionContext(messages=[{"role": "user", "content": "Hi"}])
        instructions = "You are a bot."
        
        context = await prepare_memory_step(context, instructions)
        
        assert len(context.messages) == 2
        assert context.messages[0]["role"] == "system"
        assert context.messages[0]["content"] == instructions

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test tool execution."""
        @tool
        def add(a: int, b: int) -> int:
            return a + b
            
        result = await execute_tool("add", {"a": 1, "b": 2}, [add])
        assert result == 3
        
        # Test unknown tool
        with pytest.raises(ValueError):
            await execute_tool("unknown", {}, [add])
