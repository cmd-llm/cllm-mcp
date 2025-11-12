#!/bin/bash
# Example: Quick test of the datetime MCP server with daemon
#
# This script demonstrates:
# 1. Starting the daemon in the foreground
# 2. Calling datetime tools through the daemon
# 3. Handling daemon lifecycle

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=== Quick Datetime MCP Server Test ===${NC}"
echo ""

cd "$PROJECT_ROOT"

# The MCP server command to use
# The time MCP server from modelcontextprotocol
MCP_SERVER="uvx mcp-server-time"

# Step 1: List available tools
echo -e "${GREEN}Listing available tools from datetime server...${NC}"
uv run cllm-mcp list-tools "$MCP_SERVER" --json | jq '.[].name'
echo ""

# Step 2: Get current time
echo -e "${GREEN}Getting current time...${NC}"
RESULT=$(uv run cllm-mcp call-tool "$MCP_SERVER" "get_current_time" '{}' --json 2>/dev/null || echo "")

if [ ! -z "$RESULT" ]; then
    echo "$RESULT" | jq .
else
    echo "Tool execution result (raw format):"
    uv run cllm-mcp call-tool "$MCP_SERVER" "get_current_time" '{}'
fi
echo ""

# Step 3: Start daemon in background for interactive use
echo -e "${YELLOW}Tip: To use the daemon in the background:${NC}"
echo ""
echo "  # Start the daemon in the foreground (in one terminal):"
echo "  uv run cllm-mcp daemon start --foreground"
echo ""
echo "  # In another terminal, use the running daemon for faster operations:"
echo "  uv run cllm-mcp list-tools \"uvx mcp-server-time\""
echo ""
echo "  # Check daemon status:"
echo "  uv run cllm-mcp daemon status"
echo ""
echo "  # Stop the daemon when done:"
echo "  uv run cllm-mcp daemon stop"
