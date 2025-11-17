"""MCP Daemon Server - Core daemon implementation.

This module contains the MCPDaemon class which manages persistent MCP server
processes and handles IPC communication via Unix domain sockets.

This module is internal to cllm-mcp and is accessed via the unified cllm-mcp command.
"""

import json
import logging
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .client import MCPClient
from .config import build_server_command, find_config_file, load_config, validate_config
from .env_expansion import EnvironmentVariableError, ServerEnvironmentBuilder
from .socket_utils import get_default_socket_path

# Configure logging for daemon operations
logger = logging.getLogger("MCPDaemon")


def _format_uptime(seconds: float) -> str:
    """Format uptime in seconds to human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


class MCPDaemon:
    """Daemon that manages multiple MCP server processes."""

    def __init__(
        self,
        socket_path: Optional[str] = None,
        config_path: Optional[str] = None,
    ):
        self.socket_path = socket_path or get_default_socket_path()
        self.servers: Dict[str, MCPClient] = {}
        self.lock = threading.Lock()
        self.running = True

        # ADR-0005: Track auto-started servers for health monitoring
        self.auto_started_servers: set = set()
        self.server_start_times: Dict[str, float] = {}

        # Load configuration for server discovery
        self.config = None
        self.config_path = None
        try:
            # Try explicit path first, then auto-discover
            config_file = (
                config_path or find_config_file()[0]
            )  # find_config_file returns tuple
            if config_file:
                self.config = load_config(str(config_file))
                errors = validate_config(self.config)
                if not errors:
                    self.config_path = str(config_file)
                else:
                    logger.warning(f"Configuration validation failed: {errors}")
                    self.config = None  # Invalid config, ignore it
        except Exception as e:
            logger.warning(f"Failed to load configuration: {e}")

    def start_server(
        self, name: str, command: str, auto_start: bool = False
    ) -> Dict[str, Any]:
        """
        Start and cache an MCP server.

        Args:
            name: Server name
            command: Full server command
            auto_start: If True, mark as auto-started for health monitoring (ADR-0005)
        """
        with self.lock:
            if name in self.servers:
                return {"success": True, "message": "Server already running"}

            try:
                # ADR-0008: Build environment for the server using ServerEnvironmentBuilder
                server_env = None
                if self.config and "mcpServers" in self.config:
                    server_config = self.config["mcpServers"].get(name, {})
                    if server_config:
                        try:
                            server_env = ServerEnvironmentBuilder.from_config(
                                server_name=name,
                                server_config=server_config,
                                parent_env=os.environ.copy(),
                                strict=False,  # Non-strict by default
                            )
                        except EnvironmentVariableError as e:
                            logger.warning(
                                f"Environment variable error for server '{name}': {e}"
                            )
                            # Continue with parent environment if expansion fails

                client = MCPClient(command, env=server_env)
                client.start()
                self.servers[name] = client

                # ADR-0005: Track auto-started servers
                if auto_start:
                    self.auto_started_servers.add(name)
                    self.server_start_times[name] = time.time()

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
                        "tool_count": len(tools),
                    }
                except Exception:
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
                "total_tools": sum(
                    s.get("tool_count", 0) for s in all_tools_by_server.values()
                ),
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
            for _name, client in list(self.servers.items()):
                try:
                    client.stop()
                except (Exception, OSError):
                    pass  # Ignore errors during cleanup
            self.servers.clear()
            # ADR-0005: Clear health monitoring data
            self.auto_started_servers.clear()
            self.server_start_times.clear()

    def monitor_server_health(self, interval: int = 30):
        """
        Monitor health of auto-started servers and restart if needed (ADR-0005).

        This runs as a background thread, periodically checking if auto-started
        servers are still running and restarting them if they crash.

        Args:
            interval: Check interval in seconds
        """
        logger.debug(f"Starting health monitoring (interval: {interval}s)")

        while self.running:
            time.sleep(interval)

            if not self.running:
                break

            # Check all auto-started servers
            with self.lock:
                for server_name in list(self.auto_started_servers):
                    if server_name not in self.servers:
                        # Server crashed, try to restart it
                        if self.config:
                            server_config = self.config.get("mcpServers", {}).get(
                                server_name
                            )
                            if server_config:
                                logger.warning(
                                    f"Auto-started server '{server_name}' crashed, restarting..."
                                )
                                try:
                                    command = build_server_command(server_config)
                                    result = self.start_server(
                                        server_name, command, auto_start=True
                                    )
                                    if result.get("success"):
                                        logger.info(
                                            f"[{server_name}] Restart successful"
                                        )
                                    else:
                                        logger.error(
                                            f"[{server_name}] Restart failed: {result.get('error')}"
                                        )
                                except Exception as e:
                                    logger.error(
                                        f"[{server_name}] Restart failed with exception: {e}"
                                    )

    def get_status(self) -> Dict[str, Any]:
        """Get daemon status (ADR-0005: enhanced with auto-start info)."""
        with self.lock:
            # Separate auto-started and on-demand servers
            auto_started = []
            on_demand = []

            current_time = time.time()
            for server_name in self.servers.keys():
                server_info = {"name": server_name}

                # Add uptime if available
                if server_name in self.server_start_times:
                    uptime_seconds = current_time - self.server_start_times[server_name]
                    server_info["uptime"] = uptime_seconds

                if server_name in self.auto_started_servers:
                    auto_started.append(server_info)
                else:
                    on_demand.append(server_info)

            return {
                "status": "running",
                "servers": list(self.servers.keys()),
                "server_count": len(self.servers),
                "auto_started": auto_started,
                "on_demand": on_demand,
                "auto_start_count": len(auto_started),
                "on_demand_count": len(on_demand),
            }

    def get_config(self) -> Dict[str, Any]:
        """Get available servers from configuration."""
        if not self.config:
            return {"success": False, "error": "No configuration loaded"}

        try:
            servers = self.config.get("mcpServers", {})
            available_servers = {}
            for name, config in servers.items():
                available_servers[name] = {
                    "command": config.get("command", ""),
                    "args": config.get("args", []),
                    "description": config.get("description", ""),
                    "running": name in self.servers,
                }

            return {
                "success": True,
                "config_path": self.config_path,
                "servers": available_servers,
                "server_count": len(available_servers),
            }
        except Exception as e:
            return {"success": False, "error": f"Error reading configuration: {str(e)}"}

    def handle_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a client request."""
        cmd = data.get("command")

        if cmd == "start":
            return self.start_server(data["server"], data["server_command"])

        elif cmd == "call":
            return self.call_tool(
                data["server"], data["tool"], data.get("arguments", {})
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
                        target=self.handle_connection, args=(conn,), daemon=True
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
