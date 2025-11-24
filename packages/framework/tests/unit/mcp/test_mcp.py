"""
Unit tests for MCP integration.
"""
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, List

from framework.mcp.client import MCPClient
from framework.mcp.transport import MCPTransport
from framework.mcp.tools import MCPTools
from framework.mcp.exceptions import MCPConnectionError, MCPToolExecutionError
from framework.agents.agent import Agent
from framework.agents.tool import Tool


class MockTransport(MCPTransport):
    """Mock transport for testing."""
    
    def __init__(self):
        self.connected = False
        self.requests = []
        self.responses = {}
    
    async def connect(self) -> None:
        self.connected = True
    
    async def send_request(self, method: str, params: Dict[str, Any]) -> Any:
        self.requests.append({"method": method, "params": params})
        
        if method in self.responses:
            response = self.responses[method]
            if isinstance(response, Exception):
                raise response
            return response
        
        # Default responses
        if method == "initialize":
            return {"protocolVersion": "2024-11-05"}
        elif method == "tools/list":
            return {"tools": []}
        elif method == "tools/call":
            return "success"
            
        return None
    
    async def close(self) -> None:
        self.connected = False


class TestMCP(unittest.IsolatedAsyncioTestCase):
    
    async def test_mcp_client_connection(self):
        """Test MCP client connection lifecycle."""
        transport = MockTransport()
        client = MCPClient(transport)
        
        # Test connect
        await client.connect()
        self.assertTrue(client.connected)
        self.assertTrue(transport.connected)
        self.assertEqual(transport.requests[0]["method"], "initialize")
        
        # Test close
        await client.close()
        self.assertFalse(client.connected)
        self.assertFalse(transport.connected)

    async def test_mcp_client_list_tools(self):
        """Test fetching tools."""
        transport = MockTransport()
        transport.responses["tools/list"] = {
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read a file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}}
                    }
                }
            ]
        }
        
        client = MCPClient(transport)
        await client.connect()
        
        tools = await client.list_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "read_file")

    async def test_mcp_client_call_tool(self):
        """Test calling a tool."""
        transport = MockTransport()
        transport.responses["tools/call"] = "file content"
        
        client = MCPClient(transport)
        await client.connect()
        
        result = await client.call_tool("read_file", {"path": "test.txt"})
        self.assertEqual(result, "file content")
        
        # Verify request params
        last_request = transport.requests[-1]
        self.assertEqual(last_request["method"], "tools/call")
        self.assertEqual(last_request["params"]["name"], "read_file")
        self.assertEqual(last_request["params"]["arguments"], {"path": "test.txt"})

    async def test_mcp_tools_initialization(self):
        """Test MCPTools wrapper initialization."""
        # Mock StdioTransport to return our MockTransport
        with patch("framework.mcp.tools.StdioTransport") as MockStdio:
            mock_transport = MockTransport()
            mock_transport.responses["tools/list"] = {
                "tools": [
                    {
                        "name": "read_file",
                        "description": "Read a file",
                        "inputSchema": {}
                    }
                ]
            }
            MockStdio.return_value = mock_transport
            
            mcp = MCPTools(command="test command")
            
            # Initialize
            tools = await mcp.initialize()
            
            self.assertEqual(len(tools), 1)
            self.assertIsInstance(tools[0], Tool)
            self.assertEqual(tools[0].name, "read_file")
            
            # Verify transport was created
            MockStdio.assert_called_once()

    async def test_mcp_tools_collision_detection(self):
        """Test tool name collision detection and prefixing."""
        with patch("framework.mcp.tools.StdioTransport") as MockStdio:
            mock_transport = MockTransport()
            mock_transport.responses["tools/list"] = {
                "tools": [{"name": "read_file", "inputSchema": {}}]
            }
            MockStdio.return_value = mock_transport
            
            mcp = MCPTools(command="test", name="fs")
            
            # Initialize with existing tool name collision
            tools = await mcp.initialize(existing_tool_names=["read_file"])
            
            self.assertEqual(len(tools), 1)
            # Should have prefix added
            self.assertEqual(tools[0].name, "fs_read_file")

    async def test_agent_integration(self):
        """Test Agent auto-initialization of MCP tools."""
        # Mock MCPTools
        mock_mcp = MagicMock(spec=MCPTools)
        mock_mcp.initialize = AsyncMock()
        
        # Create a real Tool object to return
        test_tool = Tool(
            name="mcp_tool",
            description="Test tool",
            parameters={},
            invoke=lambda: "success"
        )
        mock_mcp.initialize.return_value = [test_tool]
        
        # We need to mock _detect_collisions attribute check
        mock_mcp._detect_collisions = MagicMock()
        
        # Create agent with mock MCP tool
        agent = Agent(
            name="TestAgent",
            instructions="Test",
            model="test/model",
            tools=[mock_mcp]
        )
        
        # Manually trigger startup (which is called by invoke)
        await agent.startup()
        
        # Verify initialize was called
        mock_mcp.initialize.assert_called_once()
        
        # Verify agent tools were updated
        self.assertEqual(len(agent.tools), 1)
        self.assertEqual(agent.tools[0], test_tool)
        self.assertEqual(agent.tools[0].name, "mcp_tool")


if __name__ == "__main__":
    unittest.main()
