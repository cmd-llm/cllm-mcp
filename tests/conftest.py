"""Shared test configuration and fixtures for cllm-mcp tests."""

import json
import os
import socket
import tempfile
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# Test Markers
# ============================================================================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (fast, isolated)"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test (slower, requires setup)",
    )
    config.addinivalue_line(
        "markers", "daemon: mark test as requiring daemon functionality"
    )
    config.addinivalue_line("markers", "socket: mark test as requiring Unix socket")
    config.addinivalue_line("markers", "slow: mark test as slow-running")


# ============================================================================
# Mock MCP Server
# ============================================================================


class MockMCPServer:
    """Mock MCP server for testing."""

    def __init__(
        self, server_name: str = "test-server", tools: Optional[Dict[str, Any]] = None
    ):
        """Initialize mock MCP server.

        Args:
            server_name: Name of the server
            tools: Dictionary of available tools
        """
        self.server_name = server_name
        self.tools = tools or {
            "sample_tool": {
                "description": "A sample tool for testing",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "arg": {"type": "string", "description": "A test argument"}
                    },
                },
            }
        }
        self.call_history = []

    def list_tools(self) -> Dict[str, Any]:
        """Return list of available tools."""
        return {"tools": list(self.tools.values())}

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Mock tool call."""
        self.call_history.append({"tool": tool_name, "arguments": arguments})

        if tool_name not in self.tools:
            return {"error": f"Tool {tool_name} not found"}

        return {
            "result": f"Mock result for {tool_name} with args {arguments}",
            "tool": tool_name,
        }


# ============================================================================
# Fixtures - Temporary Files and Directories
# ============================================================================


@pytest.fixture
def temp_socket_dir():
    """Create temporary directory for socket files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def socket_path(temp_socket_dir):
    """Provide a socket path for testing."""
    return os.path.join(temp_socket_dir, "test-mcp.sock")


@pytest.fixture
def temp_config_dir():
    """Create temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def config_file(temp_config_dir):
    """Create a temporary config file."""
    config_path = os.path.join(temp_config_dir, "config.json")
    config_data = {
        "mcpServers": {
            "time": {"command": "uvx", "args": ["mcp-server-time"]},
            "filesystem": {"command": "uvx", "args": ["mcp-server-filesystem", "/tmp"]},
            "python": {"command": "python", "args": ["-m", "mcp_server_python"]},
        }
    }
    with open(config_path, "w") as f:
        json.dump(config_data, f)
    return config_path


# ============================================================================
# Fixtures - Mock Objects
# ============================================================================


@pytest.fixture
def mock_mcp_server():
    """Create a mock MCP server instance."""
    return MockMCPServer()


@pytest.fixture
def mock_socket():
    """Create a mock socket."""
    with patch("socket.socket") as mock:
        yield mock


@pytest.fixture
def mock_subprocess():
    """Create a mock subprocess."""
    with patch("subprocess.Popen") as mock:
        mock.return_value = MagicMock(
            pid=12345, communicate=MagicMock(return_value=(b"", b"")), returncode=0
        )
        yield mock


@pytest.fixture
def mock_daemon_process():
    """Create a mock daemon process."""
    process = MagicMock()
    process.pid = 88888
    process.is_alive.return_value = True
    process.exitcode = None
    return process


# ============================================================================
# Fixtures - Environment and State
# ============================================================================


@pytest.fixture
def clean_env():
    """Provide a clean environment without existing socket paths."""
    original_env = os.environ.copy()

    # Remove any MCP-related environment variables
    env_keys_to_remove = [k for k in os.environ if "MCP" in k or "SOCKET" in k]
    for key in env_keys_to_remove:
        del os.environ[key]

    yield os.environ.copy()

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def isolated_filesystem(tmp_path):
    """Provide an isolated filesystem for testing."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)


# ============================================================================
# Fixtures - Daemon Setup/Teardown
# ============================================================================


@pytest.fixture
def daemon_socket(socket_path):
    """Create a real Unix socket for daemon testing.

    Note: This creates an actual socket file, so tests using this
    should be marked with @pytest.mark.socket.
    """
    # Clean up if socket exists
    if os.path.exists(socket_path):
        os.remove(socket_path)

    yield socket_path

    # Clean up after test
    if os.path.exists(socket_path):
        os.remove(socket_path)


@pytest.fixture
def running_daemon(daemon_socket):
    """Start a real daemon process for integration testing.

    This fixture:
    1. Starts a daemon process
    2. Waits for it to be ready
    3. Returns the socket path
    4. Stops the daemon after test completes

    Should be marked with @pytest.mark.integration @pytest.mark.socket @pytest.mark.slow
    """
    # Note: Actual daemon startup implementation would go here
    # For now, this is a placeholder that tests can use to ensure
    # daemon is running before their test executes

    # In real implementation:
    # - Start daemon with: subprocess.Popen([...daemon command...])
    # - Wait for socket to be ready
    # - Verify daemon is responsive
    # - Clean up after test

    yield daemon_socket

    # Cleanup
    try:
        # Kill daemon if still running
        pass
    except Exception:
        pass


# ============================================================================
# Fixtures - Argument Parsers
# ============================================================================


@pytest.fixture
def mock_args():
    """Create a mock argparse Namespace for testing."""
    return MagicMock()


@pytest.fixture
def cli_args(mock_args):
    """Create mock CLI arguments."""
    mock_args.command = "list-tools"
    mock_args.server = "test-server"
    mock_args.config = None
    mock_args.socket = "/tmp/mcp-daemon.sock"
    mock_args.no_daemon = False
    mock_args.verbose = False
    mock_args.daemon_timeout = 30
    return mock_args


@pytest.fixture
def daemon_args(mock_args):
    """Create mock daemon arguments."""
    mock_args.command = "daemon"
    mock_args.subcommand = "start"
    mock_args.config = None
    mock_args.socket = "/tmp/mcp-daemon.sock"
    mock_args.verbose = False
    return mock_args


@pytest.fixture
def config_args(mock_args):
    """Create mock config arguments."""
    mock_args.command = "config"
    mock_args.subcommand = "list"
    mock_args.config = None
    mock_args.verbose = False
    return mock_args


# ============================================================================
# Fixtures - Test Data
# ============================================================================


@pytest.fixture
def sample_tools_response():
    """Sample MCP tools list response."""
    return {
        "tools": [
            {
                "name": "list_files",
                "description": "List files in a directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            },
            {
                "name": "read_file",
                "description": "Read a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            },
        ]
    }


@pytest.fixture
def sample_config():
    """Sample MCP configuration."""
    return {
        "mcpServers": {
            "filesystem": {"command": "uvx", "args": ["mcp-server-filesystem", "/tmp"]},
            "time": {"command": "uvx", "args": ["mcp-server-time"]},
            "weather": {"command": "python", "args": ["-m", "mcp_server_weather"]},
        }
    }


@pytest.fixture
def sample_daemon_status():
    """Sample daemon status response."""
    return {
        "status": "running",
        "pid": 12345,
        "socket": "/tmp/mcp-daemon.sock",
        "uptime_seconds": 3600,
        "active_servers": ["filesystem", "time"],
        "memory_usage_mb": 45.5,
    }


# ============================================================================
# Test Utility Functions
# ============================================================================


def assert_socket_available(socket_path: str) -> bool:
    """Check if a socket path is available for use."""
    if os.path.exists(socket_path):
        try:
            os.remove(socket_path)
        except OSError:
            return False
    return True


def wait_for_socket(socket_path: str, timeout: int = 5) -> bool:
    """Wait for a socket to become available."""
    import time

    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(socket_path):
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(socket_path)
                sock.close()
                return True
            except (ConnectionRefusedError, FileNotFoundError):
                pass
        time.sleep(0.1)
    return False


# ============================================================================
# Test Collection Hooks
# ============================================================================


def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on file location."""
    for item in items:
        # Add unit marker to tests in unit/
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        # Add integration marker to tests in integration/
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.slow)
