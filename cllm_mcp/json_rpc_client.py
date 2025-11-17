"""JSON-RPC Protocol Handler for MCP Client.

This module encapsulates the JSON-RPC 2.0 protocol handling for communication
with MCP servers via stdio. It abstracts away the messaging protocol details
from the higher-level MCP client logic.

This module is internal to cllm-mcp and is accessed via MCPClient in client.py.
"""

import json
import subprocess  # noqa: S404,B404
from typing import Any, Dict


class JsonRpcClient:
    """Handles JSON-RPC 2.0 protocol communication with subprocess."""

    def __init__(self, process: subprocess.Popen):
        """Initialize JSON-RPC client with an active subprocess.

        Args:
            process: Active subprocess.Popen instance with stdin/stdout/stderr pipes
        """
        self.process = process
        self.message_id = 0

    def send_message(self, message: Dict[str, Any]):
        """Send a JSON-RPC message to the server.

        Args:
            message: Dictionary containing JSON-RPC message

        Raises:
            Exception: If process not started or stdin not available
        """
        if not self.process or not self.process.stdin:
            raise Exception("Server process not started")

        json_str = json.dumps(message)
        self.process.stdin.write(json_str + "\n")
        self.process.stdin.flush()

    def send_notification(self, notification: Dict[str, Any]):
        """Send a JSON-RPC notification (no response expected).

        Args:
            notification: Dictionary containing JSON-RPC notification
        """
        self.send_message(notification)

    def read_message(self) -> Dict[str, Any]:
        """Read a JSON-RPC message from the server.

        Returns:
            Dictionary parsed from JSON response

        Raises:
            Exception: If process not started, stdout not available, or invalid JSON
        """
        if not self.process or not self.process.stdout:
            raise Exception("Server process not started")

        line = self.process.stdout.readline()
        if not line:
            stderr_output = self.process.stderr.read() if self.process.stderr else ""
            raise Exception(f"No response from server. Stderr: {stderr_output}")

        try:
            return json.loads(line)
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {line}. Error: {e}") from e

    def next_id(self) -> int:
        """Generate next message ID for request correlation.

        Returns:
            Incremented message ID
        """
        self.message_id += 1
        return self.message_id

    def initialize(self) -> Dict[str, Any]:
        """Send MCP initialize request and wait for response.

        Sends the initialize handshake message and processes the response.
        Also sends the initialized notification afterward.

        Returns:
            The initialize response from the server

        Raises:
            Exception: If initialization fails or returns error
        """
        # Send initialize request
        self.send_message(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "mcp-cli", "version": "1.0.0"},
                },
            }
        )

        # Read initialize response
        response = self.read_message()
        if "error" in response:
            raise Exception(f"Initialize error: {response['error']}")

        # Send initialized notification
        self.send_notification(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )

        return response

    def list_tools(self) -> list:
        """Request list of available tools from server.

        Returns:
            List of tool definitions

        Raises:
            Exception: If request fails or server returns error
        """
        self.send_message(
            {"jsonrpc": "2.0", "id": self.next_id(), "method": "tools/list"}
        )

        response = self.read_message()
        if "error" in response:
            raise Exception(f"Error listing tools: {response['error']}")

        return response.get("result", {}).get("tools", [])

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a specific tool on the server.

        Args:
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Tool execution result

        Raises:
            Exception: If request fails or server returns error
        """
        self.send_message(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }
        )

        response = self.read_message()
        if "error" in response:
            raise Exception(f"Error calling tool: {response['error']}")

        return response.get("result", {})
