"""
Shared pytest fixtures and configuration for cllm-mcp tests.

This module provides common fixtures, mocks, and test utilities used across
the test suite.
"""

import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from unittest import mock

import pytest


# ============================================================================
# MOCK MCP SERVER
# ============================================================================

class MockMCPServer:
    """Mock MCP server for testing without real server processes."""

    def __init__(
        self,
        tools: Optional[List[Dict]] = None,
        responses: Optional[Dict] = None,
        crash_on_tool: Optional[str] = None,
    ):
        """
        Initialize mock server.

        Args:
            tools: List of tool definitions (defaults to basic tools)
            responses: Custom tool response mappings
            crash_on_tool: Tool name that causes server to crash
        """
        self.tools = tools or self._default_tools()
        self.responses = responses or {}
        self.crash_on_tool = crash_on_tool
        self.call_count = 0

    @staticmethod
    def _default_tools() -> List[Dict]:
        """Return default tool definitions for testing."""
        return [
            {
                "name": "echo",
                "description": "Echo tool for testing",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to echo"}
                    },
                    "required": ["message"],
                },
            },
            {
                "name": "add",
                "description": "Add two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"},
                    },
                    "required": ["a", "b"],
                },
            },
        ]

    def simulate_tool_call(self, tool_name: str, args: Dict) -> Dict:
        """
        Simulate a tool call and return response.

        Args:
            tool_name: Name of tool to call
            args: Arguments for tool

        Returns:
            Tool response dict

        Raises:
            RuntimeError: If crash_on_tool matches
        """
        self.call_count += 1

        # Simulate crash if requested
        if self.crash_on_tool and tool_name == self.crash_on_tool:
            raise RuntimeError(f"Simulated crash on tool: {tool_name}")

        # Return custom response if available
        if tool_name in self.responses:
            return self.responses[tool_name]

        # Default responses based on tool name
        if tool_name == "echo":
            return {"content": [{"type": "text", "text": args.get("message", "")}]}

        if tool_name == "add":
            result = args.get("a", 0) + args.get("b", 0)
            return {"content": [{"type": "text", "text": str(result)}]}

        return {"error": f"Tool not found: {tool_name}"}


# ============================================================================
# SOCKET AND FILE FIXTURES
# ============================================================================


@pytest.fixture
def temp_socket_path():
    """Provide a temporary socket path for testing."""
    socket_path = f"/tmp/test-mcp-{os.getpid()}-{uuid.uuid4()}.sock"
    yield socket_path
    # Cleanup
    if os.path.exists(socket_path):
        try:
            os.unlink(socket_path)
        except OSError:
            pass


@pytest.fixture
def temp_config_file(tmp_path):
    """Provide a temporary config file with sample servers."""
    config = {
        "mcpServers": {
            "test-server": {
                "command": "python",
                "args": ["-m", "test_server"],
                "description": "Test MCP server",
            },
            "echo-server": {
                "command": "echo",
                "args": ["hello"],
                "description": "Simple echo server",
                "env": {"DEBUG": "1"},
            },
        }
    }
    config_file = tmp_path / "mcp-config.json"
    config_file.write_text(json.dumps(config, indent=2))
    return config_file


@pytest.fixture
def isolated_temp_dir(tmp_path):
    """Provide isolated temporary directory and change to it."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(old_cwd)


# ============================================================================
# MOCK SERVER FIXTURES
# ============================================================================


@pytest.fixture
def mock_mcp_server():
    """Provide a mock MCP server instance."""
    return MockMCPServer()


@pytest.fixture
def mock_server_with_crash():
    """Provide a mock server that crashes on specific tool."""
    return MockMCPServer(crash_on_tool="echo")


@pytest.fixture
def mock_server_custom_tools():
    """Provide a mock server with custom tools."""
    tools = [
        {
            "name": "list_files",
            "description": "List files in directory",
            "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
        },
        {
            "name": "read_file",
            "description": "Read file contents",
            "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
        },
    ]
    responses = {
        "list_files": {"content": [{"type": "text", "text": "file1.txt\nfile2.txt"}]},
        "read_file": {"content": [{"type": "text", "text": "file contents"}]},
    }
    return MockMCPServer(tools=tools, responses=responses)


# ============================================================================
# ENVIRONMENT AND MOCKING FIXTURES
# ============================================================================


@pytest.fixture
def clean_env():
    """Provide clean environment without MCP-related variables."""
    old_env = os.environ.copy()
    # Remove any MCP-related variables
    for key in list(os.environ.keys()):
        if key.startswith("MCP_"):
            del os.environ[key]
    yield os.environ.copy()
    # Restore old environment
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture
def mock_daemon_socket(mocker, temp_socket_path):
    """Mock a daemon socket that responds correctly."""
    mock_socket = mock.MagicMock()
    mocker.patch("socket.socket", return_value=mock_socket)

    def mock_recv(size):
        # Simulate receiving a response
        response = {"result": {"tools": []}}
        return json.dumps(response).encode() + b"\n"

    mock_socket.recv.side_effect = mock_recv
    return mock_socket


@pytest.fixture
def mock_subprocess(mocker):
    """Mock subprocess for testing without spawning actual processes."""
    mock_popen = mock.MagicMock()
    mock_popen.stdin = mock.MagicMock()
    mock_popen.stdout = mock.MagicMock()
    mock_popen.stderr = mock.MagicMock()
    mock_popen.pid = 12345
    mock_popen.returncode = 0

    def mock_recv_line():
        response = {"jsonrpc": "2.0", "result": {"tools": []}}
        return json.dumps(response).encode() + b"\n"

    mock_popen.stdout.readline.side_effect = mock_recv_line
    mocker.patch("subprocess.Popen", return_value=mock_popen)
    return mock_popen


# ============================================================================
# COMMAND LINE ARGUMENT FIXTURES
# ============================================================================


@pytest.fixture
def mock_argv(monkeypatch):
    """Provide function to mock sys.argv."""

    def _mock_argv(*args):
        monkeypatch.setattr(sys, "argv", ["cllm-mcp"] + list(args))

    return _mock_argv


# ============================================================================
# TEST DATA CONSTANTS
# ============================================================================


# Sample MCP tools for testing
SAMPLE_TOOLS = [
    {
        "name": "echo",
        "description": "Echo tool",
        "inputSchema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    },
    {
        "name": "add",
        "description": "Add two numbers",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
]

# Sample tool responses
SAMPLE_TOOL_RESPONSE = {
    "jsonrpc": "2.0",
    "result": {"content": [{"type": "text", "text": "Hello, World!"}]},
}

# Sample configuration
SAMPLE_CONFIG = {
    "mcpServers": {
        "test-server": {
            "command": "python",
            "args": ["-m", "test_server"],
            "description": "Test server",
        },
        "github": {
            "command": "python",
            "args": ["-m", "github_server"],
            "env": {"GITHUB_TOKEN": "test-token"},
            "description": "GitHub API server",
        },
    }
}


# ============================================================================
# PYTEST CONFIGURATION AND MARKERS
# ============================================================================


def pytest_configure(config):
    """Configure pytest and register custom markers."""
    config.addinivalue_line("markers", "unit: Mark test as a unit test")
    config.addinivalue_line("markers", "integration: Mark test as an integration test")
    config.addinivalue_line("markers", "slow: Mark test as slow running")
    config.addinivalue_line("markers", "socket: Requires socket operations")
    config.addinivalue_line("markers", "daemon: Requires daemon operations")
