#!/bin/bash
# Wrapper script to list MCP tools
# Usage: ./mcp-list-tools.sh <server_command>
#
# Example:
#   ./mcp-list-tools.sh "npx -y @modelcontextprotocol/server-filesystem /tmp"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <server_command>" >&2
    echo "Example: $0 'npx -y @modelcontextprotocol/server-filesystem /tmp'" >&2
    exit 1
fi

SERVER_COMMAND="$1"

exec python3 "$SCRIPT_DIR/mcp_cli.py" list-tools "$SERVER_COMMAND"
