"""
Unified command dispatcher for cllm-mcp (ADR-0003).

Routes commands to appropriate handlers with smart daemon detection.
Supports:
  - list-tools: List available MCP tools
  - call-tool: Execute a specific MCP tool
  - interactive: Interactive REPL for exploring tools
  - daemon: Manage persistent daemon (start, stop, status, restart)
  - config: Manage configurations (list, validate)
"""

import sys
import argparse
import os

# Import handlers from existing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mcp_cli import cmd_list_tools, cmd_call_tool, cmd_interactive
from mcp_daemon import daemon_start, daemon_stop, daemon_status
from cllm_mcp.daemon_utils import should_use_daemon, get_daemon_socket_path
from cllm_mcp.config import cmd_config_list, cmd_config_validate


def create_parser():
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        prog="cllm-mcp",
        description="Unified Model Context Protocol CLI with daemon support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List tools from a server (auto-uses daemon if available)
  cllm-mcp list-tools "python -m server"

  # Call a tool with arguments
  cllm-mcp call-tool "python -m server" "tool-name" '{"param": "value"}'

  # Start persistent daemon for performance
  cllm-mcp daemon start

  # Check daemon status
  cllm-mcp daemon status

  # List configured servers
  cllm-mcp config list

  # Validate configuration
  cllm-mcp config validate
        """
    )

    # Global options
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to MCP configuration file (default: auto-discover)"
    )
    parser.add_argument(
        "--socket",
        type=str,
        default=None,
        help="Path to daemon socket (default: /tmp/mcp-daemon.sock)"
    )
    parser.add_argument(
        "--no-daemon",
        action="store_true",
        help="Force direct mode, don't use daemon even if available"
    )
    parser.add_argument(
        "--daemon-timeout",
        type=float,
        default=1.0,
        help="Daemon detection timeout in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output including mode selection"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list-tools command
    list_tools_parser = subparsers.add_parser(
        "list-tools",
        help="List available tools from MCP server"
    )
    list_tools_parser.add_argument(
        "server_command",
        help="Command to start the MCP server"
    )
    list_tools_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    list_tools_parser.set_defaults(func=handle_list_tools)

    # call-tool command
    call_tool_parser = subparsers.add_parser(
        "call-tool",
        help="Execute a specific MCP tool"
    )
    call_tool_parser.add_argument(
        "server_command",
        help="Command to start the MCP server"
    )
    call_tool_parser.add_argument(
        "tool_name",
        help="Name of the tool to call"
    )
    call_tool_parser.add_argument(
        "parameters",
        help="JSON parameters for the tool"
    )
    call_tool_parser.set_defaults(func=handle_call_tool)

    # interactive command
    interactive_parser = subparsers.add_parser(
        "interactive",
        help="Interactive REPL for exploring and calling tools"
    )
    interactive_parser.add_argument(
        "server_command",
        help="Command to start the MCP server"
    )
    interactive_parser.set_defaults(func=handle_interactive)

    # daemon subcommand
    daemon_parser = subparsers.add_parser(
        "daemon",
        help="Manage MCP daemon"
    )
    daemon_subparsers = daemon_parser.add_subparsers(
        dest="daemon_command",
        help="Daemon operation"
    )

    # daemon start
    daemon_subparsers.add_parser("start", help="Start daemon")
    # daemon stop
    daemon_subparsers.add_parser("stop", help="Stop daemon")
    # daemon status
    daemon_subparsers.add_parser("status", help="Show daemon status")
    # daemon restart
    daemon_subparsers.add_parser("restart", help="Restart daemon")

    daemon_parser.set_defaults(func=handle_daemon)

    # config subcommand
    config_parser = subparsers.add_parser(
        "config",
        help="Manage MCP server configurations"
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_command",
        help="Configuration operation"
    )

    # config list
    config_list_parser = config_subparsers.add_parser(
        "list",
        help="List configured servers"
    )
    config_list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    config_list_parser.set_defaults(func=handle_config)

    # config validate
    config_subparsers.add_parser(
        "validate",
        help="Validate configuration file"
    )
    config_parser.set_defaults(func=handle_config)

    return parser


def handle_list_tools(args):
    """Handle list-tools command with daemon detection."""
    socket_path = get_daemon_socket_path(args.socket)
    use_daemon = should_use_daemon(
        socket_path,
        args.no_daemon,
        args.daemon_timeout,
        args.verbose
    )

    # Set args for the handler
    args.use_daemon = use_daemon
    args.daemon_socket = socket_path
    args.json = getattr(args, 'json', False)

    return cmd_list_tools(args)


def handle_call_tool(args):
    """Handle call-tool command with daemon detection."""
    socket_path = get_daemon_socket_path(args.socket)
    use_daemon = should_use_daemon(
        socket_path,
        args.no_daemon,
        args.daemon_timeout,
        args.verbose
    )

    # Set args for the handler
    args.use_daemon = use_daemon
    args.daemon_socket = socket_path

    return cmd_call_tool(args)


def handle_interactive(args):
    """Handle interactive command (always direct mode)."""
    # Interactive mode doesn't use daemon
    args.use_daemon = False
    return cmd_interactive(args)


def handle_daemon(args):
    """Handle daemon subcommands."""
    socket_path = get_daemon_socket_path(args.socket)

    if args.daemon_command == "start":
        # Create args object for daemon handler
        daemon_args = argparse.Namespace(daemon_socket=socket_path)
        return daemon_start(daemon_args)
    elif args.daemon_command == "stop":
        daemon_args = argparse.Namespace(daemon_socket=socket_path)
        return daemon_stop(daemon_args)
    elif args.daemon_command == "status":
        daemon_args = argparse.Namespace(daemon_socket=socket_path)
        return daemon_status(daemon_args)
    elif args.daemon_command == "restart":
        # Restart = stop + start
        daemon_args = argparse.Namespace(daemon_socket=socket_path)
        print("Stopping daemon...")
        try:
            daemon_stop(daemon_args)
        except Exception:
            pass  # Ignore if not running
        print("Starting daemon...")
        return daemon_start(daemon_args)
    else:
        print("Error: Unknown daemon command", file=sys.stderr)
        sys.exit(1)


def handle_config(args):
    """Handle config subcommands."""
    if args.config_command == "list":
        return cmd_config_list(args)
    elif args.config_command == "validate":
        return cmd_config_validate(args)
    else:
        print("Error: Unknown config command", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for cllm-mcp."""
    parser = create_parser()
    args = parser.parse_args()

    # If no command, show help
    if not hasattr(args, 'func'):
        parser.print_help()
        sys.exit(1)

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nCancelled", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
