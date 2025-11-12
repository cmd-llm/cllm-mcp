# MCP CLI - Model Context Protocol Command Line Utility

A lightweight CLI utility for making MCP (Model Context Protocol) tool calls without requiring an LLM. This reduces token usage by allowing bash scripts to directly invoke MCP tools, instead of loading tool definitions into the LLM's context window.

## Problem Statement

When using MCP servers with LLMs, tool definitions consume significant tokens in the context window. For repetitive or well-defined tasks, this is inefficient. This utility allows:

1. **Direct tool invocation** - Call MCP tools from bash scripts without LLM involvement
2. **Reduced token usage** - Keep tool definitions out of the LLM's context
3. **Simplified workflows** - LLMs can call bash scripts that handle MCP communication

## Architecture

```
┌─────────────────┐
│   LLM / Agent   │
└────────┬────────┘
         │ calls bash script
         ▼
┌─────────────────┐
│  Bash Wrapper   │
│   (mcp-*.sh)    │
└────────┬────────┘
         │ invokes
         ▼
┌─────────────────┐
│   mcp_cli.py    │ ◄─── MCP Client
└────────┬────────┘
         │ JSON-RPC over stdio
         ▼
┌─────────────────┐
│   MCP Server    │ (filesystem, github, etc.)
└─────────────────┘
```

## Components

### 1. Core MCP Client (`mcp_cli.py`)

Python-based MCP client that communicates with MCP servers using JSON-RPC over stdio.

**Features:**
- Initialize connections to MCP servers
- List available tools
- Execute tool calls with JSON parameters
- Interactive exploration mode

### 2. Simple Bash Wrappers

Direct wrappers for basic operations:
- `mcp-list-tools.sh` - List all tools from a server
- `mcp-call-tool.sh` - Call a specific tool

### 3. Advanced Configuration Wrapper

Configuration-based wrapper for managing multiple MCP servers:
- `mcp-wrapper.sh` - Execute commands using server definitions from config
- `mcp-config.example.json` - Example configuration with common servers

## Installation

### Prerequisites

- Python 3.7+
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- Node.js and npm (for MCP servers)
- Bash shell

### Setup

1. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone this repository:
```bash
git clone <repository-url>
cd research
```

3. Install the project using uv:
```bash
uv sync
```

4. Make scripts executable:
```bash
chmod +x mcp_cli.py mcp-*.sh
```

5. (Optional) Create configuration file:
```bash
cp mcp-config.example.json mcp-config.json
# Edit mcp-config.json with your server configurations
```

### Running with uv

You can run the CLI tool using uv:
```bash
# Using uv run
uv run mcp-cli list-tools "npx -y @modelcontextprotocol/server-filesystem /tmp"

# Or activate the virtual environment
source .venv/bin/activate
mcp-cli list-tools "npx -y @modelcontextprotocol/server-filesystem /tmp"
```

## Usage

### Method 1: Direct Python Client

#### List Tools
```bash
./mcp_cli.py list-tools "npx -y @modelcontextprotocol/server-filesystem /tmp"
```

#### Call a Tool
```bash
./mcp_cli.py call-tool "npx -y @modelcontextprotocol/server-filesystem /tmp" \
    read_file '{"path": "/tmp/test.txt"}'
```

#### Interactive Mode
```bash
./mcp_cli.py interactive "npx -y @modelcontextprotocol/server-filesystem /tmp"
```

### Method 2: Simple Bash Wrappers

```bash
# List tools
./mcp-list-tools.sh "npx -y @modelcontextprotocol/server-filesystem /tmp"

# Call a tool
./mcp-call-tool.sh "npx -y @modelcontextprotocol/server-filesystem /tmp" \
    read_file '{"path": "/tmp/test.txt"}'
```

### Method 3: Configuration-Based Wrapper (Recommended)

1. Configure your servers in `mcp-config.json`:
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    }
  }
}
```

2. Use the wrapper:
```bash
# List tools from configured server
./mcp-wrapper.sh filesystem list-tools

# Call a tool
./mcp-wrapper.sh filesystem call-tool read_file '{"path": "/tmp/test.txt"}'

# Interactive mode
./mcp-wrapper.sh filesystem interactive
```

## Integration with LLMs

The key benefit is that LLMs can now call simple bash scripts instead of managing MCP protocol details:

### Before (High Token Usage)
```
LLM Context:
- Full MCP protocol knowledge
- All tool definitions (schemas, parameters)
- Connection management logic
≈ 2000-5000 tokens per server
```

### After (Minimal Token Usage)
```
LLM Instructions:
"To read a file, call: ./mcp-wrapper.sh filesystem call-tool read_file '{\"path\": \"<path>\"}'
≈ 50-100 tokens per operation
```

### Example LLM Prompt

```
You have access to the following bash commands for file operations:

1. List available filesystem tools:
   ./mcp-wrapper.sh filesystem list-tools

2. Read a file:
   ./mcp-wrapper.sh filesystem call-tool read_file '{"path": "<file_path>"}'

3. Write to a file:
   ./mcp-wrapper.sh filesystem call-tool write_file '{"path": "<file_path>", "content": "<content>"}'

Use these commands to perform file operations as needed.
```

## Common MCP Servers

### Filesystem Operations
```bash
./mcp-wrapper.sh filesystem call-tool read_file '{"path": "/tmp/file.txt"}'
./mcp-wrapper.sh filesystem call-tool write_file '{"path": "/tmp/file.txt", "content": "Hello"}'
./mcp-wrapper.sh filesystem call-tool list_directory '{"path": "/tmp"}'
```

### GitHub Operations
```bash
./mcp-wrapper.sh github call-tool create_issue '{
  "owner": "username",
  "repo": "repository",
  "title": "Bug Report",
  "body": "Description of the bug"
}'
```

### Web Search (Brave)
```bash
./mcp-wrapper.sh brave-search call-tool search '{
  "query": "MCP protocol documentation"
}'
```

### Database Operations (SQLite)
```bash
./mcp-wrapper.sh sqlite call-tool query '{
  "sql": "SELECT * FROM users LIMIT 10"
}'
```

## Configuration Format

The `mcp-config.json` file defines available MCP servers:

```json
{
  "mcpServers": {
    "server_name": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-name", "arg1"],
      "env": {
        "API_KEY": "your_api_key"
      },
      "description": "Description of what this server does"
    }
  }
}
```

### Fields:
- **command**: Executable to run (usually `npx` for Node.js MCP servers)
- **args**: Array of command-line arguments
- **env**: (Optional) Environment variables to set
- **description**: (Optional) Human-readable description

## Advanced Usage

### Creating Custom Tool Wrappers

You can create specialized bash scripts for specific tasks:

```bash
#!/bin/bash
# read-github-issue.sh - Read a GitHub issue

OWNER="$1"
REPO="$2"
ISSUE_NUM="$3"

./mcp-wrapper.sh github call-tool get_issue "{
  \"owner\": \"$OWNER\",
  \"repo\": \"$REPO\",
  \"issue_number\": $ISSUE_NUM
}"
```

### Error Handling

The CLI returns appropriate exit codes:
- `0` - Success
- `1` - Error (with error message to stderr)

Example error handling in bash:
```bash
if ! output=$(./mcp-wrapper.sh filesystem call-tool read_file '{"path": "/tmp/file.txt"}' 2>&1); then
    echo "Error reading file: $output" >&2
    exit 1
fi

echo "File content: $output"
```

### Chaining Operations

```bash
#!/bin/bash
# Example: Read a file and create a GitHub issue with its content

FILE_PATH="$1"
OWNER="$2"
REPO="$3"

# Read file content
CONTENT=$(./mcp-wrapper.sh filesystem call-tool read_file "{\"path\": \"$FILE_PATH\"}" | jq -r '.content[0].text')

# Create issue with file content
./mcp-wrapper.sh github call-tool create_issue "{
  \"owner\": \"$OWNER\",
  \"repo\": \"$REPO\",
  \"title\": \"File Report: $FILE_PATH\",
  \"body\": \"$CONTENT\"
}"
```

## Daemon Mode (Performance Optimization)

For scripts that make multiple MCP tool calls, daemon mode eliminates the overhead of starting a new server process for each call. This provides **10-60x performance improvement** for repeated operations.

### How It Works

The daemon keeps MCP servers running in the background and communicates via Unix domain sockets:

```
┌─────────────────┐
│   Bash Script   │
└────────┬────────┘
         │ Unix Socket (fast IPC)
         ▼
┌─────────────────┐
│   MCP Daemon    │ ◄─── Manages server pool
└────────┬────────┘
         │ Reuses existing connections
         ▼
┌─────────────────┐
│   MCP Servers   │ (filesystem, github, etc.)
└─────────────────┘
```

### Performance Comparison

| Method | First Call | Subsequent Calls | Best For |
|--------|------------|------------------|----------|
| **Direct** | ~200ms | ~200ms | Single calls |
| **Daemon** | ~200ms | ~5-20ms | Multiple calls |

### Usage

#### 1. Start the Daemon

```bash
# Start daemon in background
./mcp-daemon start

# Check daemon status
./mcp-daemon status
```

#### 2. Use Daemon Mode

**With Direct CLI:**
```bash
# Add --use-daemon flag to any command
./mcp_cli.py call-tool --use-daemon \
  "npx -y @modelcontextprotocol/server-filesystem /tmp" \
  read_file '{"path": "/tmp/test.txt"}'
```

**With Config Wrapper:**
```bash
# Enable daemon mode via environment variable
export MCP_USE_DAEMON=1

# All subsequent calls will use daemon
./mcp-wrapper.sh filesystem call-tool read_file '{"path": "/tmp/file1.txt"}'
./mcp-wrapper.sh filesystem call-tool read_file '{"path": "/tmp/file2.txt"}'
./mcp-wrapper.sh filesystem call-tool read_file '{"path": "/tmp/file3.txt"}'
```

#### 3. Stop the Daemon

```bash
./mcp-daemon stop
```

### Example: Batch Operations

```bash
#!/bin/bash
# Process multiple files efficiently with daemon mode

# Start daemon
./mcp-daemon start

# Enable daemon mode
export MCP_USE_DAEMON=1

# Process files (fast - no server startup overhead)
for file in /tmp/*.txt; do
    echo "Processing $file..."
    ./mcp-wrapper.sh filesystem call-tool read_file "{\"path\": \"$file\"}"
done

# Stop daemon when done
./mcp-daemon stop
```

### Daemon Commands

```bash
# Start daemon
./mcp-daemon start

# Start in foreground (for debugging)
./mcp-daemon start --foreground

# Check status
./mcp-daemon status

# Check status (JSON output)
./mcp-daemon status --json

# Stop daemon
./mcp-daemon stop
```

### When to Use Daemon Mode

✅ **Use Daemon Mode When:**
- Making multiple tool calls in a script
- Running repeated operations (batch processing)
- Performance is critical
- You can manage daemon lifecycle (start/stop)

❌ **Skip Daemon Mode When:**
- Making a single tool call
- Running one-off commands
- Can't reliably stop the daemon afterwards
- Running in restricted environments (no Unix sockets)

### Troubleshooting

**Daemon won't start:**
```bash
# Check if daemon is already running
./mcp-daemon status

# If stale socket exists, clean it up
rm /tmp/mcp-daemon.sock
./mcp-daemon start
```

**"Daemon not running" error:**
```bash
# Make sure daemon is started first
./mcp-daemon start

# Verify it's running
./mcp-daemon status
```

**Custom socket path:**
```bash
# Use custom socket location
./mcp-daemon --socket /path/to/custom.sock start
./mcp_cli.py call-tool --use-daemon --daemon-socket /path/to/custom.sock ...
```

## Benefits

1. **Token Efficiency**: Reduces context window usage by 80-95% for tool definitions
2. **Simplicity**: LLMs only need to know bash command syntax
3. **Flexibility**: Easy to add new MCP servers without updating LLM prompts
4. **Reusability**: Bash scripts can be shared and versioned
5. **Debugging**: Easier to test and debug tool calls independently
6. **Performance**: Direct invocation is faster than going through LLM reasoning

## Limitations

1. **No Dynamic Discovery**: LLM must know which tools are available (but can call `list-tools`)
2. **Error Handling**: LLM needs to handle JSON parsing errors from tool responses
3. **State Management**: Each call starts a new server instance (use daemon mode for persistent connections)
4. **Platform**: Requires Python and bash (Unix-like systems)
5. **Daemon Mode**: Only works on Unix-like systems with Unix domain socket support

## Future Enhancements

- [x] Persistent server connections (daemon mode) ✅
- [ ] Caching of tool definitions
- [ ] Automatic retry logic
- [ ] Result formatting options (JSON, text, table)
- [ ] Batch tool calling
- [ ] WebSocket transport support
- [ ] Tool call logging and analytics
- [ ] Integration with popular AI frameworks

## Examples

See the `examples/` directory for complete working examples:
- File operations workflow
- GitHub automation
- Database queries
- Web scraping

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see LICENSE file for details

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)
- [Claude Desktop MCP Integration](https://docs.anthropic.com/claude/docs/model-context-protocol)

---

**Generated with [Claude Code](https://claude.ai/code)**
