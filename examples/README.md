# cllm-mcp Examples

This directory contains example scripts demonstrating various features of the cllm-mcp tool.

## Quick Start

### 1. Comprehensive Demo (Recommended)

The **best starting point** - shows all major features in one script:

```bash
./examples/comprehensive-demo.sh
```

This covers:
- Configuration management and validation
- Daemon lifecycle (start, status, stop)
- Working with server names from config
- Working with direct server commands
- Listing all daemon tools
- Different output formats (text, JSON, verbose)
- Direct mode (without daemon)

**Duration**: ~2-3 minutes

---

## Individual Examples

### Configuration & Setup

#### `setup-datetime-config.sh`
Sets up the daemon with time server configuration:
```bash
./examples/setup-datetime-config.sh
```

Use this to:
- Create or validate `mcp-config.json`
- Start the daemon in foreground mode
- Test basic tool operations

---

### Daemon Management

#### `start-daemon-with-datetime.sh`
Starts the daemon in foreground mode with datetime server:
```bash
./examples/start-daemon-with-datetime.sh
```

Use this when you:
- Want to see daemon output in real-time
- Need to debug daemon behavior
- Are first learning how the daemon works

---

### Tool Usage Examples

#### `quick-datetime-test.sh`
Quick test of datetime tools with daemon:
```bash
./examples/quick-datetime-test.sh
```

Demonstrates:
- Listing tools from a specific server
- Calling tools with parameters
- Using both daemon and direct modes

#### `daemon-batch-processing.sh`
Batch processing example - calling multiple tools in sequence:
```bash
./examples/daemon-batch-processing.sh
```

Use this for:
- Processing multiple commands efficiently
- Leveraging daemon caching for performance
- Batch automation workflows

#### `file-operations.sh`
Examples of file system operations through MCP:
```bash
./examples/file-operations.sh
```

Demonstrates:
- Reading files
- Writing files
- Directory operations
- Using the filesystem MCP server

---

## Key Concepts Demonstrated

### 1. Server Configuration
All examples use the `mcp-config.json` file to define available servers:
```json
{
  "mcpServers": {
    "time": {
      "command": "uvx",
      "args": ["mcp-server-time"],
      "description": "Time utilities"
    }
  }
}
```

### 2. Multiple Ways to Reference Servers

**By name (from config):**
```bash
uv run cllm-mcp list-tools time
```

**By full command:**
```bash
uv run cllm-mcp list-tools "uvx mcp-server-time"
```

Both work identically!

### 3. Daemon Benefits

The daemon caches servers for faster repeated calls:

```bash
# First call: ~2-3 seconds (server startup)
uv run cllm-mcp list-tools time

# Second call: ~100-500ms (cached)
uv run cllm-mcp list-tools time

# List all cached tools (no startup)
uv run cllm-mcp list-tools
```

### 4. Output Formats

**Human-readable (default):**
```bash
uv run cllm-mcp list-tools time
```

**JSON (for automation):**
```bash
uv run cllm-mcp list-tools time --json
```

**Verbose (for debugging):**
```bash
uv run cllm-mcp --verbose list-tools time
```

---

## Common Workflows

### Setup and Configure

```bash
# 1. Validate configuration
uv run cllm-mcp config validate

# 2. List available servers
uv run cllm-mcp config list

# 3. Start daemon (background)
uv run cllm-mcp daemon start

# 4. Check daemon status
uv run cllm-mcp daemon status
```

### Explore Tools

```bash
# List all cached tools (requires daemon)
uv run cllm-mcp list-tools

# List specific server tools
uv run cllm-mcp list-tools time

# Get JSON for filtering
uv run cllm-mcp list-tools time --json | jq '.[].name'
```

### Call Tools

```bash
# Simple tool call
uv run cllm-mcp call-tool time "get_current_time" '{"timezone": "UTC"}'

# With pretty output
uv run cllm-mcp call-tool time "get_current_time" '{"timezone": "UTC"}' | jq
```

### Automation

```bash
# Batch processing in shell script
for tz in "America/New_York" "Europe/London" "Asia/Tokyo"; do
  echo "Current time in $tz:"
  uv run cllm-mcp call-tool time "get_current_time" "{\"timezone\": \"$tz\"}" | jq '.content[0].text'
done
```

### Debug Issues

```bash
# Verbose output
uv run cllm-mcp --verbose list-tools time

# Direct mode (bypass daemon)
uv run cllm-mcp --no-daemon list-tools time

# Check daemon status
uv run cllm-mcp daemon status

# Stop and restart daemon
uv run cllm-mcp daemon stop
sleep 1
uv run cllm-mcp daemon start
```

---

## Adding New Servers

1. Edit `mcp-config.json`:

```json
{
  "mcpServers": {
    "time": { ... },
    "my-server": {
      "command": "npx",
      "args": ["@organization/my-mcp-server"],
      "description": "My custom MCP server"
    }
  }
}
```

2. Validate:
```bash
uv run cllm-mcp config validate
```

3. Use it:
```bash
uv run cllm-mcp list-tools my-server
```

---

## Troubleshooting

### Daemon won't start
```bash
# Check what's using the socket
lsof /tmp/mcp-daemon.sock

# Remove stale socket
rm /tmp/mcp-daemon.sock

# Start daemon again
uv run cllm-mcp daemon start
```

### Tools not found
```bash
# Verify configuration
uv run cllm-mcp config validate

# Check daemon status
uv run cllm-mcp daemon status

# List all tools
uv run cllm-mcp list-tools
```

### Slow operations
```bash
# Start daemon to cache servers
uv run cllm-mcp daemon start

# Subsequent calls will be faster (cached)
uv run cllm-mcp list-tools time
```

---

## Performance Tips

1. **Use the daemon** - Caches servers for 5-10x faster repeated calls
2. **Reference by name** - `uv run cllm-mcp list-tools time` is shorter and clearer
3. **Batch operations** - Group multiple tool calls together
4. **Use JSON output** - Pipe to `jq` for filtering and processing

---

## Prerequisites

- Python 3.8+
- uv package manager: https://docs.astral.sh/uv/
- Node.js (for `npx` to run npm-based MCP servers)
- Bash 4.0+ (for most example scripts)

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Getting Help

- Run `uv run cllm-mcp --help` for CLI help
- Run `uv run cllm-mcp <command> --help` for specific command help
- Check `mcp-config.json` for server configuration examples
- Review main README.md for architecture details
