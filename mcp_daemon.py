#!/usr/bin/env python3
"""
MCP Daemon - Persistent MCP server manager

This daemon keeps MCP servers running to avoid process startup overhead.
It uses Unix domain sockets for fast IPC communication.

Usage:
    mcp_daemon.py start [--socket PATH]
    mcp_daemon.py stop [--socket PATH]
    mcp_daemon.py status [--socket PATH]

Example:
    # Start the daemon
    ./mcp_daemon.py start

    # Use mcp_cli.py with daemon
    ./mcp_cli.py call-tool --use-daemon "npx -y @modelcontextprotocol/server-filesystem /tmp" \
        read_file '{"path": "/tmp/test.txt"}'

    # Stop the daemon
    ./mcp_daemon.py stop
"""

import socket
import json
import threading
import sys
import os
import signal
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from mcp_cli import MCPClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from cllm_mcp.socket_utils import SocketClient, DAEMON_CTRL_TIMEOUT
from cllm_mcp.config import find_config_file, load_config, validate_config


class MCPDaemon:
    """Daemon that manages multiple MCP server processes."""

    def __init__(self, socket_path: str = "/tmp/mcp-daemon.sock", config_path: Optional[str] = None):
        self.socket_path = socket_path
        self.servers: Dict[str, MCPClient] = {}
        self.lock = threading.Lock()
        self.running = True

        # Load configuration for server discovery
        self.config = None
        self.config_path = None
        try:
            # Try explicit path first, then auto-discover
            config_file = config_path or find_config_file()
            if config_file:
                self.config = load_config(str(config_file))
                errors = validate_config(self.config)
                if not errors:
                    self.config_path = str(config_file)
                else:
                    self.config = None  # Invalid config, ignore it
        except Exception:
            pass  # Gracefully ignore config loading errors

    def start_server(self, name: str, command: str) -> Dict[str, Any]:
        """Start and cache an MCP server."""
        with self.lock:
            if name in self.servers:
                return {"success": True, "message": "Server already running"}

            try:
                client = MCPClient(command)
                client.start()
                self.servers[name] = client
                return {"success": True, "message": f"Server '{name}' started"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def call_tool(self, server: str, tool: str, args: dict) -> Dict[str, Any]:
        """Call a tool on a running server."""
        with self.lock:
            if server not in self.servers:
                return {"error": f"Server '{server}' not running. Start it first."}

            try:
                result = self.servers[server].call_tool(tool, args)
                return {"success": True, "result": result}
            except Exception as e:
                # Server may have crashed, remove it
                try:
                    self.servers[server].stop()
                except (Exception, OSError):
                    pass  # Ignore errors during cleanup
                del self.servers[server]
                return {"success": False, "error": str(e), "retry": True}

    def list_tools(self, server: str) -> Dict[str, Any]:
        """List tools from a running server."""
        with self.lock:
            if server not in self.servers:
                return {"error": f"Server '{server}' not running. Start it first."}

            try:
                tools = self.servers[server].list_tools()
                return {"success": True, "tools": tools}
            except Exception as e:
                # Server may have crashed, remove it
                try:
                    self.servers[server].stop()
                except (Exception, OSError):
                    pass  # Ignore errors during cleanup
                del self.servers[server]
                return {"success": False, "error": str(e)}

    def list_all_tools(self) -> Dict[str, Any]:
        """List tools from all running servers."""
        with self.lock:
            all_tools_by_server = {}

            for server_id, client in self.servers.items():
                try:
                    tools = client.list_tools()
                    all_tools_by_server[server_id] = {
                        "tools": tools,
                        "tool_count": len(tools)
                    }
                except Exception as e:
                    # Server may have crashed, remove it
                    try:
                        client.stop()
                    except (Exception, OSError):
                        pass  # Ignore errors during cleanup
                    del self.servers[server_id]

            return {
                "success": True,
                "servers": all_tools_by_server,
                "server_count": len(all_tools_by_server),
                "total_tools": sum(s.get("tool_count", 0) for s in all_tools_by_server.values())
            }

    def stop_server(self, name: str) -> Dict[str, Any]:
        """Stop a specific server."""
        with self.lock:
            if name not in self.servers:
                return {"success": True, "message": f"Server '{name}' not running"}

            try:
                self.servers[name].stop()
                del self.servers[name]
                return {"success": True, "message": f"Server '{name}' stopped"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def stop_all(self):
        """Stop all servers."""
        with self.lock:
            for name, client in list(self.servers.items()):
                try:
                    client.stop()
                except (Exception, OSError):
                    pass  # Ignore errors during cleanup
            self.servers.clear()

    def get_status(self) -> Dict[str, Any]:
        """Get daemon status."""
        with self.lock:
            return {
                "status": "running",
                "servers": list(self.servers.keys()),
                "server_count": len(self.servers)
            }

    def get_config(self) -> Dict[str, Any]:
        """Get available servers from configuration."""
        if not self.config:
            return {
                "success": False,
                "error": "No configuration loaded"
            }

        try:
            servers = self.config.get("mcpServers", {})
            available_servers = {}
            for name, config in servers.items():
                available_servers[name] = {
                    "command": config.get("command", ""),
                    "args": config.get("args", []),
                    "description": config.get("description", ""),
                    "running": name in self.servers
                }

            return {
                "success": True,
                "config_path": self.config_path,
                "servers": available_servers,
                "server_count": len(available_servers)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading configuration: {str(e)}"
            }

    def handle_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a client request."""
        cmd = data.get("command")

        if cmd == "start":
            return self.start_server(data["server"], data["server_command"])

        elif cmd == "call":
            return self.call_tool(
                data["server"],
                data["tool"],
                data.get("arguments", {})
            )

        elif cmd == "list":
            return self.list_tools(data["server"])

        elif cmd == "stop":
            return self.stop_server(data["server"])

        elif cmd == "list-all":
            return self.list_all_tools()

        elif cmd == "status":
            return self.get_status()

        elif cmd == "get-config":
            return self.get_config()

        elif cmd == "shutdown":
            self.running = False
            return {"success": True, "message": "Daemon shutting down"}

        else:
            return {"error": f"Unknown command: {cmd}"}

    def run(self):
        """Run the daemon server."""
        # Clean up old socket
        Path(self.socket_path).unlink(missing_ok=True)

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(self.socket_path)
        sock.listen(5)
        sock.settimeout(1.0)  # Allow checking self.running periodically

        print(f"MCP Daemon started (socket: {self.socket_path})")
        print(f"PID: {os.getpid()}")

        try:
            while self.running:
                try:
                    conn, _ = sock.accept()
                    # Handle each connection in a separate thread
                    threading.Thread(
                        target=self.handle_connection,
                        args=(conn,),
                        daemon=True
                    ).start()
                except socket.timeout:
                    continue  # Check self.running again
        finally:
            print("\nShutting down daemon...")
            self.stop_all()
            try:
                sock.close()
            except (Exception, OSError):
                pass  # Ignore errors during cleanup
            Path(self.socket_path).unlink(missing_ok=True)
            print("Daemon stopped")

    def handle_connection(self, conn: socket.socket):
        """Handle a single client connection."""
        try:
            # Read the request (with a reasonable size limit)
            data = b""
            while len(data) < 1024 * 1024:  # 1MB limit
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk

                # Check if we have a complete message (newline-delimited)
                if b"\n" in data:
                    break

            if data:
                request = json.loads(data.decode().strip())
                response = self.handle_request(request)
                conn.sendall(json.dumps(response).encode() + b"\n")
        except json.JSONDecodeError as e:
            error_response = {"error": f"Invalid JSON: {str(e)}"}
            conn.sendall(json.dumps(error_response).encode() + b"\n")
        except Exception as e:
            error_response = {"error": str(e)}
            conn.sendall(json.dumps(error_response).encode() + b"\n")
        finally:
            conn.close()


def daemon_start(args):
    """Start the daemon."""
    socket_path = args.socket

    # Check if daemon is already running
    if os.path.exists(socket_path):
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(socket_path)
            sock.close()
            print(f"Error: Daemon already running at {socket_path}", file=sys.stderr)
            print("Use 'mcp_daemon.py stop' to stop it first", file=sys.stderr)
            sys.exit(1)
        except (ConnectionRefusedError, FileNotFoundError):
            # Socket exists but nothing listening, clean it up
            os.unlink(socket_path)

    # Get config path if provided
    config_path = getattr(args, 'config', None)
    daemon = MCPDaemon(socket_path, config_path)

    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        print("\nReceived signal, shutting down...")
        daemon.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.foreground:
        # Run in foreground
        daemon.run()
    else:
        # Daemonize (double fork)
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process
                print(f"Daemon started with PID {pid}")
                print(f"Socket: {socket_path}")
                sys.exit(0)
        except OSError as e:
            print(f"Fork failed: {e}", file=sys.stderr)
            sys.exit(1)

        # First child
        os.setsid()

        try:
            pid = os.fork()
            if pid > 0:
                # First child exits
                sys.exit(0)
        except OSError as e:
            print(f"Fork failed: {e}", file=sys.stderr)
            sys.exit(1)

        # Second child (daemon)
        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()

        # Run the daemon
        daemon.run()


def daemon_stop(args):
    """Stop the daemon."""
    socket_path = args.socket

    if not os.path.exists(socket_path):
        print("Daemon is not running")
        return

    try:
        client = SocketClient(socket_path, timeout=DAEMON_CTRL_TIMEOUT)
        result = client.send_request({"command": "shutdown"})
        client.close()

        if result.get("success"):
            print("Daemon stopped")
            # Wait a bit for cleanup
            time.sleep(0.5)
        else:
            print(f"Error stopping daemon: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except ConnectionError:
        print("Daemon is not running (socket exists but no response)")
        # Clean up stale socket
        try:
            os.unlink(socket_path)
        except OSError:
            pass
    except (TimeoutError, ValueError) as e:
        print(f"Error stopping daemon: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error stopping daemon: {e}", file=sys.stderr)
        sys.exit(1)


def daemon_status(args):
    """Check daemon status."""
    socket_path = args.socket

    if not os.path.exists(socket_path):
        print("Daemon is not running")
        return

    try:
        client = SocketClient(socket_path, timeout=DAEMON_CTRL_TIMEOUT)
        result = client.send_request({"command": "status"})
        client.close()

        if getattr(args, 'json', False):
            print(json.dumps(result, indent=2))
        else:
            print(f"Daemon status: {result.get('status', 'unknown')}")
            print(f"Socket: {socket_path}")
            print(f"Active servers: {result.get('server_count', 0)}")
            if result.get('servers'):
                print(f"Server names: {', '.join(result['servers'])}")

    except ConnectionError:
        print("Daemon is not running")
    except (TimeoutError, ValueError) as e:
        print(f"Error checking status: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error checking status: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for MCP daemon."""
    parser = argparse.ArgumentParser(
        description="MCP Daemon - Persistent MCP server manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--socket",
        default="/tmp/mcp-daemon.sock",
        help="Unix socket path (default: /tmp/mcp-daemon.sock)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # start command
    start_parser = subparsers.add_parser("start", help="Start the daemon")
    start_parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run in foreground (don't daemonize)"
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
