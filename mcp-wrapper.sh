#!/bin/bash
# Advanced MCP wrapper that uses configuration file
# Usage: ./mcp-wrapper.sh <server_name> <command> [args...]
#
# Examples:
#   ./mcp-wrapper.sh filesystem list-tools
#   ./mcp-wrapper.sh filesystem call-tool read_file '{"path": "/tmp/test.txt"}'
#   ./mcp-wrapper.sh github call-tool create_issue '{"owner": "user", "repo": "repo", "title": "Bug"}'
#
# Daemon mode:
#   export MCP_USE_DAEMON=1  # Enable daemon mode for faster repeated calls
#   ./mcp-wrapper.sh filesystem call-tool read_file '{"path": "/tmp/test.txt"}'

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${MCP_CONFIG_FILE:-$SCRIPT_DIR/mcp-config.json}"

if [ $# -lt 2 ]; then
    echo "Usage: $0 <server_name> <command> [args...]" >&2
    echo "" >&2
    echo "Commands:" >&2
    echo "  list-tools                     - List available tools" >&2
    echo "  call-tool <name> <json_params> - Call a specific tool" >&2
    echo "  interactive                    - Interactive mode" >&2
    echo "" >&2
    echo "Config file: $CONFIG_FILE" >&2
    exit 1
fi

SERVER_NAME="$1"
COMMAND="$2"
shift 2

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found: $CONFIG_FILE" >&2
    echo "Create one from mcp-config.example.json" >&2
    exit 1
fi

# Extract server configuration using Python
SERVER_CONFIG=$(python3 -c "
import json
import sys

try:
    with open('$CONFIG_FILE') as f:
        config = json.load(f)

    if 'mcpServers' not in config:
        print('Error: mcpServers not found in config', file=sys.stderr)
        sys.exit(1)

    if '$SERVER_NAME' not in config['mcpServers']:
        print('Error: Server \"$SERVER_NAME\" not found in config', file=sys.stderr)
        print('Available servers:', ', '.join(config['mcpServers'].keys()), file=sys.stderr)
        sys.exit(1)

    server = config['mcpServers']['$SERVER_NAME']

    # Build command
    cmd = [server['command']] + server.get('args', [])
    cmd_str = ' '.join(cmd)

    # Export environment variables if any
    env_vars = server.get('env', {})
    for key, value in env_vars.items():
        print(f'export {key}=\"{value}\"')

    # Print the command
    print(f'MCP_SERVER_COMMAND=\"{cmd_str}\"')

except Exception as e:
    print(f'Error parsing config: {e}', file=sys.stderr)
    sys.exit(1)
")

# Execute the Python output to set variables
eval "$SERVER_CONFIG"

# Build daemon flag if MCP_USE_DAEMON is set
DAEMON_FLAG=""
if [ "${MCP_USE_DAEMON:-0}" = "1" ]; then
    DAEMON_FLAG="--use-daemon"
fi

# Execute the MCP CLI command
case "$COMMAND" in
    list-tools)
        exec python3 "$SCRIPT_DIR/mcp_cli.py" list-tools $DAEMON_FLAG "$MCP_SERVER_COMMAND"
        ;;
    call-tool)
        if [ $# -lt 2 ]; then
            echo "Usage: $0 $SERVER_NAME call-tool <tool_name> <json_params>" >&2
            exit 1
        fi
        TOOL_NAME="$1"
        JSON_PARAMS="$2"
        exec python3 "$SCRIPT_DIR/mcp_cli.py" call-tool $DAEMON_FLAG "$MCP_SERVER_COMMAND" "$TOOL_NAME" "$JSON_PARAMS"
        ;;
    interactive)
        exec python3 "$SCRIPT_DIR/mcp_cli.py" interactive "$MCP_SERVER_COMMAND"
        ;;
    *)
        echo "Unknown command: $COMMAND" >&2
        echo "Available commands: list-tools, call-tool, interactive" >&2
        exit 1
        ;;
esac
