"""
MCP Client - Core client for MCP tool invocation

This module provides the MCP client implementation that allows bash scripts
to invoke MCP tools directly, reducing the need to load tool definitions
into an LLM's context window.

This module is internal to cllm-mcp and is accessed via the unified cllm-mcp command.

Usage:
    cllm-mcp list-tools <server_name>
    cllm-mcp call-tool <server_name> <tool_name> <json_params>
    cllm-mcp interactive <server_name>

Examples:
    # List all available tools from a configured server
    cllm-mcp list-tools filesystem

    # Call a specific tool with parameters
    cllm-mcp call-tool filesystem read-file '{"path": "/tmp/test.txt"}'

    # Interactive mode for exploring tools
    cllm-mcp interactive filesystem
"""

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from typing import Any, Dict, List, Optional

from .socket_utils import DAEMON_TOOL_TIMEOUT, SocketClient


class MCPClient:
    """Simple MCP client that communicates with MCP servers via stdio."""

    def __init__(self, server_command: str):
        """
        Initialize MCP client with a server command.

        Args:
            server_command: Command to start the MCP server (e.g., "npx server-name")
        """
        self.server_command = server_command
        self.process: Optional[subprocess.Popen] = None
        self.message_id = 0

    def start(self):
        """Start the MCP server process."""
        cmd_parts = shlex.split(self.server_command)
        self.process = subprocess.Popen(
            cmd_parts,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # Initialize the connection
        self._send_message(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "mcp-cli", "version": "1.0.0"},
                },
            }
        )

        # Read initialize response
        response = self._read_message()
        if "error" in response:
            raise Exception(f"Initialize error: {response['error']}")

        # Send initialized notification
        self._send_notification(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )

    def stop(self):
        """Stop the MCP server process."""
        if self.process:
            self.process.stdin.close()
            self.process.stdout.close()
            self.process.stderr.close()
            self.process.terminate()
            self.process.wait(timeout=5)

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools from the MCP server.

        Returns:
            List of tool definitions
        """
        self._send_message(
            {"jsonrpc": "2.0", "id": self._next_id(), "method": "tools/list"}
        )

        response = self._read_message()
        if "error" in response:
            raise Exception(f"Error listing tools: {response['error']}")

        return response.get("result", {}).get("tools", [])

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a specific MCP tool with the given arguments.

        Args:
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Tool execution result
        """
        self._send_message(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }
        )

        response = self._read_message()
        if "error" in response:
            raise Exception(f"Error calling tool: {response['error']}")

        return response.get("result", {})

    def _next_id(self) -> int:
        """Generate next message ID."""
        self.message_id += 1
        return self.message_id

    def _send_message(self, message: Dict[str, Any]):
        """Send a JSON-RPC message to the server."""
        if not self.process or not self.process.stdin:
            raise Exception("Server process not started")

        json_str = json.dumps(message)
        self.process.stdin.write(json_str + "\n")
        self.process.stdin.flush()

    def _send_notification(self, notification: Dict[str, Any]):
        """Send a JSON-RPC notification (no response expected)."""
        self._send_message(notification)

    def _read_message(self) -> Dict[str, Any]:
        """Read a JSON-RPC message from the server."""
        if not self.process or not self.process.stdout:
            raise Exception("Server process not started")

        line = self.process.stdout.readline()
        if not line:
            stderr_output = self.process.stderr.read() if self.process.stderr else ""
            raise Exception(f"No response from server. Stderr: {stderr_output}")

        try:
            return json.loads(line)
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {line}. Error: {e}")


# Daemon client functions
def get_server_id(command: str) -> str:
    """Generate a unique ID for a server command."""
    return hashlib.md5(command.encode()).hexdigest()[:12]


def send_daemon_request(
    request: Dict[str, Any], socket_path: str = "/tmp/mcp-daemon.sock"
) -> Dict[str, Any]:
    """Send a request to the daemon and return the response."""
    try:
        client = SocketClient(socket_path, timeout=DAEMON_TOOL_TIMEOUT)
        response = client.send_request(request)
        client.close()
        return response
    except ConnectionError as e:
        raise Exception(str(e))
    except TimeoutError as e:
        raise Exception(f"Daemon request timed out: {e}")
    except ValueError as e:
        raise Exception(f"Invalid daemon response: {e}")
    except Exception as e:
        raise Exception(f"Daemon communication error: {e}")


def daemon_list_tools(
    server_command: str, socket_path: str = "/tmp/mcp-daemon.sock"
) -> List[Dict[str, Any]]:
    """List tools via daemon."""
    server_id = get_server_id(server_command)

    # Ensure server is started
    start_request = {
        "command": "start",
        "server": server_id,
        "server_command": server_command,
    }
    start_response = send_daemon_request(start_request, socket_path)

    if not start_response.get("success"):
        raise Exception(
            f"Failed to start server: {start_response.get('error', 'Unknown error')}"
        )

    # List tools
    list_request = {"command": "list", "server": server_id}
    list_response = send_daemon_request(list_request, socket_path)

    if not list_response.get("success"):
        raise Exception(
            f"Failed to list tools: {list_response.get('error', 'Unknown error')}"
        )

    return list_response.get("tools", [])


def daemon_list_all_tools(socket_path: str = "/tmp/mcp-daemon.sock") -> Dict[str, Any]:
    """List all tools from all running daemon servers."""
    list_request = {"command": "list-all"}
    response = send_daemon_request(list_request, socket_path)

    if not response.get("success"):
        raise Exception(
            f"Failed to list tools: {response.get('error', 'Unknown error')}"
        )

    return response


def daemon_call_tool(
    server_command: str,
    tool_name: str,
    arguments: Dict[str, Any],
    socket_path: str = "/tmp/mcp-daemon.sock",
) -> Any:
    """Call a tool via daemon."""
    server_id = get_server_id(server_command)

    # Ensure server is started
    start_request = {
        "command": "start",
        "server": server_id,
        "server_command": server_command,
    }
    start_response = send_daemon_request(start_request, socket_path)

    if not start_response.get("success"):
        raise Exception(
            f"Failed to start server: {start_response.get('error', 'Unknown error')}"
        )

    # Call tool
    call_request = {
        "command": "call",
        "server": server_id,
        "tool": tool_name,
        "arguments": arguments,
    }
    call_response = send_daemon_request(call_request, socket_path)

    if not call_response.get("success"):
        error = call_response.get("error", "Unknown error")
        if call_response.get("retry"):
            raise Exception(f"Server crashed: {error}. Try again.")
        raise Exception(f"Tool call failed: {error}")

    return call_response.get("result", {})


def generate_placeholder(prop_info: dict) -> any:
    """
    Generate appropriate placeholder for a property based on its type.

    Args:
        prop_info: Property schema info with type and structure

    Returns:
        Placeholder value or structure representing the type
    """
    prop_type = prop_info.get("type", "string")

    if prop_type == "string":
        return "<string>"
    elif prop_type == "number":
        return "<number>"
    elif prop_type == "integer":
        return "<integer>"
    elif prop_type == "boolean":
        return True
    elif prop_type == "array":
        item_placeholder = generate_placeholder(prop_info.get("items", {}))
        return [item_placeholder, item_placeholder]
    elif prop_type == "object":
        # For nested objects, show the structure with type placeholders
        nested_props = prop_info.get("properties", {})
        if nested_props:
            nested_example = {}
            for key, val in nested_props.items():
                nested_example[key] = generate_placeholder(val)
            return nested_example
        else:
            return {"<string>": "<string>"}
    else:
        return f"<{prop_type}>"


def generate_json_example(schema: dict) -> dict:
    """
    Generate a JSON example object with type-based placeholders from schema.

    Args:
        schema: The tool's inputSchema

    Returns:
        Dict with placeholder values based on type
    """
    if not schema:
        return {}

    properties = schema.get("properties", {})
    if not properties:
        return {}

    example = {}
    for prop_name, prop_info in properties.items():
        example[prop_name] = generate_placeholder(prop_info)

    return example


def cmd_list_tools(args):
    """Command to list all available tools."""
    if args.use_daemon:
        # Use daemon mode
        try:
            tools = daemon_list_tools(args.server_command, args.daemon_socket)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Direct mode
        client = MCPClient(args.server_command)
        try:
            client.start()
            tools = client.list_tools()
        finally:
            client.stop()

    # Display tools
    if args.json:
        print(json.dumps(tools, indent=2))
    else:
        # Markdown format
        print(f"# Available tools from: {args.server_command}\n")
        for tool in tools:
            print(f"## {tool['name']}\n")
            if "description" in tool:
                print(f"{tool['description']}\n")
            if "inputSchema" in tool:
                schema = tool["inputSchema"]
                # Generate and show example
                example = generate_json_example(schema)
                # Use server_name if available (from config), otherwise use server_command
                server_ref = getattr(args, "server_name", args.server_command)
                print("### Example\n")
                print("```bash")
                if example:
                    example_json = json.dumps(example)
                    print(
                        f"cllm-mcp call-tool {server_ref} {tool['name']} '{example_json}'"
                    )
                else:
                    # For tools with no parameters
                    print(f"cllm-mcp call-tool {server_ref} {tool['name']} '{{}}'")
                print("```\n")


def cmd_call_tool(args):
    """Command to call a specific tool."""
    # Parse JSON parameters
    try:
        params = json.loads(args.parameters)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON parameters: {e}", file=sys.stderr)
        sys.exit(1)

    if args.use_daemon:
        # Use daemon mode
        try:
            result = daemon_call_tool(
                args.server_command, args.tool_name, params, args.daemon_socket
            )
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Direct mode
        client = MCPClient(args.server_command)
        try:
            client.start()
            result = client.call_tool(args.tool_name, params)
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            client.stop()


def cmd_interactive(args):
    """Interactive mode for exploring and calling tools."""
    client = MCPClient(args.server_command)
    try:
        client.start()
        print(f"Connected to MCP server: {args.server_command}")
        print("Commands: list, call <tool_name> <json_params>, quit\n")

        while True:
            try:
                command = input("> ").strip()

                if not command:
                    continue

                if command == "quit" or command == "exit":
                    break

                if command == "list":
                    tools = client.list_tools()
                    print("\nAvailable tools:")
                    for tool in tools:
                        print(f"  • {tool['name']}")
                        if "description" in tool:
                            print(f"    {tool['description']}")
                    print()

                elif command.startswith("call "):
                    parts = command.split(maxsplit=2)
                    if len(parts) < 3:
                        print("Usage: call <tool_name> <json_params>")
                        continue

                    tool_name = parts[1]
                    try:
                        params = json.loads(parts[2])
                    except json.JSONDecodeError as e:
                        print(f"Error: Invalid JSON: {e}")
                        continue

                    result = client.call_tool(tool_name, params)
                    print(json.dumps(result, indent=2))
                    print()

                else:
                    print(
                        "Unknown command. Available: list, call <tool_name> <json_params>, quit"
                    )

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except Exception as e:
                print(f"Error: {e}")

    finally:
        client.stop()


def main():
    """Main entry point for the MCP CLI."""
    parser = argparse.ArgumentParser(
        description="MCP CLI - Make MCP tool calls without an LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # list-tools command
    list_parser = subparsers.add_parser("list-tools", help="List all available tools")
    list_parser.add_argument("server_command", help="Command to start MCP server")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    list_parser.add_argument(
        "--use-daemon",
        action="store_true",
        help="Use daemon mode for faster repeated calls",
    )
    list_parser.add_argument(
        "--daemon-socket",
        default="/tmp/mcp-daemon.sock",
        help="Daemon socket path (default: /tmp/mcp-daemon.sock)",
    )

    # call-tool command
    call_parser = subparsers.add_parser("call-tool", help="Call a specific tool")
    call_parser.add_argument("server_command", help="Command to start MCP server")
    call_parser.add_argument("tool_name", help="Name of the tool to call")
    call_parser.add_argument("parameters", help="JSON string of tool parameters")
    call_parser.add_argument(
        "--use-daemon",
        action="store_true",
        help="Use daemon mode for faster repeated calls",
    )
    call_parser.add_argument(
        "--daemon-socket",
        default="/tmp/mcp-daemon.sock",
        help="Daemon socket path (default: /tmp/mcp-daemon.sock)",
    )

    # interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Interactive mode")
    interactive_parser.add_argument(
        "server_command", help="Command to start MCP server"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "list-tools":
        cmd_list_tools(args)
    elif args.command == "call-tool":
        cmd_call_tool(args)
    elif args.command == "interactive":
        cmd_interactive(args)


if __name__ == "__main__":
    main()
