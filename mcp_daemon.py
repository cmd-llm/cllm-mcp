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

import argparse
import asyncio
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mcp_cli import MCPClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from cllm_mcp.config import find_config_file, load_config, validate_config
from cllm_mcp.socket_utils import DAEMON_CTRL_TIMEOUT, SocketClient

# Configure logging for ADR-0005 initialization
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)
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


class InitializationResult:
    """Result of server initialization process (ADR-0005)."""

    def __init__(
        self,
        total: int = 0,
        successful: int = 0,
        failed: int = 0,
        optional_failures: int = 0,
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        self.total = total
        self.successful = successful
        self.failed = failed
        self.optional_failures = optional_failures
        self.details = details or []

    def __repr__(self) -> str:
        return (
            f"InitializationResult(total={self.total}, successful={self.successful}, "
            f"failed={self.failed}, optional_failures={self.optional_failures})"
        )


def build_server_command(server_config: Dict[str, Any]) -> str:
    """Build the full server command from configuration."""
    command = server_config.get("command", "")
    args = server_config.get("args", [])
    if args:
        return f"{command} {' '.join(args)}"
    return command


async def initialize_servers_async(
    daemon: "MCPDaemon", config: Dict[str, Any], no_auto_init: bool = False
) -> InitializationResult:
    """
    Initialize all auto-start servers from configuration (ADR-0005).

    This function is called during daemon startup to prepare all configured
    MCP servers that have autoStart: true.

    Args:
        daemon: MCPDaemon instance to register servers with
        config: Configuration dictionary
        no_auto_init: If True, skip initialization entirely

    Returns:
        InitializationResult with success/failure status
    """
    if no_auto_init:
        logger.info("Auto-initialization disabled")
        return InitializationResult(total=0, successful=0, failed=0)

    # Get servers to initialize
    servers_config = config.get("mcpServers", {})
    servers_to_start = [
        (name, server_config)
        for name, server_config in servers_config.items()
        if server_config.get("autoStart", True)
    ]

    if not servers_to_start:
        logger.info("No servers configured for auto-start")
        return InitializationResult(total=0, successful=0, failed=0)

    # Get daemon configuration
    daemon_config = config.get("daemon", {})
    init_timeout = daemon_config.get("initializationTimeout", 60)
    parallel = daemon_config.get("parallelInitialization", 4)
    on_failure = daemon_config.get("onInitFailure", "warn")

    print(f"Initializing {len(servers_to_start)} auto-start servers...")
    logger.info(
        f"Initializing {len(servers_to_start)} auto-start servers "
        f"(max parallel: {parallel}, timeout: {init_timeout}s)"
    )

    # Start servers in parallel batches
    results: List[Dict[str, Any]] = []
    failed_servers: List[Tuple[str, str]] = []
    required_failures: List[str] = []

    for i in range(0, len(servers_to_start), parallel):
        batch = servers_to_start[i : i + parallel]
        batch_num = (i // parallel) + 1
        total_batches = (len(servers_to_start) + parallel - 1) // parallel

        logger.debug(f"Starting batch {batch_num}/{total_batches} ({len(batch)} servers)")

        # Start batch servers concurrently
        tasks = []
        for name, server_config in batch:
            print(f"  Starting: {name}")
            logger.debug(f"  [{name}] Starting server...")
            tasks.append(
                _start_server_with_timeout(
                    daemon, name, server_config, init_timeout
                )
            )

        # Run tasks with timeout
        try:
            batch_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=False),
                timeout=init_timeout,
            )
            results.extend(batch_results)
        except asyncio.TimeoutError:
            logger.error(
                f"Batch {batch_num} initialization timed out "
                f"(exceeded {init_timeout}s)"
            )
            for name, _ in batch:
                results.append(
                    {
                        "name": name,
                        "success": False,
                        "error": f"Initialization timeout (>{init_timeout}s)",
                    }
                )

    # Process results
    for result in results:
        if result["success"]:
            duration = result.get('duration', 0)
            print(f"  ✓ {result['name']} ready ({duration:.1f}s)")
            logger.info(f"[{result['name']}] Ready in {duration:.1f}s")
        else:
            error = result.get('error', 'Unknown error')
            print(f"  ✗ {result['name']} failed: {error}")
            logger.error(f"[{result['name']}] Failed: {error}")
            failed_servers.append((result["name"], error))

            # Check if this is a required failure
            is_optional = servers_config.get(result["name"], {}).get("optional", False)
            if not is_optional:
                required_failures.append(result["name"])

    # Handle failures based on policy
    if required_failures and on_failure == "fail":
        error_msg = f"Failed to start required servers: {', '.join(required_failures)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    successful = sum(1 for r in results if r.get("success"))
    failed = len(failed_servers)
    optional_failed = failed - len(required_failures)

    # Print summary
    print(f"\nServer initialization: {successful}/{len(servers_to_start)} started")
    if failed > 0:
        if optional_failed > 0:
            print(f"  ⚠ {optional_failed} optional server(s) failed (continuing)")
        if required_failures:
            print(f"  ⚠ {len(required_failures)} required server(s) failed")

    logger.info(
        f"Initialization complete: {successful}/{len(servers_to_start)} servers started"
    )
    if failed > 0:
        if optional_failed > 0:
            logger.warning(f"  {optional_failed} optional server(s) failed (continuing)")
        if required_failures:
            logger.warning(f"  {len(required_failures)} required server(s) failed")

    return InitializationResult(
        total=len(servers_to_start),
        successful=successful,
        failed=failed,
        optional_failures=optional_failed,
        details=results,
    )


async def _start_server_with_timeout(
    daemon: "MCPDaemon", name: str, server_config: Dict[str, Any], timeout: float
) -> Dict[str, Any]:
    """
    Start a single server with timeout (ADR-0005).

    Args:
        daemon: MCPDaemon instance
        name: Server name
        server_config: Server configuration
        timeout: Timeout in seconds

    Returns:
        Result dictionary with success/failure info
    """
    start_time = time.time()

    try:
        command = build_server_command(server_config)

        # Start server in thread (sync operation)
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: daemon.start_server(name, command, auto_start=True)),
            timeout=timeout,
        )

        duration = time.time() - start_time
        return {
            "name": name,
            "success": result.get("success", False),
            "error": result.get("error"),
            "duration": duration,
        }

    except asyncio.TimeoutError:
        duration = time.time() - start_time
        return {
            "name": name,
            "success": False,
            "error": f"Timeout (>{timeout}s)",
            "duration": duration,
        }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "name": name,
            "success": False,
            "error": str(e),
            "duration": duration,
        }


class MCPDaemon:
    """Daemon that manages multiple MCP server processes."""

    def __init__(
        self,
        socket_path: str = "/tmp/mcp-daemon.sock",
        config_path: Optional[str] = None,
    ):
        self.socket_path = socket_path
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
            config_file = config_path or find_config_file()[0]  # find_config_file returns tuple
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

    def start_server(self, name: str, command: str, auto_start: bool = False) -> Dict[str, Any]:
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
                client = MCPClient(command)
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
                                        logger.info(f"[{server_name}] Restart successful")
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


def daemon_start(args):
    """
    Start the daemon (ADR-0005: with auto-initialization support).

    Supports the --no-auto-init flag to disable automatic server initialization.
    """
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
    config_path = getattr(args, "config", None)
    daemon = MCPDaemon(socket_path, config_path)

    # ADR-0005: Initialize servers if config is loaded and auto-init is enabled
    no_auto_init = getattr(args, "no_auto_init", False)
    if daemon.config and not no_auto_init:
        try:
            # Run async initialization
            init_result = asyncio.run(
                initialize_servers_async(daemon, daemon.config, no_auto_init=False)
            )
            logger.info(f"Initialization complete: {init_result}")
        except RuntimeError as e:
            # Handle initialization failure
            logger.error(f"Initialization failed: {e}")
            daemon_config = daemon.config.get("daemon", {})
            on_failure = daemon_config.get("onInitFailure", "warn")
            if on_failure == "fail":
                sys.exit(1)
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error during initialization: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        print("\nReceived signal, shutting down...")
        daemon.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # ADR-0005: Start health monitoring in background thread
    if daemon.auto_started_servers:
        health_thread = threading.Thread(
            target=daemon.monitor_server_health, args=(30,), daemon=True
        )
        health_thread.start()
        logger.debug("Health monitoring thread started")

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
    """Check daemon status (ADR-0005: enhanced with auto-start info)."""
    socket_path = args.socket

    if not os.path.exists(socket_path):
        print("Daemon is not running")
        return

    try:
        client = SocketClient(socket_path, timeout=DAEMON_CTRL_TIMEOUT)
        result = client.send_request({"command": "status"})
        client.close()

        if getattr(args, "json", False):
            print(json.dumps(result, indent=2))
        else:
            print(f"Daemon status: {result.get('status', 'unknown')}")
            print(f"Socket: {socket_path}")
            print(f"Active servers: {result.get('server_count', 0)}")

            # ADR-0005: Enhanced status display
            auto_started = result.get("auto_started", [])
            on_demand = result.get("on_demand", [])

            if auto_started:
                print("\nAuto-Started Servers (from config):")
                for server_info in auto_started:
                    name = server_info.get("name")
                    uptime = server_info.get("uptime")
                    if uptime is not None:
                        uptime_str = _format_uptime(uptime)
                        print(f"  - {name} (uptime: {uptime_str})")
                    else:
                        print(f"  - {name}")

            if on_demand:
                print("\nOn-Demand Servers:")
                for server_info in on_demand:
                    name = server_info.get("name")
                    print(f"  - {name}")

            if not auto_started and not on_demand and result.get("servers"):
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
        epilog=__doc__,
    )

    parser.add_argument(
        "--socket",
        default="/tmp/mcp-daemon.sock",
        help="Unix socket path (default: /tmp/mcp-daemon.sock)",
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
