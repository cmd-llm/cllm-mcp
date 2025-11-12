#!/bin/bash
# Wrapper script to call an MCP tool
# Usage: ./mcp-call-tool.sh <server_command> <tool_name> <json_params>
#
# Example:
#   ./mcp-call-tool.sh "npx -y @modelcontextprotocol/server-filesystem /tmp" \
#       read_file '{"path": "/tmp/test.txt"}'

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 3 ]; then
    echo "Usage: $0 <server_command> <tool_name> <json_params>" >&2
    echo "Example: $0 'npx server' read_file '{\"path\": \"/tmp/file.txt\"}'" >&2
    exit 1
fi

SERVER_COMMAND="$1"
TOOL_NAME="$2"
JSON_PARAMS="$3"

exec python3 "$SCRIPT_DIR/mcp_cli.py" call-tool "$SERVER_COMMAND" "$TOOL_NAME" "$JSON_PARAMS"
