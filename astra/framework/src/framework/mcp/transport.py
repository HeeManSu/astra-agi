"""
MCP transport layer.

Supports stdio (local) and HTTP (remote) transports.
"""

from abc import ABC, abstractmethod
import asyncio
import json
import os
from typing import Any


try:
    import aiohttp
except ImportError:
    aiohttp = None

from framework.mcp.exceptions import MCPConnectionError, MCPTransportError


class MCPTransport(ABC):
    """Base class for MCP transports."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to MCP server."""

    @abstractmethod
    async def send_request(self, method: str, params: dict[str, Any]) -> Any:
        """
        Send JSON-RPC request.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            Response result
        """

    @abstractmethod
    async def close(self) -> None:
        """Close connection."""


class StdioTransport(MCPTransport):
    """
    Stdio transport for local MCP servers.

    Communicates via stdin/stdout with subprocess.
    """

    def __init__(
        self, command: str, args: list[str] | None = None, env: dict[str, str] | None = None
    ):
        """
        Initialize stdio transport.

        Args:
            command: Command to execute
            args: Command arguments
            env: Environment variables
        """
        self.command = command
        self.args = args or []
        self.env = env
        self.process: asyncio.subprocess.Process | None = None
        self._request_id = 0

    async def connect(self) -> None:
        """Start MCP server process."""
        try:
            # Merge env
            run_env = os.environ.copy()
            if self.env:
                run_env.update(self.env)

            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=run_env,
            )
        except Exception as e:
            raise MCPConnectionError(f"Failed to start MCP server: {e}") from e

    async def send_request(self, method: str, params: dict[str, Any]) -> Any:
        """Send JSON-RPC request via stdin."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise MCPTransportError("Transport not connected")

        self._request_id += 1
        request = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}

        try:
            # Write to stdin
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()

            # Read from stdout
            response_line = await self.process.stdout.readline()
            if not response_line:
                # Check stderr if process failed
                stderr = await self.process.stderr.read() if self.process.stderr else b""
                raise MCPTransportError(f"No response from MCP server. Stderr: {stderr.decode()}")

            response = json.loads(response_line.decode())

            if "error" in response:
                raise MCPTransportError(f"MCP error: {response['error']}")

            return response.get("result")

        except json.JSONDecodeError as e:
            raise MCPTransportError(f"Invalid JSON response: {e}") from e
        except Exception as e:
            raise MCPTransportError(f"Transport error: {e}") from e

    async def close(self) -> None:
        """Close connection and terminate process."""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception:
                pass
            self.process = None


class HTTPTransport(MCPTransport):
    """
    HTTP transport for remote MCP servers.
    """

    def __init__(self, url: str):
        """
        Initialize HTTP transport.

        Args:
            url: MCP server URL
        """
        self.url = url
        self.session: Any | None = None
        self._request_id = 0

    async def connect(self) -> None:
        """Create HTTP session."""
        if aiohttp is None:
            raise MCPConnectionError(
                "aiohttp required for HTTP transport. Install with: uv add aiohttp"
            )
        self.session = aiohttp.ClientSession()

    async def send_request(self, method: str, params: dict[str, Any]) -> Any:
        """Send JSON-RPC request via HTTP."""
        if not self.session:
            raise MCPTransportError("Transport not connected")

        self._request_id += 1
        request = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}

        try:
            async with self.session.post(self.url, json=request) as resp:
                response = await resp.json()

                if "error" in response:
                    raise MCPTransportError(f"MCP error: {response['error']}")

                return response.get("result")

        except Exception as e:
            raise MCPTransportError(f"HTTP transport error: {e}") from e

    async def close(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
