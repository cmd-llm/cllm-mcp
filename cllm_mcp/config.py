"""
Configuration management for ADR-0003 and ADR-0004.

Handles loading, validating, and discovering MCP server configurations
using CLLM-style configuration precedence.

Configuration Search Order (lowest to highest priority):
1. ~/.cllm/mcp-config.json         (Global defaults)
2. ./.cllm/mcp-config.json         (Project-specific)
3. ./mcp-config.json               (Current directory)
4. Environment variables (CLLM_MCP_*) (CI/CD, containerized)
5. CLI arguments                    (Explicit overrides)
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ConfigError(Exception):
    """Raised when configuration is invalid."""

    pass


def _get_env_config_override() -> Optional[str]:
    """
    Get configuration file path from environment variable.

    Supports: CLLM_MCP_CONFIG

    Returns:
        Config file path from environment, or None if not set
    """
    return os.environ.get("CLLM_MCP_CONFIG")


def find_config_file(
    explicit_path: Optional[str] = None, verbose: bool = False
) -> Tuple[Optional[Path], List[str]]:
    """
    Find configuration file using CLLM precedence.

    ADR-0004 Configuration Precedence (lowest to highest priority):
    1. ~/.cllm/mcp-config.json         (Global defaults)
    2. ./.cllm/mcp-config.json         (Project-specific)
    3. ./mcp-config.json               (Current directory)
    4. Environment variables (CLLM_MCP_CONFIG)
    5. Explicit path argument (highest priority)

    Args:
        explicit_path: Explicit path to config file (highest priority)
        verbose: If True, return trace of all checked paths

    Returns:
        Tuple of (path_to_config, trace_messages)
        - path_to_config: Path to config file if found, None otherwise
        - trace_messages: List of diagnostic messages (empty if verbose=False)
    """
    trace = []

    if verbose:
        trace.append("[CONFIG] Searching for configuration files...")

    # Priority 5: Explicit path (highest priority)
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if verbose:
            trace.append(f"[CONFIG] Checking explicit path: {path}")
        if path.exists():
            if verbose:
                trace.append(f"[CONFIG] ✓ Found (highest priority): {path}")
            return path, trace
        if verbose:
            trace.append(f"[CONFIG] ✗ Not found: {path}")
        return None, trace

    # Priority 4: Environment variables
    env_path = _get_env_config_override()
    if env_path:
        path = Path(env_path).expanduser()
        if verbose:
            trace.append(f"[CONFIG] Checking CLLM_MCP_CONFIG: {path}")
        if path.exists():
            if verbose:
                trace.append(f"[CONFIG] ✓ Found (environment): {path}")
            return path, trace
        if verbose:
            trace.append(f"[CONFIG] ✗ Not found: {path}")

    # Priority 3: Current directory (./mcp-config.json)
    cwd_config = Path.cwd() / "mcp-config.json"
    if verbose:
        trace.append(f"[CONFIG] Checking current directory: {cwd_config}")
    if cwd_config.exists():
        if verbose:
            trace.append(f"[CONFIG] ✓ Found (current directory): {cwd_config}")
        return cwd_config, trace
    if verbose:
        trace.append(f"[CONFIG] ✗ Not found: {cwd_config}")

    # Priority 2: Project-specific (./.cllm/mcp-config.json)
    project_config = Path.cwd() / ".cllm" / "mcp-config.json"
    if verbose:
        trace.append(f"[CONFIG] Checking project config: {project_config}")
    if project_config.exists():
        if verbose:
            trace.append(f"[CONFIG] ✓ Found (project-specific): {project_config}")
        return project_config, trace
    if verbose:
        trace.append(f"[CONFIG] ✗ Not found: {project_config}")

    # Priority 1: Global defaults (~/.cllm/mcp-config.json)
    global_config = Path.home() / ".cllm" / "mcp-config.json"
    if verbose:
        trace.append(f"[CONFIG] Checking global config: {global_config}")
    if global_config.exists():
        if verbose:
            trace.append(f"[CONFIG] ✓ Found (global defaults): {global_config}")
        return global_config, trace
    if verbose:
        trace.append(f"[CONFIG] ✗ Not found: {global_config}")

    # Backward compatibility: Check old paths (deprecated)
    old_paths = [
        Path.home() / ".config" / "cllm-mcp" / "config.json",
        Path("/etc/cllm-mcp/config.json"),
    ]

    for old_path in old_paths:
        if verbose:
            trace.append(f"[CONFIG] Checking deprecated path: {old_path}")
        if old_path.exists():
            if verbose:
                trace.append(f"[CONFIG] ⚠ Found at deprecated location: {old_path}")
                trace.append("[CONFIG] ⚠ WARNING: Old config locations are deprecated")
                trace.append("[CONFIG] ⚠ Please migrate to ~/.cllm/mcp-config.json")
            return old_path, trace

    if verbose:
        trace.append("[CONFIG] ✗ No configuration file found")

    return None, trace


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load and parse configuration file.

    Args:
        config_path: Path to configuration file

    Returns:
        Parsed configuration dictionary

    Raises:
        ConfigError: If file doesn't exist or JSON is invalid
    """
    path = Path(config_path).expanduser()

    if not path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {config_path}: {e}")
    except IOError as e:
        raise ConfigError(f"Error reading {config_path}: {e}")

    return config


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate configuration structure.

    Validates both server configurations and daemon settings (ADR-0005).

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if "mcpServers" not in config:
        errors.append("Missing 'mcpServers' section")
        return errors

    servers = config.get("mcpServers", {})
    if not isinstance(servers, dict):
        errors.append("'mcpServers' must be a dictionary")
        return errors

    for server_name, server_config in servers.items():
        if not isinstance(server_config, dict):
            errors.append(f"Server '{server_name}': configuration must be a dictionary")
            continue

        # Check required fields
        if "command" not in server_config:
            errors.append(f"Server '{server_name}': missing required 'command' field")

        # Validate optional fields
        if "args" in server_config and not isinstance(server_config["args"], list):
            errors.append(f"Server '{server_name}': 'args' must be a list")

        if "env" in server_config and not isinstance(server_config["env"], dict):
            errors.append(f"Server '{server_name}': 'env' must be a dictionary")

        if "description" in server_config and not isinstance(
            server_config["description"], str
        ):
            errors.append(f"Server '{server_name}': 'description' must be a string")

        # ADR-0005: Validate new auto-start fields
        if "autoStart" in server_config and not isinstance(
            server_config["autoStart"], bool
        ):
            errors.append(f"Server '{server_name}': 'autoStart' must be a boolean")

        if "optional" in server_config and not isinstance(
            server_config["optional"], bool
        ):
            errors.append(f"Server '{server_name}': 'optional' must be a boolean")

    # ADR-0005: Validate daemon configuration section
    if "daemon" in config:
        daemon_config = config["daemon"]
        if not isinstance(daemon_config, dict):
            errors.append("'daemon' section must be a dictionary")
        else:
            # Validate daemon field types
            if "socket" in daemon_config and not isinstance(
                daemon_config["socket"], str
            ):
                errors.append("'daemon.socket' must be a string")

            if "timeout" in daemon_config and not isinstance(
                daemon_config["timeout"], (int, float)
            ):
                errors.append("'daemon.timeout' must be a number")

            if "maxServers" in daemon_config and not isinstance(
                daemon_config["maxServers"], int
            ):
                errors.append("'daemon.maxServers' must be an integer")

            if "initializationTimeout" in daemon_config and not isinstance(
                daemon_config["initializationTimeout"], (int, float)
            ):
                errors.append("'daemon.initializationTimeout' must be a number")

            if "parallelInitialization" in daemon_config and not isinstance(
                daemon_config["parallelInitialization"], int
            ):
                errors.append("'daemon.parallelInitialization' must be an integer")

            # Validate onInitFailure enum
            if "onInitFailure" in daemon_config:
                valid_values = ["fail", "warn", "ignore"]
                if daemon_config["onInitFailure"] not in valid_values:
                    errors.append(
                        f"'daemon.onInitFailure' must be one of: {', '.join(valid_values)}"
                    )

    return errors


def get_server_config(
    config: Dict[str, Any], server_name: str
) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific server.

    Args:
        config: Full configuration dictionary
        server_name: Name of the server

    Returns:
        Server configuration dictionary or None if not found
    """
    servers = config.get("mcpServers", {})
    return servers.get(server_name)


def build_server_command(server_config: Dict[str, Any]) -> str:
    """
    Build the full server command from configuration.

    Args:
        server_config: Server configuration dictionary with 'command' and optional 'args'

    Returns:
        Full command string (e.g., "uvx mcp-server-time" or "npx -y @modelcontextprotocol/server-filesystem /tmp")
    """
    command = server_config.get("command", "")
    args = server_config.get("args", [])

    if args:
        return f"{command} {' '.join(args)}"
    return command


def resolve_server_ref(
    server_ref: str, config: Optional[Dict[str, Any]] = None
) -> Tuple[str, Optional[str]]:
    """
    Resolve a server reference to a full command.

    A server reference can be:
    1. A server name from config (e.g., "time")
    2. A full server command (e.g., "uvx mcp-server-time")

    Args:
        server_ref: Server reference (name or command)
        config: Configuration dictionary (optional)

    Returns:
        Tuple of (resolved_command, server_name_or_none)
        - resolved_command: The full command to execute
        - server_name_or_none: The server name if resolved from config, None otherwise
    """
    # Check if server_ref matches a configured server name
    if config:
        servers = config.get("mcpServers", {})
        if server_ref in servers:
            server_config = servers[server_ref]
            command = build_server_command(server_config)
            return (command, server_ref)

    # Otherwise, treat it as a direct command
    return (server_ref, None)


def list_servers(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    List all configured servers with details.

    Args:
        config: Configuration dictionary

    Returns:
        List of server info dictionaries
    """
    servers = []
    config_servers = config.get("mcpServers", {})

    for name in sorted(config_servers.keys()):
        server_config = config_servers[name]
        servers.append(
            {
                "name": name,
                "command": server_config.get("command", ""),
                "args": server_config.get("args", []),
                "description": server_config.get("description", ""),
                "env": server_config.get("env", {}),
                "autoStart": server_config.get("autoStart", True),  # ADR-0005
                "optional": server_config.get("optional", False),  # ADR-0005
            }
        )

    return servers


def cmd_config_list(args):
    """Command to list configured servers."""
    verbose = getattr(args, "verbose", False)

    # Find config file
    config_path = args.config
    found_path, trace = find_config_file(config_path, verbose=verbose)

    # Print trace messages if verbose
    if trace:
        for msg in trace:
            print(msg)

    if not found_path:
        print("Error: No configuration file found", file=sys.stderr)
        print("\nSearched in (priority order):", file=sys.stderr)
        print("  1. ~/.cllm/mcp-config.json (global defaults)", file=sys.stderr)
        print("  2. ./.cllm/mcp-config.json (project-specific)", file=sys.stderr)
        print("  3. ./mcp-config.json (current directory)", file=sys.stderr)
        print("  4. CLLM_MCP_CONFIG environment variable", file=sys.stderr)
        print("  5. Explicit --config argument", file=sys.stderr)
        sys.exit(1)

    config_path = str(found_path)

    # Load and validate config
    try:
        config = load_config(config_path)
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate_config(config)
    if errors:
        print("Error: Configuration is invalid", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    # List servers
    servers = list_servers(config)

    if getattr(args, "json", False):
        print(json.dumps(servers, indent=2))
    else:
        if not servers:
            print("No servers configured")
            sys.exit(0)

        print(f"Configured MCP servers (from {config_path}):\n")
        for server in servers:
            print(f"  {server['name']}")
            if server["description"]:
                print(f"    Description: {server['description']}")
            print(f"    Command: {server['command']}")
            if server["args"]:
                print(f"    Args: {' '.join(server['args'])}")
            if server["env"]:
                env_str = ", ".join(f"{k}={v}" for k, v in server["env"].items())
                print(f"    Env: {env_str}")
            print()


def cmd_config_validate(args):
    """Command to validate configuration file."""
    verbose = getattr(args, "verbose", False)

    # Find config file
    config_path = args.config
    found_path, trace = find_config_file(config_path, verbose=verbose)

    # Print trace messages if verbose
    if trace:
        for msg in trace:
            print(msg)

    if not found_path:
        print("Error: No configuration file found", file=sys.stderr)
        sys.exit(1)

    config_path = str(found_path)

    # Load and validate config
    try:
        config = load_config(config_path)
    except ConfigError as e:
        print(f"✗ Invalid: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate_config(config)
    if errors:
        print(f"✗ Configuration invalid at {config_path}")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    # Count servers
    servers = list_servers(config)
    print(f"✓ Configuration valid at {config_path}")
    print(f"✓ {len(servers)} server(s) configured")

    # Check if commands are executable (if possible)
    for server in servers:
        cmd = server["command"].split()[0]  # Get first part
        # Try to find the command
        if os.path.isfile(cmd):
            if not os.access(cmd, os.X_OK):
                print(f"⚠ Warning: {server['name']}: command not executable: {cmd}")


def cmd_config_show(args):
    """Command to show which configuration file is being used."""
    getattr(args, "verbose", False)

    # Find config file (always verbose for this command)
    config_path = args.config
    found_path, trace = find_config_file(config_path, verbose=True)

    print("\n=== Configuration File Resolution ===\n")

    # Always show the trace for this command
    for msg in trace:
        print(msg)

    if found_path:
        print("\n[CONFIG] Using configuration file:")
        print(f"  {found_path}")

        # Try to load and show info
        try:
            config = load_config(str(found_path))
            errors = validate_config(config)

            if not errors:
                servers = list_servers(config)
                print("\n[CONFIG] Configuration Status: ✓ Valid")
                print(f"[CONFIG] Servers configured: {len(servers)}")
                if servers:
                    print(
                        f"[CONFIG] Available servers: {', '.join(s['name'] for s in servers)}"
                    )
            else:
                print("\n[CONFIG] Configuration Status: ✗ Invalid")
                for error in errors:
                    print(f"[CONFIG]   - {error}")
        except ConfigError as e:
            print("\n[CONFIG] Configuration Status: ✗ Error")
            print(f"[CONFIG]   {e}")
    else:
        print("\n[CONFIG] No configuration file found!")
        print("[CONFIG] To create one, use:")
        print("[CONFIG]   mkdir -p ~/.cllm")
        print("[CONFIG]   cat > ~/.cllm/mcp-config.json << 'EOF'")
        print("[CONFIG] {")
        print('[CONFIG]   "mcpServers": {}')
        print("[CONFIG] }")
        print("[CONFIG] EOF")


def cmd_config_migrate(args):
    """Command to migrate old config files to new CLLM folder structure."""
    print("\n=== Configuration Migration Tool ===\n")

    # Check for old config locations
    old_locations = [
        Path.home() / ".config" / "cllm-mcp" / "config.json",
        Path("/etc/cllm-mcp/config.json"),
    ]

    new_location = Path.home() / ".cllm" / "mcp-config.json"

    old_found = []
    for old_path in old_locations:
        if old_path.exists():
            old_found.append(old_path)

    if not old_found:
        print("✓ No old configuration files found.")
        print("  Your configuration is already using the new CLLM structure!")
        return

    print(f"Found {len(old_found)} old configuration file(s):\n")
    for path in old_found:
        print(f"  - {path}")

    if new_location.exists():
        print("\n⚠ WARNING: New location already exists!")
        print(f"  {new_location}")
        print("\nPlease manually migrate your configuration.")
        print("Do not overwrite the existing file.")
        return

    # Ask for confirmation
    response = input(f"\nMigrate to {new_location}? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("Migration cancelled.")
        return

    try:
        # Create .cllm directory
        new_location.parent.mkdir(parents=True, exist_ok=True)

        # Copy the first old config to new location
        source = old_found[0]
        with open(source, "r") as f:
            config_data = f.read()

        with open(new_location, "w") as f:
            f.write(config_data)

        print("\n✓ Migrated successfully!")
        print(f"  Source: {source}")
        print(f"  Target: {new_location}")

        if len(old_found) > 1:
            print(f"\n⚠ Found {len(old_found)} old configuration files.")
            print("  Migrated from the first one.")
            print("  Other locations:")
            for path in old_found[1:]:
                print(f"    - {path}")
            print(
                "  You can safely remove these files after verifying migration was successful."
            )

    except Exception as e:
        print(f"\n✗ Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
