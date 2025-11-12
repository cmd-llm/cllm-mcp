"""
Daemon detection and utility functions for ADR-0003.

Provides smart daemon detection with graceful fallback to direct mode.
"""

import os
import sys
from typing import Optional

from .socket_utils import (
    is_daemon_available,
)


def should_use_daemon(
    socket_path: str,
    no_daemon: bool = False,
    timeout: float = 1.0,
    verbose: bool = False,
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
            print(
                "[mode] Using direct mode (daemon explicitly disabled)", file=sys.stderr
            )
        return False

    if is_daemon_available(socket_path, timeout, verbose):
        if verbose:
            print("[mode] Using daemon mode (auto-detected)", file=sys.stderr)
        return True

    if verbose:
        print(
            "[mode] Using direct mode (daemon not available, fallback)", file=sys.stderr
        )
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
