"""
MCP transport layer.

Supports stdio (local) and HTTP (remote) transports.
"""
import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .exceptions import MCPTransportError, MCPConnectionError


class MCPTransport(ABC):
    """Base class for MCP transports."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to MCP server."""
        pass
    
    @abstractmethod
    async def send_request(self, method: str, params: Dict[str, Any]) -> Any:
        """
        Send JSON-RPC request.
        
        Args:
            method: RPC method name
            params: Method parameters
            
        Returns:
            Response result
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close connection."""
        pass


class StdioTransport(MCPTransport):
    """
    Stdio transport for local MCP servers.
    
    Communicates via stdin/stdout with subprocess.
    
    Example:
        ```python
        transport = StdioTransport("npx", ["-y", "@modelcontextprotocol/server-filesystem", "."])
        await transport.connect()
        result = await transport.send_request("tools/list", {})
        ```
    """
    
    def __init__(self, command: str, args: Optional[List[str]] = None):
        """
        Initialize stdio transport.
        
        Args:
            command: Command to execute
            args: Command arguments
        """
        self.command = command
        self.args = args or []
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
    
    async def connect(self) -> None:
        """Start MCP server process."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except Exception as e:
            raise MCPConnectionError(f"Failed to start MCP server: {e}")
    
    async def send_request(self, method: str, params: Dict[str, Any]) -> Any:
        """Send JSON-RPC request via stdin."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise MCPTransportError("Transport not connected")
        
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params
        }
        
        try:
            # Write to stdin
            request_json = json.dumps(request) + '\n'
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()
            
            # Read from stdout
            response_line = await self.process.stdout.readline()
            if not response_line:
                raise MCPTransportError("No response from MCP server")
            
            response = json.loads(response_line.decode())
            
            if "error" in response:
                raise MCPTransportError(f"MCP error: {response['error']}")
            
            return response.get("result")
        
        except json.JSONDecodeError as e:
            raise MCPTransportError(f"Invalid JSON response: {e}")
        except Exception as e:
            raise MCPTransportError(f"Transport error: {e}")
    
    async def close(self) -> None:
        """Close connection and terminate process."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None


class HTTPTransport(MCPTransport):
    """
    HTTP transport for remote MCP servers.
    
    Example:
        ```python
        transport = HTTPTransport("https://api.example.com/mcp")
        await transport.connect()
        result = await transport.send_request("tools/list", {})
        ```
    """
    
    def __init__(self, url: str):
        """
        Initialize HTTP transport.
        
        Args:
            url: MCP server URL
        """
        self.url = url
        self.session: Optional[Any] = None
        self._request_id = 0
    
    async def connect(self) -> None:
        """Create HTTP session."""
        try:
            import aiohttp
            self.session = aiohttp.ClientSession()
        except ImportError:
            raise MCPConnectionError(
                "aiohttp required for HTTP transport. "
                "Install with: pip install aiohttp"
            )
    
    async def send_request(self, method: str, params: Dict[str, Any]) -> Any:
        """Send JSON-RPC request via HTTP."""
        if not self.session:
            raise MCPTransportError("Transport not connected")
        
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params
        }
        
        try:
            async with self.session.post(self.url, json=request) as resp:
                response = await resp.json()
                
                if "error" in response:
                    raise MCPTransportError(f"MCP error: {response['error']}")
                
                return response.get("result")
        
        except Exception as e:
            raise MCPTransportError(f"HTTP transport error: {e}")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
