"""
Daemon detection and utility functions for ADR-0003.

Provides smart daemon detection with graceful fallback to direct mode.
"""

import os
import socket
import json
import sys
from typing import Optional


def is_daemon_available(socket_path: str, timeout: float = 1.0, verbose: bool = False) -> bool:
    """
    Check if the daemon is available and responsive.

    Args:
        socket_path: Path to the daemon socket
        timeout: Connection timeout in seconds
        verbose: Print status messages

    Returns:
        True if daemon is available and responsive, False otherwise
    """
    # Check if socket file exists
    if not os.path.exists(socket_path):
        if verbose:
            print(f"[daemon] Socket not found at {socket_path}", file=sys.stderr)
        return False

    try:
        # Attempt to connect and send a ping
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(socket_path)

        # Send a simple status request
        ping_request = {"command": "status"}
        sock.sendall(json.dumps(ping_request).encode() + b"\n")

        # Wait for response
        try:
            response_data = sock.recv(4096)
            sock.close()

            if response_data:
                # Parse to verify it's valid JSON
                json.loads(response_data.decode().strip())
                if verbose:
                    print("[daemon] Daemon is available and responsive", file=sys.stderr)
                return True
        except socket.timeout:
            if verbose:
                print("[daemon] Daemon connection timed out", file=sys.stderr)
            sock.close()
            return False
        except json.JSONDecodeError:
            if verbose:
                print("[daemon] Invalid response from daemon", file=sys.stderr)
            sock.close()
            return False

    except (FileNotFoundError, ConnectionRefusedError, ConnectionError) as e:
        if verbose:
            print(f"[daemon] Cannot connect to daemon: {e}", file=sys.stderr)
        return False
    except socket.timeout:
        if verbose:
            print("[daemon] Daemon socket connection timed out", file=sys.stderr)
        return False
    except Exception as e:
        if verbose:
            print(f"[daemon] Unexpected error checking daemon: {e}", file=sys.stderr)
        return False


def should_use_daemon(
    socket_path: str,
    no_daemon: bool = False,
    timeout: float = 1.0,
    verbose: bool = False
) -> bool:
    """
    Determine if daemon should be used for tool execution.

    Returns True if:
    1. no_daemon flag is False (not explicitly disabled)
    2. Daemon socket exists and is responsive

    Args:
        socket_path: Path to the daemon socket
        no_daemon: If True, force direct mode
        timeout: Connection timeout for daemon check
        verbose: Print mode selection

    Returns:
        True if daemon should be used, False if direct mode should be used
    """
    if no_daemon:
        if verbose:
            print("[mode] Using direct mode (daemon explicitly disabled)", file=sys.stderr)
        return False

    if is_daemon_available(socket_path, timeout, verbose):
        if verbose:
            print("[mode] Using daemon mode (auto-detected)", file=sys.stderr)
        return True

    if verbose:
        print("[mode] Using direct mode (daemon not available, fallback)", file=sys.stderr)
    return False


def get_daemon_socket_path(socket_path: Optional[str] = None) -> str:
    """
    Get the daemon socket path from explicit arg, env var, or default.

    Priority: explicit arg > environment variable > default

    Args:
        socket_path: Explicit socket path argument

    Returns:
        The daemon socket path to use
    """
    if socket_path:
        return socket_path

    env_path = os.environ.get("MCP_DAEMON_SOCKET")
    if env_path:
        return env_path

    return "/tmp/mcp-daemon.sock"
