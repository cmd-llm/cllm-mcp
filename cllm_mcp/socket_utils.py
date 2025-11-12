"""
Unified socket communication utilities for MCP daemon/client.

Provides SocketClient class for consistent daemon communication across the codebase.
Handles socket creation, communication, error handling, and timeout management.
"""

import json
import socket
import sys
from typing import Dict, Any, Optional

# Standard timeouts for different operations
DAEMON_CHECK_TIMEOUT = 1.0  # Quick availability check
DAEMON_TOOL_TIMEOUT = 30.0  # Extended timeout for tool execution
DAEMON_CTRL_TIMEOUT = 5.0   # Control commands (stop, status)

# Default socket path
DEFAULT_SOCKET_PATH = "/tmp/mcp-daemon.sock"


class SocketClient:
    """
    Unified socket client for daemon communication.

    Handles all socket operations with consistent error handling,
    timeout management, and resource cleanup.
    """

    def __init__(self, socket_path: str = DEFAULT_SOCKET_PATH, timeout: float = DAEMON_TOOL_TIMEOUT):
        """
        Initialize socket client.

        Args:
            socket_path: Path to daemon socket (default: /tmp/mcp-daemon.sock)
            timeout: Communication timeout in seconds (default: 30.0)
        """
        self.socket_path = socket_path
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """
        Connect to daemon socket.

        Raises:
            ConnectionError: If daemon is not running or connection fails
            TimeoutError: If connection times out
        """
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect(self.socket_path)
        except FileNotFoundError:
            raise ConnectionError(
                f"Daemon not running. Start with: cllm-mcp daemon start"
            )
        except ConnectionRefusedError:
            raise ConnectionError(
                f"Cannot connect to daemon at {self.socket_path}. "
                f"Start with: cllm-mcp daemon start"
            )
        except socket.timeout:
            raise TimeoutError(
                f"Daemon connection timed out ({self.timeout}s)"
            )

    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send request to daemon and receive response.

        Args:
            request: Request dictionary to send

        Returns:
            Response dictionary from daemon

        Raises:
            ConnectionError: If not connected to daemon
            TimeoutError: If request times out
            ValueError: If response is invalid JSON
        """
        if not self.sock:
            self.connect()

        try:
            # Send request as JSON with newline delimiter
            self.sock.sendall(json.dumps(request).encode() + b"\n")

            # Receive response
            data = self._receive_message()
            return json.loads(data.decode().strip())

        except socket.timeout:
            self.close()
            raise TimeoutError(f"Daemon request timed out ({self.timeout}s)")
        except json.JSONDecodeError as e:
            self.close()
            raise ValueError(f"Invalid JSON response from daemon: {e}")
        except Exception as e:
            self.close()
            raise

    def _receive_message(self) -> bytes:
        """
        Receive complete message from socket (up to first newline).

        Returns:
            Message bytes

        Raises:
            ConnectionError: If connection closes before receiving data
        """
        data = b""
        while True:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    raise ConnectionError("Connection closed by daemon")
                data += chunk
                if b"\n" in data:
                    return data.split(b"\n")[0] + b"\n"
            except socket.timeout:
                # Re-raise timeout to be handled by caller
                raise

    def close(self) -> None:
        """Close socket connection."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass  # Ignore errors on close
            self.sock = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def is_daemon_available(socket_path: str = DEFAULT_SOCKET_PATH,
                       timeout: float = DAEMON_CHECK_TIMEOUT,
                       verbose: bool = False) -> bool:
    """
    Check if daemon is available and responsive.

    Args:
        socket_path: Path to daemon socket
        timeout: Connection timeout in seconds
        verbose: Print status messages to stderr

    Returns:
        True if daemon is available, False otherwise
    """
    try:
        client = SocketClient(socket_path, timeout)
        response = client.send_request({"command": "status"})
        client.close()

        if response:
            if verbose:
                print("[daemon] Daemon is available and responsive", file=sys.stderr)
            return True
        return False

    except ConnectionError as e:
        if verbose:
            print(f"[daemon] Cannot connect to daemon: {e}", file=sys.stderr)
        return False
    except TimeoutError:
        if verbose:
            print("[daemon] Daemon connection timed out", file=sys.stderr)
        return False
    except (ValueError, json.JSONDecodeError):
        if verbose:
            print("[daemon] Invalid response from daemon", file=sys.stderr)
        return False
    except Exception as e:
        if verbose:
            print(f"[daemon] Unexpected error checking daemon: {e}", file=sys.stderr)
        return False


def get_daemon_config(socket_path: str = DEFAULT_SOCKET_PATH,
                      timeout: float = DAEMON_CTRL_TIMEOUT,
                      verbose: bool = False) -> Optional[Dict[str, Any]]:
    """
    Get configuration from daemon (list of available servers).

    Args:
        socket_path: Path to daemon socket
        timeout: Communication timeout in seconds
        verbose: Print status messages to stderr

    Returns:
        Configuration dict with available servers, or None if error
    """
    try:
        client = SocketClient(socket_path, timeout)
        response = client.send_request({"command": "get-config"})
        client.close()

        if response.get("success"):
            return response
        else:
            if verbose:
                print(f"[daemon] {response.get('error', 'Unknown error')}", file=sys.stderr)
            return None

    except ConnectionError as e:
        if verbose:
            print(f"[daemon] Cannot connect to daemon: {e}", file=sys.stderr)
        return None
    except TimeoutError:
        if verbose:
            print("[daemon] Daemon request timed out", file=sys.stderr)
        return None
    except (ValueError, json.JSONDecodeError):
        if verbose:
            print("[daemon] Invalid response from daemon", file=sys.stderr)
        return None
    except Exception as e:
        if verbose:
            print(f"[daemon] Error getting config from daemon: {e}", file=sys.stderr)
        return None
