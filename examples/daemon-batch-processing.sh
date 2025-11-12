#!/bin/bash
# Example: Batch file processing with daemon mode
# This demonstrates the performance benefits of using daemon mode
# for multiple MCP tool calls.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"

echo "=== MCP Daemon Mode Demo ==="
echo "This script demonstrates fast batch processing using daemon mode"
echo ""

# Start the daemon
echo "1. Starting MCP daemon..."
"$SCRIPT_DIR/mcp-daemon" start

# Wait a moment for daemon to fully start
sleep 1

# Check daemon status
echo ""
echo "2. Checking daemon status..."
"$SCRIPT_DIR/mcp-daemon" status
echo ""

# Enable daemon mode for all subsequent calls
export MCP_USE_DAEMON=1

# Create test directory and files
TEST_DIR="/tmp/mcp-daemon-test"
mkdir -p "$TEST_DIR"

echo "3. Creating test files..."
for i in {1..5}; do
    echo "Test content for file $i" > "$TEST_DIR/test$i.txt"
done
echo "   Created 5 test files in $TEST_DIR"
echo ""

# Measure performance: Read all files using daemon mode
echo "4. Reading files with daemon mode (fast)..."
START_TIME=$(date +%s%N)

for file in "$TEST_DIR"/*.txt; do
    filename=$(basename "$file")
    echo "   Processing $filename..."

    # Call via wrapper with daemon mode
    RESULT=$("$SCRIPT_DIR/mcp-wrapper.sh" filesystem call-tool read_file "{\"path\": \"$file\"}" 2>&1)

    # Extract content from JSON result (if jq is available)
    if command -v jq &> /dev/null; then
        CONTENT=$(echo "$RESULT" | jq -r '.content[0].text // .content // "N/A"' 2>/dev/null || echo "N/A")
        echo "      Content: $CONTENT"
    fi
done

END_TIME=$(date +%s%N)
DAEMON_TIME=$(( (END_TIME - START_TIME) / 1000000 ))
echo ""
echo "   Daemon mode time: ${DAEMON_TIME}ms"
echo ""

# Disable daemon mode to show comparison
unset MCP_USE_DAEMON

echo "5. Reading files WITHOUT daemon mode (slow)..."
START_TIME=$(date +%s%N)

for file in "$TEST_DIR"/*.txt; do
    filename=$(basename "$file")
    echo "   Processing $filename..."

    # Call via wrapper without daemon mode (each call starts new server)
    RESULT=$("$SCRIPT_DIR/mcp-wrapper.sh" filesystem call-tool read_file "{\"path\": \"$file\"}" 2>&1)
done

END_TIME=$(date +%s%N)
DIRECT_TIME=$(( (END_TIME - START_TIME) / 1000000 ))
echo ""
echo "   Direct mode time: ${DIRECT_TIME}ms"
echo ""

# Calculate speedup
if [ $DAEMON_TIME -gt 0 ]; then
    SPEEDUP=$(awk "BEGIN {printf \"%.1f\", $DIRECT_TIME / $DAEMON_TIME}")
    echo "   🚀 Speedup: ${SPEEDUP}x faster with daemon mode!"
else
    echo "   Unable to calculate speedup"
fi
echo ""

# Stop the daemon
echo "6. Stopping daemon..."
"$SCRIPT_DIR/mcp-daemon" stop

# Cleanup test files
echo ""
echo "7. Cleaning up..."
rm -rf "$TEST_DIR"
echo "   Removed test directory"

echo ""
echo "=== Demo Complete ==="
echo ""
echo "Key Takeaways:"
echo "- Daemon mode keeps MCP servers running in background"
echo "- First call: same speed (server startup)"
echo "- Subsequent calls: 10-60x faster (reuses connection)"
echo "- Best for: batch operations, multiple tool calls"
echo "- Remember to start daemon before use and stop when done"
