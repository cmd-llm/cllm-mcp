#!/bin/bash
# Comprehensive cllm-mcp Demo
#
# This script demonstrates all major features of cllm-mcp:
# 1. Working with server names from config
# 2. Working with full server commands
# 3. Daemon management
# 4. Listing all tools in the daemon
# 5. Calling tools with different parameters
# 6. JSON output for programmatic use
#
# Prerequisites:
#   - Python 3.8+
#   - uv (Python package manager): https://docs.astral.sh/uv/
#
# Usage:
#   ./examples/comprehensive-demo.sh

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
section() {
	echo ""
	echo -e "${BLUE}==== $1 ====${NC}"
	echo ""
}

subsection() {
	echo -e "${CYAN}→ $1${NC}"
}

success() {
	echo -e "${GREEN}✓ $1${NC}"
}

info() {
	echo -e "${YELLOW}ℹ $1${NC}"
}

code() {
	echo -e "${MAGENTA}  $ $1${NC}"
}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

cd "${PROJECT_ROOT}"

echo -e "${BLUE}"
cat <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         🚀 cllm-mcp Comprehensive Feature Demo 🚀            ║
║                                                              ║
║    Demonstrating daemon management, server configuration,   ║
║              and tool execution with cllm-mcp               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# ============================================================================
section "PART 1: Configuration and Server Discovery"
# ============================================================================

subsection "Validating configuration"
code "uv run cllm-mcp config validate"
uv run cllm-mcp config validate
success "Configuration is valid"

subsection "Listing configured servers"
code "uv run cllm-mcp config list"
uv run cllm-mcp config list

# ============================================================================
section "PART 2: Daemon Lifecycle Management"
# ============================================================================

subsection "Checking daemon status"
code "uv run cllm-mcp daemon status"
uv run cllm-mcp daemon status || info "Daemon not running (this is OK)"

subsection "Starting the daemon in background"
code "uv run cllm-mcp daemon start &"
uv run cllm-mcp daemon start >/dev/null 2>&1 &
DAEMON_PID=$!
sleep 2
success "Daemon started (PID: ${DAEMON_PID})"

subsection "Checking daemon status again"
code "uv run cllm-mcp daemon status"
uv run cllm-mcp daemon status

# ============================================================================
section "PART 3: Working with Server Names from Config"
# ============================================================================

subsection "List tools by server name (from config)"
info "Using server name 'time' which is configured in mcp-config.json"
code "uv run cllm-mcp list-tools time"
uv run cllm-mcp list-tools time | head -20
echo "  ..."

subsection "Call a tool using server name"
code "uv run cllm-mcp call-tool time \"get_current_time\" '{\"timezone\": \"America/New_York\"}'"
uv run cllm-mcp call-tool time "get_current_time" '{"timezone": "America/New_York"}'

success "Tool executed successfully!"

# ============================================================================
section "PART 4: Working with Direct Server Commands"
# ============================================================================

subsection "List tools by full server command"
info "Using full command instead of config name (backward compatible)"
code 'uv run cllm-mcp list-tools "uvx mcp-server-time"'
uv run cllm-mcp list-tools "uvx mcp-server-time" | head -20
echo "  ..."

subsection "Convert time between timezones"
code "uv run cllm-mcp call-tool \"uvx mcp-server-time\" \"convert_time\" '{\"source_timezone\": \"America/New_York\", \"time\": \"14:30\", \"target_timezone\": \"Europe/London\"}'"
uv run cllm-mcp call-tool "uvx mcp-server-time" "convert_time" \
	'{"source_timezone": "America/New_York", "time": "14:30", "target_timezone": "Europe/London"}'

# ============================================================================
section "PART 5: Viewing All Daemon Tools"
# ============================================================================

subsection "List all tools from all active daemon servers"
info "Shows a summary of all tools currently cached in the daemon"
code "uv run cllm-mcp list-tools"
uv run cllm-mcp list-tools

subsection "Get all tools in JSON format"
info "Useful for programmatic processing"
code "uv run cllm-mcp list-tools --json | jq '.total_tools'"
TOTAL_TOOLS=$(uv run cllm-mcp list-tools --json | jq '.total_tools')
echo -e "${GREEN}Total tools in daemon: ${TOTAL_TOOLS}${NC}"

# ============================================================================
section "PART 6: Different Output Formats"
# ============================================================================

subsection "JSON output for programmatic use"
code "uv run cllm-mcp list-tools time --json"
echo "First tool from 'time' server:"
uv run cllm-mcp list-tools time --json | jq '.[0] | {name, description}' | head -10

subsection "Verbose mode for debugging"
code "uv run cllm-mcp --verbose list-tools time"
uv run cllm-mcp --verbose list-tools time 2>&1 | head -10

# ============================================================================
section "PART 7: Direct Mode (Without Daemon)"
# ============================================================================

subsection "Force direct mode with --no-daemon flag"
info "Bypasses daemon even if available (useful for debugging)"
code "uv run cllm-mcp --no-daemon list-tools time"
uv run cllm-mcp --no-daemon list-tools time | head -20
echo "  ..."

# ============================================================================
section "PART 8: Daemon Cleanup"
# ============================================================================

subsection "Check final daemon status"
code "uv run cllm-mcp daemon status"
uv run cllm-mcp daemon status

subsection "Stop the daemon"
code "uv run cllm-mcp daemon stop"
uv run cllm-mcp daemon stop
success "Daemon stopped"

# ============================================================================
section "SUMMARY"
# ============================================================================

cat <<'EOF'

✅ Demo Complete! You've learned:

1. 📋 Configuration Management
   - Validating config files
   - Listing configured servers
   - Using server names from config

2. 🎯 Server Commands
   - Using short names: `cllm-mcp list-tools time`
   - Using full commands: `cllm-mcp list-tools "uvx mcp-server-time"`
   - Both work seamlessly!

3. 🚀 Daemon Management
   - Start: `cllm-mcp daemon start`
   - Status: `cllm-mcp daemon status`
   - Stop: `cllm-mcp daemon stop`
   - List all: `cllm-mcp list-tools` (no args)

4. 🔧 Tool Execution
   - List tools: `cllm-mcp list-tools <server>`
   - Call tools: `cllm-mcp call-tool <server> <tool> <json>`
   - JSON output: Add `--json` flag

5. 🔍 Debugging
   - Verbose mode: `cllm-mcp --verbose <command>`
   - Direct mode: `cllm-mcp --no-daemon <command>`
   - View config: `cllm-mcp config list`

📖 Quick Reference:

   # Setup
   uv run cllm-mcp config validate
   uv run cllm-mcp daemon start

   # List tools
   uv run cllm-mcp list-tools time              # By config name
   uv run cllm-mcp list-tools                   # All daemon tools
   uv run cllm-mcp list-tools --json            # JSON format

   # Call tools
   uv run cllm-mcp call-tool time "get_current_time" '{"timezone": "UTC"}'

   # Cleanup
   uv run cllm-mcp daemon stop

🎓 Next Steps:
   - Edit mcp-config.json to add more MCP servers
   - Create bash scripts using cllm-mcp for automation
   - Use JSON output with jq for advanced filtering

EOF

echo -e "${BLUE}"
cat <<'EOF'
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
