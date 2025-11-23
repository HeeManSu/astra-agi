import pytest
from typing import List, Dict, Optional
from framework.agents.tool import tool, Tool, _type_to_json_schema_type

class TestTool:
    def test_tool_decorator_simple(self):
        """Test simple tool decorator."""
        @tool
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b
        
        assert isinstance(add, Tool)
        assert add.name == "add"
        assert add.description == "Add two numbers."
        assert add.parameters["properties"]["a"]["type"] == "integer"
        assert add.parameters["properties"]["b"]["type"] == "integer"
        assert "a" in add.parameters["required"]
        assert "b" in add.parameters["required"]
        
        # Test invocation
        assert add(1, 2) == 3

    def test_tool_decorator_complex_types(self):
        """Test tool decorator with complex types."""
        @tool
        def process_items(items: List[str], config: Dict[str, int]) -> bool:
            """Process items."""
            return True
        
        assert process_items.parameters["properties"]["items"]["type"] == "array"
        assert process_items.parameters["properties"]["items"]["items"]["type"] == "string"
        assert process_items.parameters["properties"]["config"]["type"] == "object"

    def test_tool_decorator_custom_metadata(self):
        """Test tool decorator with custom name and description."""
        @tool(name="custom_add", description="Custom description")
        def add(a: int, b: int) -> int:
            return a + b
        
        assert add.name == "custom_add"
        assert add.description == "Custom description"

    def test_async_tool(self):
        """Test async tool."""
        @tool
        async def async_add(a: int, b: int) -> int:
            return a + b
        
        import asyncio
        assert asyncio.iscoroutinefunction(async_add.invoke)

    def test_type_mapping(self):
        """Test type to JSON schema mapping."""
        assert _type_to_json_schema_type(int) == {"type": "integer"}
        assert _type_to_json_schema_type(str) == {"type": "string"}
        assert _type_to_json_schema_type(bool) == {"type": "boolean"}
        assert _type_to_json_schema_type(float) == {"type": "number"}
        assert _type_to_json_schema_type(List[int]) == {"type": "array", "items": {"type": "integer"}}
        assert _type_to_json_schema_type(Optional[str]) == {"type": "string"}
