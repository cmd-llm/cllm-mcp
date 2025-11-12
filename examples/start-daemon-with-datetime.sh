#!/bin/bash
# Example: Start the daemon in the foreground with the datetime MCP server
#
# This script demonstrates:
# 1. Starting the cllm-mcp daemon in foreground mode
# 2. Configuring it to use the datetime MCP server from modelcontextprotocol
# 3. Running time-related tools through the daemon
#
# Prerequisites:
#   - Python 3.8+
#   - uv (Python package manager): https://docs.astral.sh/uv/
#   - Node.js (for npx to run MCP servers)
#
# The datetime MCP server provides tools like:
#   - get_current_time: Get the current date and time
#   - get_timezone: Get the current timezone

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

echo -e "${BLUE}=== Starting MCP Daemon with Datetime Server ===${NC}"
echo ""

# Option 1: Start daemon in foreground with daemon command
echo -e "${GREEN}Starting daemon in foreground mode...${NC}"
echo "This will run the daemon in the foreground so you can see all output."
echo ""

cd "${PROJECT_ROOT}"

# Start the daemon with --foreground flag
# The daemon will load configurations from mcp-config.json or environment
uv run cllm-mcp daemon start --foreground

# Note: The daemon will run until you press Ctrl+C
# Once the daemon is running, you can use it in another terminal with commands like:
#
#   # List tools from the datetime server
#   uv run cllm-mcp list-tools "uvx mcp-server-time"
#
#   # Call a specific tool
#   uv run cllm-mcp call-tool "uvx mcp-server-time" \
#     "get_current_time" '{}'
