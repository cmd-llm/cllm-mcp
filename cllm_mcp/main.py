"""
Unified command dispatcher for cllm-mcp (ADR-0003, ADR-0004).

Routes commands to appropriate handlers with smart daemon detection.
Supports:
  - list-tools: List available MCP tools
  - call-tool: Execute a specific MCP tool
  - interactive: Interactive REPL for exploring tools
  - daemon: Manage persistent daemon (start, stop, status, restart)
  - config: Manage configurations (list, validate, show, migrate)

Configuration follows CLLM-style precedence (ADR-0004):
  1. ~/.cllm/mcp-config.json (global defaults)
  2. ./.cllm/mcp-config.json (project-specific)
  3. ./mcp-config.json (current directory)
  4. CLLM_MCP_CONFIG environment variable
  5. --config CLI argument (highest priority)
"""

import argparse
import os
import sys
from typing import Any, Dict

# Import handlers from existing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cllm_mcp.config import (
    ConfigError,
    cmd_config_list,
    cmd_config_migrate,
    cmd_config_show,
    cmd_config_validate,
    find_config_file,
    load_config,
    resolve_server_ref,
    validate_config,
)
from cllm_mcp.daemon_utils import get_daemon_socket_path, should_use_daemon
from cllm_mcp.socket_utils import get_daemon_config
from mcp_cli import (
    cmd_call_tool,
    cmd_interactive,
    cmd_list_tools,
    daemon_list_all_tools,
    generate_json_example,
)
from mcp_daemon import daemon_start, daemon_status, daemon_stop


def _display_all_daemon_tools(
    result: Dict[str, Any], json_output: bool = False
) -> None:
    """Display all tools from all daemon servers in markdown format with examples."""
    import json as json_module

    if json_output:
        print(json_module.dumps(result, indent=2))
    else:
        servers = result.get("servers", {})
        server_count = result.get("server_count", 0)
        total_tools = result.get("total_tools", 0)

        if server_count == 0:
            print("No active servers in daemon")
            return

        print(
            f"# Available tools from {server_count} active daemon server(s) ({total_tools} total tools)\n"
        )

        for server_id, server_data in servers.items():
            tools = server_data.get("tools", [])
            print(f"## Server: {server_id}\n")

            for tool in tools:
                tool_name = tool.get("name", "unknown")
                print(f"### {tool_name}\n")

                if tool.get("description"):
                    print(f"{tool['description']}\n")

                # Generate and show example
                input_schema = tool.get("inputSchema", {})
                example = generate_json_example(input_schema)
                example_json = json_module.dumps(example)

                print("#### Example\n")
                print("```bash")
                print(
                    f"cllm-mcp call-tool {server_id} {tool_name} '{example_json}'"
                )
                print("```\n")


def create_parser():
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        prog="cllm-mcp",
        description="Unified Model Context Protocol CLI with daemon support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List tools by server name (from config)
  cllm-mcp list-tools time

  # List tools by full command (direct mode)
  cllm-mcp list-tools "uvx mcp-server-time"

  # Call a tool using server name from config
  cllm-mcp call-tool time "get_current_time" '{"timezone": "America/New_York"}'

  # Call a tool using full command
  cllm-mcp call-tool "uvx mcp-server-time" "get_current_time" '{"timezone": "America/New_York"}'

  # Start persistent daemon for performance
  cllm-mcp daemon start

  # Check daemon status
  cllm-mcp daemon status

  # List configured servers
  cllm-mcp config list

  # Validate configuration
  cllm-mcp config validate
        """,
    )

    # Global options
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to MCP configuration file (default: auto-discover)",
    )
    parser.add_argument(
        "--socket",
        type=str,
        default=None,
        help="Path to daemon socket (default: /tmp/mcp-daemon.sock)",
    )
    parser.add_argument(
        "--no-daemon",
        action="store_true",
        help="Force direct mode, don't use daemon even if available",
    )
    parser.add_argument(
        "--daemon-timeout",
        type=float,
        default=1.0,
        help="Daemon detection timeout in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output including mode selection",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list-tools command
    list_tools_parser = subparsers.add_parser(
        "list-tools", help="List available tools from MCP server or all daemon servers"
    )
    list_tools_parser.add_argument(
        "server_command",
        nargs="?",
        default=None,
        help="Command or name to start the MCP server (optional: omit to list all daemon tools)",
    )
    list_tools_parser.add_argument("--json", action="store_true", help="Output as JSON")
    list_tools_parser.set_defaults(func=handle_list_tools)

    # call-tool command
    call_tool_parser = subparsers.add_parser(
        "call-tool", help="Execute a specific MCP tool"
    )
    call_tool_parser.add_argument(
        "server_command", help="Command to start the MCP server"
    )
    call_tool_parser.add_argument("tool_name", help="Name of the tool to call")
    call_tool_parser.add_argument("parameters", help="JSON parameters for the tool")
    call_tool_parser.set_defaults(func=handle_call_tool)

    # interactive command
    interactive_parser = subparsers.add_parser(
        "interactive", help="Interactive REPL for exploring and calling tools"
    )
    interactive_parser.add_argument(
        "server_command", help="Command to start the MCP server"
    )
    interactive_parser.set_defaults(func=handle_interactive)

    # daemon subcommand
    daemon_parser = subparsers.add_parser("daemon", help="Manage MCP daemon")
    daemon_subparsers = daemon_parser.add_subparsers(
        dest="daemon_command", help="Daemon operation"
    )

    # daemon start
    start_parser = daemon_subparsers.add_parser("start", help="Start daemon")
    start_parser.add_argument(
        "--foreground", action="store_true", help="Run daemon in foreground"
    )
    # daemon stop
    daemon_subparsers.add_parser("stop", help="Stop daemon")
    # daemon status
    daemon_subparsers.add_parser("status", help="Show daemon status")
    # daemon restart
    daemon_subparsers.add_parser("restart", help="Restart daemon")

    daemon_parser.set_defaults(func=handle_daemon)

    # config subcommand
    config_parser = subparsers.add_parser(
        "config", help="Manage MCP server configurations"
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_command", help="Configuration operation"
    )

    # config list
    config_list_parser = config_subparsers.add_parser(
        "list", help="List configured servers"
    )
    config_list_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    config_list_parser.set_defaults(func=handle_config)

    # config validate
    config_subparsers.add_parser("validate", help="Validate configuration file")

    # config show
    config_subparsers.add_parser(
        "show", help="Show which configuration file is being used and its status"
    )

    # config migrate
    config_subparsers.add_parser(
        "migrate", help="Migrate old config files to new .cllm folder structure"
    )

    config_parser.set_defaults(func=handle_config)

    return parser


def handle_list_tools(args):
    """Handle list-tools command with daemon detection and config resolution."""
    # If no server_command specified, list all tools from all running daemon servers
    if args.server_command is None:
        socket_path = get_daemon_socket_path(args.socket)
        is_daemon_available = should_use_daemon(
            socket_path, args.no_daemon, args.daemon_timeout, args.verbose
        )

        if not is_daemon_available:
            print(
                "Error: No server specified and daemon is not available",
                file=sys.stderr,
            )
            print(
                "Usage: cllm-mcp list-tools [server_name_or_command]", file=sys.stderr
            )
            sys.exit(1)

        # List all running tools from all daemon servers
        try:
            result = daemon_list_all_tools(socket_path)
            return _display_all_daemon_tools(result, args.json)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Try to load config and resolve server reference
    config = None
    try:
        if args.config:
            config_path = args.config
        else:
            config_path, _ = find_config_file(verbose=args.verbose)
        if config_path:
            config = load_config(str(config_path))
            errors = validate_config(config)
            if errors:
                if args.verbose:
                    print(
                        "[config] Configuration is invalid, ignoring", file=sys.stderr
                    )
                config = None
    except ConfigError:
        if args.verbose:
            print("[config] Could not load configuration", file=sys.stderr)
        config = None

    # Detect and configure daemon early to potentially get server names from daemon config
    socket_path = get_daemon_socket_path(args.socket)
    use_daemon = should_use_daemon(
        socket_path, args.no_daemon, args.daemon_timeout, args.verbose
    )

    # If no local config found but daemon is available, try to get config from daemon
    if not config and use_daemon:
        daemon_config = get_daemon_config(socket_path, verbose=args.verbose)
        if daemon_config and daemon_config.get("servers"):
            # Build a config dict from daemon's servers for resolution
            config = {"mcpServers": daemon_config.get("servers", {})}

    # Resolve server reference (could be a name or a command)
    resolved_command, server_name = resolve_server_ref(args.server_command, config)

    if args.verbose and server_name:
        print(f"[config] Resolved server '{server_name}' to: {resolved_command}")

    # Set the resolved command and preserve the server name
    args.server_command = resolved_command
    args.server_name = server_name or args.server_command  # Use name if available, otherwise use command

    # Set args for the handler
    args.use_daemon = use_daemon
    args.daemon_socket = socket_path
    args.json = getattr(args, "json", False)

    return cmd_list_tools(args)


def handle_call_tool(args):
    """Handle call-tool command with daemon detection and config resolution."""
    # Try to load config and resolve server reference
    config = None
    try:
        if args.config:
            config_path = args.config
        else:
            config_path, _ = find_config_file(verbose=args.verbose)
        if config_path:
            config = load_config(str(config_path))
            errors = validate_config(config)
            if errors:
                if args.verbose:
                    print(
                        "[config] Configuration is invalid, ignoring", file=sys.stderr
                    )
                config = None
    except ConfigError:
        if args.verbose:
            print("[config] Could not load configuration", file=sys.stderr)
        config = None

    # Detect and configure daemon early to potentially get server names from daemon config
    socket_path = get_daemon_socket_path(args.socket)
    use_daemon = should_use_daemon(
        socket_path, args.no_daemon, args.daemon_timeout, args.verbose
    )

    # If no local config found but daemon is available, try to get config from daemon
    if not config and use_daemon:
        daemon_config = get_daemon_config(socket_path, verbose=args.verbose)
        if daemon_config and daemon_config.get("servers"):
            # Build a config dict from daemon's servers for resolution
            config = {"mcpServers": daemon_config.get("servers", {})}

    # Resolve server reference (could be a name or a command)
    resolved_command, server_name = resolve_server_ref(args.server_command, config)

    if args.verbose and server_name:
        print(f"[config] Resolved server '{server_name}' to: {resolved_command}")

    # Set the resolved command
    args.server_command = resolved_command

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
        daemon_args = argparse.Namespace(
            socket=socket_path,
            config=args.config,
            foreground=getattr(args, "foreground", False),
        )
        return daemon_start(daemon_args)
    elif args.daemon_command == "stop":
        daemon_args = argparse.Namespace(socket=socket_path)
        return daemon_stop(daemon_args)
    elif args.daemon_command == "status":
        daemon_args = argparse.Namespace(socket=socket_path)
        return daemon_status(daemon_args)
    elif args.daemon_command == "restart":
        # Restart = stop + start
        daemon_args = argparse.Namespace(socket=socket_path)
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
    elif args.config_command == "show":
        return cmd_config_show(args)
    elif args.config_command == "migrate":
        return cmd_config_migrate(args)
    else:
        print("Error: Unknown config command", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for cllm-mcp."""
    parser = create_parser()
    args = parser.parse_args()

    # If no command, show help
    if not hasattr(args, "func"):
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
