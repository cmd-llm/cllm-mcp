#!/bin/bash
# Example: Filesystem operations using MCP CLI
# This demonstrates how an LLM can perform file operations via bash scripts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
MCP_WRAPPER="$SCRIPT_DIR/mcp-wrapper.sh"

echo "=== MCP CLI Filesystem Operations Example ==="
echo

# Create a temporary directory for testing
TEST_DIR="/tmp/mcp-test-$$"
mkdir -p "$TEST_DIR"

echo "Test directory: $TEST_DIR"
echo

# Update config to use our test directory
cat > /tmp/mcp-config-temp.json <<EOF
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "$TEST_DIR"]
    }
  }
}
EOF

export MCP_CONFIG_FILE="/tmp/mcp-config-temp.json"

echo "1. List available filesystem tools:"
echo "   Command: $MCP_WRAPPER filesystem list-tools"
echo
"$MCP_WRAPPER" filesystem list-tools | head -20
echo

echo "2. Write a file:"
echo "   Creating test.txt with sample content..."
"$MCP_WRAPPER" filesystem call-tool write_file "{
  \"path\": \"$TEST_DIR/test.txt\",
  \"content\": \"Hello from MCP CLI!\\nThis is a test file.\\nLine 3.\"
}"
echo "   ✓ File written"
echo

echo "3. Read the file back:"
echo "   Command: call-tool read_file"
CONTENT=$("$MCP_WRAPPER" filesystem call-tool read_file "{\"path\": \"$TEST_DIR/test.txt\"}")
echo "$CONTENT" | jq -r '.content[0].text'
echo

echo "4. List directory contents:"
"$MCP_WRAPPER" filesystem call-tool list_directory "{\"path\": \"$TEST_DIR\"}" | jq -r '.content[0].text'
echo

echo "5. Create a subdirectory and another file:"
mkdir -p "$TEST_DIR/subdir"
"$MCP_WRAPPER" filesystem call-tool write_file "{
  \"path\": \"$TEST_DIR/subdir/nested.txt\",
  \"content\": \"This is a nested file.\"
}"
echo "   ✓ Nested file created"
echo

echo "6. List directory recursively:"
"$MCP_WRAPPER" filesystem call-tool list_directory "{\"path\": \"$TEST_DIR\"}" | jq -r '.content[0].text'
echo

# Cleanup
echo "Cleaning up test directory..."
rm -rf "$TEST_DIR"
rm -f /tmp/mcp-config-temp.json
echo "✓ Cleanup complete"
echo

echo "=== Example Complete ==="
echo
echo "This demonstrates how simple bash scripts can handle MCP operations"
echo "that would normally require tool definitions in the LLM's context window."
