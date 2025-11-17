"""
MCP Daemon - Persistent MCP server manager

This daemon keeps MCP servers running to avoid process startup overhead.
It uses Unix domain sockets for fast IPC communication.

This module serves as the main entry point for daemon operations.
Core server logic is in daemon_server.py and lifecycle operations are in daemon_lifecycle.py.

This module is internal to cllm-mcp and is accessed via the unified cllm-mcp command.

Usage:
    cllm-mcp daemon start [--socket PATH]
    cllm-mcp daemon stop [--socket PATH]
    cllm-mcp daemon status [--socket PATH]

Example:
    # Start the daemon
    cllm-mcp daemon start

    # Use daemon for fast tool calls
    cllm-mcp call-tool filesystem read-file '{"path": "/tmp/test.txt"}'

    # Check daemon status
    cllm-mcp daemon status

    # Stop the daemon
    cllm-mcp daemon stop
"""

import argparse
import logging
import sys

# Import public APIs from submodules
from .daemon_lifecycle import (
    InitializationResult,
    daemon_start,
    daemon_status,
    daemon_stop,
    initialize_servers_async,
)
from .daemon_server import MCPDaemon, build_server_command

# Export for use in main.py and tests
__all__ = [
    "MCPDaemon",
    "InitializationResult",
    "build_server_command",
    "initialize_servers_async",
    "daemon_start",
    "daemon_stop",
    "daemon_status",
    "main",
]

# Configure logging for daemon operations
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)


def main():
    """Main entry point for MCP daemon."""
    parser = argparse.ArgumentParser(
        description="MCP Daemon - Persistent MCP server manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--socket",
        default=None,
        help="Unix socket path (default: $MCP_DAEMON_SOCKET, $XDG_RUNTIME_DIR/mcp-daemon.sock, or /tmp/mcp-daemon.sock)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # start command
    start_parser = subparsers.add_parser("start", help="Start the daemon")
    start_parser.add_argument(
        "--foreground", action="store_true", help="Run in foreground (don't daemonize)"
    )
    start_parser.add_argument(
        "--no-auto-init",
        action="store_true",
        help="Disable automatic server initialization (ADR-0005)",
    )

    # stop command
    subparsers.add_parser("stop", help="Stop the daemon")

    # status command
    status_parser = subparsers.add_parser("status", help="Check daemon status")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "start":
        daemon_start(args)
    elif args.command == "stop":
        daemon_stop(args)
    elif args.command == "status":
        daemon_status(args)


if __name__ == "__main__":
    main()
