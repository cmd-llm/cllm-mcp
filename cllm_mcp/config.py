"""
Configuration management for ADR-0003.

Handles loading, validating, and discovering MCP server configurations.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class ConfigError(Exception):
    """Raised when configuration is invalid."""
    pass


def find_config_file(explicit_path: Optional[str] = None) -> Optional[Path]:
    """
    Find configuration file in standard locations.

    Priority:
    1. Explicit path (--config argument)
    2. Current working directory (mcp-config.json, .mcp-config.json)
    3. Home directory (~/.config/cllm-mcp/config.json)
    4. System directory (/etc/cllm-mcp/config.json)

    Args:
        explicit_path: Explicit path to config file

    Returns:
        Path to config file if found, None otherwise
    """
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if path.exists():
            return path
        return None

    # Check current working directory
    for name in ["mcp-config.json", ".mcp-config.json"]:
        path = Path.cwd() / name
        if path.exists():
            return path

    # Check home directory
    home_config = Path.home() / ".config" / "cllm-mcp" / "config.json"
    if home_config.exists():
        return home_config

    # Check system directory
    system_config = Path("/etc/cllm-mcp/config.json")
    if system_config.exists():
        return system_config

    return None


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
        with open(path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {config_path}: {e}")
    except IOError as e:
        raise ConfigError(f"Error reading {config_path}: {e}")

    return config


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate configuration structure.

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

        if "description" in server_config and not isinstance(server_config["description"], str):
            errors.append(f"Server '{server_name}': 'description' must be a string")

    return errors


def get_server_config(config: Dict[str, Any], server_name: str) -> Optional[Dict[str, Any]]:
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


def resolve_server_ref(server_ref: str, config: Optional[Dict[str, Any]] = None) -> Tuple[str, Optional[str]]:
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
        servers.append({
            "name": name,
            "command": server_config.get("command", ""),
            "args": server_config.get("args", []),
            "description": server_config.get("description", ""),
            "env": server_config.get("env", {})
        })

    return servers


def cmd_config_list(args):
    """Command to list configured servers."""
    # Find config file
    config_path = args.config
    if not config_path:
        found_path = find_config_file()
        if not found_path:
            print("Error: No configuration file found", file=sys.stderr)
            print("Searched in: .", file=sys.stderr)
            print("             ~/.config/cllm-mcp/config.json", file=sys.stderr)
            print("             /etc/cllm-mcp/config.json", file=sys.stderr)
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

    if args.json:
        print(json.dumps(servers, indent=2))
    else:
        if not servers:
            print("No servers configured")
            sys.exit(0)

        print(f"Configured MCP servers (from {config_path}):\n")
        for server in servers:
            print(f"  {server['name']}")
            if server['description']:
                print(f"    Description: {server['description']}")
            print(f"    Command: {server['command']}")
            if server['args']:
                print(f"    Args: {' '.join(server['args'])}")
            if server['env']:
                env_str = ', '.join(f"{k}={v}" for k, v in server['env'].items())
                print(f"    Env: {env_str}")
            print()


def cmd_config_validate(args):
    """Command to validate configuration file."""
    # Find config file
    config_path = args.config
    if not config_path:
        found_path = find_config_file()
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
        cmd = server['command'].split()[0]  # Get first part
        # Try to find the command
        if os.path.isfile(cmd):
            if not os.access(cmd, os.X_OK):
                print(f"⚠ Warning: {server['name']}: command not executable: {cmd}")
