"""MCP Daemon Lifecycle - Command handlers for daemon operations.

This module contains handlers for daemon start, stop, and status commands,
as well as async initialization logic for auto-start servers.

This module is internal to cllm-mcp and is accessed via the unified cllm-mcp command.
"""

import asyncio
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from .daemon_server import MCPDaemon, _format_uptime, build_server_command
from .socket_utils import DAEMON_CTRL_TIMEOUT, SocketClient

# Configure logging for daemon operations
logger = logging.getLogger("MCPDaemon")


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


async def initialize_servers_async(
    daemon: MCPDaemon, config: Dict[str, Any], no_auto_init: bool = False
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

        logger.debug(
            f"Starting batch {batch_num}/{total_batches} ({len(batch)} servers)"
        )

        # Start batch servers concurrently
        tasks = []
        for name, server_config in batch:
            print(f"  Starting: {name}")
            logger.debug(f"  [{name}] Starting server...")
            tasks.append(
                _start_server_with_timeout(daemon, name, server_config, init_timeout)
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
            duration = result.get("duration", 0)
            print(f"  ✓ {result['name']} ready ({duration:.1f}s)")
            logger.info(f"[{result['name']}] Ready in {duration:.1f}s")
        else:
            error = result.get("error", "Unknown error")
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
            logger.warning(
                f"  {optional_failed} optional server(s) failed (continuing)"
            )
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
    daemon: MCPDaemon, name: str, server_config: Dict[str, Any], timeout: float
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
            loop.run_in_executor(
                None, lambda: daemon.start_server(name, command, auto_start=True)
            ),
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


def daemon_start(args):
    """
    Start the daemon (ADR-0005: with auto-initialization support).

    Supports the --no-auto-init flag to disable automatic server initialization.
    """
    socket_path = args.socket or None
    from .config import find_config_file, load_config

    # Determine socket path
    if not socket_path:
        from .socket_utils import get_default_socket_path
        socket_path = get_default_socket_path()

    # Check if daemon is already running
    if os.path.exists(socket_path):
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(socket_path)
            sock.close()
            print(f"Error: Daemon already running at {socket_path}", file=sys.stderr)
            print("Use 'cllm-mcp daemon stop' to stop it first", file=sys.stderr)
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
    def signal_handler(signum, frame):
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
    from .socket_utils import get_default_socket_path

    socket_path = args.socket or get_default_socket_path()

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
    from .socket_utils import get_default_socket_path

    socket_path = args.socket or get_default_socket_path()

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
