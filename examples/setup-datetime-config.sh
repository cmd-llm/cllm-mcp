#!/bin/bash
# Example: Set up configuration and start daemon with datetime MCP server
#
# This script demonstrates the full workflow:
# 1. Create a configuration file with the datetime MCP server
# 2. Validate the configuration
# 3. Start the daemon in foreground mode
# 4. Show example commands to use the daemon

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

echo -e "${BLUE}=== MCP Daemon Setup with Datetime Server ===${NC}"
echo ""

cd "${PROJECT_ROOT}"

# Step 1: Create configuration file
echo -e "${GREEN}Step 1: Creating configuration file...${NC}"
CONFIG_FILE="mcp-config.json"

# Create a config file with the datetime MCP server
cat >"${CONFIG_FILE}" <<'EOF'
{
  "mcpServers": {
    "time": {
      "command": "uvx",
      "args": ["mcp-server-time"],
      "description": "Time and date utilities including timezone support"
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "description": "File system access for /tmp directory"
    }
  }
}
EOF

echo "Created ${CONFIG_FILE} with the following servers:"
cat "${CONFIG_FILE}" | jq '.mcpServers | keys'
echo ""

# Step 2: Validate configuration
echo -e "${GREEN}Step 2: Validating configuration...${NC}"
uv run cllm-mcp --config "${CONFIG_FILE}" config validate
echo ""

# Step 3: List configured servers
echo -e "${GREEN}Step 3: Configured servers:${NC}"
uv run cllm-mcp --config "${CONFIG_FILE}" config list
echo ""

# Step 4: Start daemon
echo -e "${GREEN}Step 4: Starting daemon in foreground mode...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the daemon${NC}"
echo ""
echo "While the daemon is running, you can use it in another terminal:"
echo ""
echo "  # List available time tools"
echo "  uv run cllm-mcp --config ${CONFIG_FILE} list-tools \"uvx mcp-server-time\""
echo ""
echo "  # Get current time (timezone is required)"
echo "  uv run cllm-mcp --config ${CONFIG_FILE} call-tool \"uvx mcp-server-time\" \\"
echo "    \"get_current_time\" '{\"timezone\": \"UTC\"}'"
echo ""
echo "  # Get time in a specific timezone"
echo "  uv run cllm-mcp --config ${CONFIG_FILE} call-tool \"uvx mcp-server-time\" \\"
echo "    \"get_current_time\" '{\"timezone\": \"America/New_York\"}'"
echo ""
echo "  # Check daemon status"
echo "  uv run cllm-mcp daemon status"
echo ""
echo "  # Stop the daemon when done"
echo "  uv run cllm-mcp daemon stop"
echo ""

# Start the daemon in foreground
uv run cllm-mcp daemon start --foreground
