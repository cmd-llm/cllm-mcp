# cllm-mcp - CLI for Model Context Protocol

A high-performance, zero-dependency Python CLI utility for invoking MCP (Model Context Protocol) tools directly from bash scripts. Designed to reduce LLM token usage by eliminating the need to load tool definitions into the context window, and to accelerate batch operations with persistent daemon mode.

## The Problem

When using MCP servers with LLMs, tool definitions consume significant tokens:
- **Token cost per server**: 2,000-5,000 tokens for full tool definitions and schemas
- **Repetitive invocation**: Multiple tool calls require constant LLM reasoning overhead
- **Inefficiency**: Scripted/deterministic tasks still consume tokens for MCP protocol handling

## The Solution

**cllm-mcp** enables:

1. **Direct tool invocation** - Call MCP tools from bash without LLM involvement (~50-100 tokens per operation)
2. **Reduced token usage** - 80-95% reduction in context window consumption
3. **High performance** - Daemon mode provides 10-60x speedup for batch operations
4. **Seamless integration** - Works transparently with or without daemon mode
5. **Zero dependencies** - Uses only Python standard library for maximum portability

## Architecture

```
┌─────────────────┐
│   LLM / Agent   │
└────────┬────────┘
         │ calls bash script
         ▼
┌─────────────────┐
│  cllm-mcp CLI   │
│   (command)     │
└────────┬────────┘
         │ invokes
         ▼
┌─────────────────┐
│   MCP Client    │ ◄─── Core Implementation
└────────┬────────┘
         │ JSON-RPC over stdio
         ▼
┌─────────────────┐
│   MCP Server    │ (filesystem, github, etc.)
└─────────────────┘
```

## Quick Start

### Unified Command Architecture

The modern entry point is `cllm-mcp` - a single command that intelligently handles both direct and daemon modes:

```bash
# List tools from an MCP server
cllm-mcp list-tools "npx -y @modelcontextprotocol/server-filesystem /tmp"

# Call a tool
cllm-mcp call-tool "npx -y @modelcontextprotocol/server-filesystem /tmp" \
  read_file '{"path": "/tmp/test.txt"}'

# Interactive exploration
cllm-mcp interactive "npx -y @modelcontextprotocol/server-filesystem /tmp"

# Daemon management
cllm-mcp daemon start      # Start daemon in background
cllm-mcp daemon status     # Check daemon status
cllm-mcp daemon stop       # Stop daemon

# Configuration management
cllm-mcp config list       # List configured servers
cllm-mcp config validate   # Validate configuration
cllm-mcp config show       # Display full configuration
```

**Implementation**: `cllm_mcp/main.py` (Architecture Decision Record: ADR-0003)

### Smart Daemon Detection

The `cllm-mcp` command automatically:
1. Detects if daemon is running (1s timeout check)
2. Uses daemon if available for faster performance
3. Falls back to direct mode if daemon unavailable (graceful degradation)
4. Works identically in both modes - no code changes needed

### Module Architecture

```
cllm_mcp/                    # Package structure
├── main.py                  # Unified command dispatcher (entry point)
├── config.py                # Configuration management (ADR-0004)
├── daemon_utils.py          # Daemon detection & socket path resolution
└── socket_utils.py          # Shared socket communication utilities
```

**Architecture Decisions**:
- **ADR-0003**: Unified daemon/client command architecture
- **ADR-0004**: CLLM-style configuration with hierarchical overrides
- **ADR-0005**: Auto-initialization of configured servers on daemon startup
- **ADR-0007**: Dropped legacy Python script entry points for modern `cllm-mcp` command

## Core Features

The `cllm-mcp` command provides all functionality needed for MCP server interaction:

**Key Capabilities:**

- Initialize connections to MCP servers
- List available tools with examples
- Execute tool calls with JSON parameters
- Interactive exploration mode
- Daemon mode for high-performance batch operations
- Configuration management with CLLM standards
- Auto-initialization of configured servers

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

4. (Optional) Create configuration file:

```bash
cp mcp-config.example.json mcp-config.json
# Edit mcp-config.json with your server configurations
```

### Running the CLI

You can run the CLI tool directly after installation:

```bash
# Using installed command
cllm-mcp list-tools filesystem

# Using uv run (during development)
uv run cllm-mcp list-tools filesystem

# Or activate the virtual environment
source .venv/bin/activate
cllm-mcp list-tools filesystem
```

## Usage Examples

### Method 1: Direct Server Specification

List and call tools by directly specifying the server command:

```bash
# List tools
cllm-mcp list-tools "npx -y @modelcontextprotocol/server-filesystem /tmp"

# Call a tool
cllm-mcp call-tool "npx -y @modelcontextprotocol/server-filesystem /tmp" \
  read_file '{"path": "/tmp/test.txt"}'

# Interactive exploration
cllm-mcp interactive "npx -y @modelcontextprotocol/server-filesystem /tmp"
```

**Best for**: One-off commands, scripting without configuration

### Method 2: Configuration-Based (Recommended)

Configure servers once, reference them by name:

#### 1. Create Configuration

Configuration files are resolved in this order (highest priority wins):
1. CLI argument: `cllm-mcp --config /path/to/config.json`
2. Environment variable: `CLLM_MCP_CONFIG=/path/to/config.json`
3. Current directory: `./mcp-config.json`
4. Project directory: `./.cllm/mcp-config.json`
5. Home directory: `~/.cllm/mcp-config.json`

Create `.cllm/mcp-config.json` in your project:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "description": "File operations"
    },
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "your_token_here"
      },
      "description": "GitHub API access",
      "autoStart": true,
      "optional": false
    }
  }
}
```

#### 2. Use Configured Servers

```bash
# List tools from configured server
cllm-mcp list-tools filesystem

# Call a tool
cllm-mcp call-tool filesystem read_file '{"path": "/tmp/test.txt"}'

# Interactive mode
cllm-mcp interactive filesystem

# Manage configuration
cllm-mcp config list          # List configured servers
cllm-mcp config validate      # Validate configuration
cllm-mcp config show          # Display full configuration
```

**Best for**: Production workflows, batch scripts, team projects

### Method 3: Daemon Mode for Batch Operations

For scripts making multiple tool calls:

```bash
# Start daemon (auto-initializes configured servers)
cllm-mcp daemon start

# Daemon automatically manages server connections
cllm-mcp call-tool filesystem read_file '{"path": "/tmp/file1.txt"}'
cllm-mcp call-tool filesystem read_file '{"path": "/tmp/file2.txt"}'
cllm-mcp call-tool filesystem read_file '{"path": "/tmp/file3.txt"}'

# Check daemon status
cllm-mcp daemon status

# Stop when done
cllm-mcp daemon stop
```

**Performance**: 10-60x faster than direct mode for multiple operations

**Best for**: Batch processing, repeated operations, performance-critical scripts

## Integration with LLMs

LLMs can delegate MCP operations to bash scripts, reducing context window usage by 80-95%:

### Before (LLM Token Overhead)

```
LLM Context:
- Full MCP protocol knowledge (500+ tokens)
- Tool definitions & schemas (1500-4000 tokens per server)
- Connection management logic (200+ tokens)
─────────────────────────────────────
Total: 2,200-4,700 tokens per server
```

### After (Minimal Token Usage)

```
LLM Instructions:
"To list filesystem tools: cllm-mcp list-tools filesystem
 To read a file: cllm-mcp call-tool filesystem read_file '{\"path\": \"...\"}'
 To write a file: cllm-mcp call-tool filesystem write_file '{\"path\": \"...\", \"content\": \"...\"}'

─────────────────────────────────────
Total: 50-100 tokens for simple instructions
```

### Example LLM System Prompt

```
You have access to the following bash commands for file and GitHub operations:

## File Operations
- List available filesystem tools:
  cllm-mcp list-tools filesystem

- Read a file:
  cllm-mcp call-tool filesystem read_file '{"path": "<file_path>"}'

- Write to a file:
  cllm-mcp call-tool filesystem write_file '{"path": "<file_path>", "content": "<content>"}'

## GitHub Operations
- List available GitHub tools:
  cllm-mcp list-tools github

- Create an issue:
  cllm-mcp call-tool github create_issue '{"owner": "...", "repo": "...", "title": "...", "body": "..."}'

When you need to perform file operations or GitHub actions, use these commands.
The tools will execute immediately and return results in JSON format.
```

## Common MCP Servers

Quick reference for popular MCP servers. Use `cllm-mcp list-tools <server>` to see all available tools.

### Filesystem Operations

```bash
# Configure in .cllm/mcp-config.json:
# "filesystem": {
#   "command": "npx",
#   "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
# }

# Usage:
cllm-mcp list-tools filesystem
cllm-mcp call-tool filesystem read_file '{"path": "/tmp/file.txt"}'
cllm-mcp call-tool filesystem write_file '{"path": "/tmp/file.txt", "content": "Hello"}'
cllm-mcp call-tool filesystem list_directory '{"path": "/tmp"}'
```

### GitHub Operations

```bash
# Configure in .cllm/mcp-config.json:
# "github": {
#   "command": "npx",
#   "args": ["@modelcontextprotocol/server-github"],
#   "env": {"GITHUB_TOKEN": "your_token"}
# }

# Usage:
cllm-mcp list-tools github
cllm-mcp call-tool github create_issue '{
  "owner": "username",
  "repo": "repository",
  "title": "Bug Report",
  "body": "Description"
}'
```

### Time & Date Utilities

```bash
# Configure in .cllm/mcp-config.json:
# "time": {
#   "command": "uvx",
#   "args": ["mcp-server-time"]
# }

# Usage:
cllm-mcp list-tools time
cllm-mcp call-tool time get_current_time '{}'
```

### Web Search (Multiple Options Available)

```bash
# Brave Search:
# "brave-search": {
#   "command": "npx",
#   "args": ["@modelcontextprotocol/server-brave-search"],
#   "env": {"BRAVE_API_KEY": "your_key"}
# }

# Usage:
cllm-mcp call-tool brave-search search '{"query": "MCP protocol"}'
```

### Database Operations (SQLite)

```bash
# Configure in .cllm/mcp-config.json:
# "sqlite": {
#   "command": "npx",
#   "args": ["@modelcontextprotocol/server-sqlite", "/path/to/db.sqlite"]
# }

# Usage:
cllm-mcp call-tool sqlite query '{"sql": "SELECT * FROM users LIMIT 10"}'
```

## Configuration Format

Configuration uses CLLM-style hierarchy. Server definitions go in `.cllm/mcp-config.json`:

```json
{
  "mcpServers": {
    "server_name": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-name", "arg1"],
      "description": "Description of what this server does",
      "env": {
        "API_KEY": "your_api_key"
      },
      "autoStart": true,
      "optional": false
    }
  }
}
```

### Server Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes | Executable to run (e.g., `npx`, `python`, `uvx`) |
| `args` | array | Yes | Command-line arguments as array |
| `description` | string | No | Human-readable server description |
| `env` | object | No | Environment variables to set (e.g., API keys) |
| `autoStart` | boolean | No | Auto-start when daemon launches (default: false) |
| `optional` | boolean | No | Don't fail daemon startup if server fails (default: false) |

### Configuration Resolution (ADR-0004)

Files are searched in this order (highest priority wins):

1. **CLI argument**: `cllm-mcp --config /path/to/config.json`
2. **Environment variable**: `CLLM_MCP_CONFIG=/path/to/config.json`
3. **Current directory**: `./mcp-config.json`
4. **Project directory**: `./.cllm/mcp-config.json`
5. **Home directory**: `~/.cllm/mcp-config.json`

**Recommended structure**: Use `.cllm/mcp-config.json` in your project root for version control.

### Example: Multi-Server Configuration

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "description": "File operations",
      "autoStart": true
    },
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "description": "GitHub API access",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      },
      "autoStart": true,
      "optional": false
    },
    "sqlite": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-sqlite", "/tmp/app.db"],
      "description": "SQLite database",
      "autoStart": false,
      "optional": true
    }
  }
}
```

## Advanced Usage

### Creating Custom Tool Wrappers

Build specialized bash scripts on top of cllm-mcp:

```bash
#!/bin/bash
# github-issue.sh - Helper for GitHub operations

COMMAND="$1"

case "$COMMAND" in
  list)
    cllm-mcp list-tools github
    ;;
  create)
    OWNER="$2"
    REPO="$3"
    TITLE="$4"
    BODY="$5"
    cllm-mcp call-tool github create_issue "{
      \"owner\": \"$OWNER\",
      \"repo\": \"$REPO\",
      \"title\": \"$TITLE\",
      \"body\": \"$BODY\"
    }"
    ;;
  get)
    OWNER="$2"
    REPO="$3"
    ISSUE_NUM="$4"
    cllm-mcp call-tool github get_issue "{
      \"owner\": \"$OWNER\",
      \"repo\": \"$REPO\",
      \"issue_number\": $ISSUE_NUM
    }"
    ;;
  *)
    echo "Usage: $0 {list|create|get} [args]"
    exit 1
    ;;
esac
```

Usage: `./github-issue.sh create myorg myrepo "Bug report" "Details here"`

### Error Handling

The CLI returns appropriate exit codes:

- `0` - Success
- `1` - Error (with error message to stderr)

Example error handling:

```bash
#!/bin/bash

if ! output=$(cllm-mcp call-tool filesystem read_file '{"path": "/tmp/file.txt"}' 2>&1); then
    echo "Error reading file: $output" >&2
    exit 1
fi

echo "File content: $output"
```

### Chaining Operations with jq

Combine tools with JSON processing:

```bash
#!/bin/bash
# Example: List files in directory, read each one, create GitHub issues

REPO_OWNER="$1"
REPO_NAME="$2"
TARGET_DIR="$3"

# Start daemon for batch operations
cllm-mcp daemon start

# List files in directory
files=$(cllm-mcp call-tool filesystem list_directory "{\"path\": \"$TARGET_DIR\"}" \
  | jq -r '.contents[].name')

for file in $files; do
  echo "Processing $file..."

  # Read file content
  content=$(cllm-mcp call-tool filesystem read_file "{\"path\": \"$TARGET_DIR/$file\"}")

  # Create issue with file content
  cllm-mcp call-tool github create_issue "{
    \"owner\": \"$REPO_OWNER\",
    \"repo\": \"$REPO_NAME\",
    \"title\": \"File Report: $file\",
    \"body\": $(echo "$content" | jq -R -s '.')
  }"
done

# Stop daemon
cllm-mcp daemon stop
```

### Parallel Operations

Process multiple items in parallel:

```bash
#!/bin/bash
# Process files concurrently

# Start daemon
cllm-mcp daemon start

# Process multiple files in background
for file in /tmp/file1.txt /tmp/file2.txt /tmp/file3.txt; do
  (
    cllm-mcp call-tool filesystem read_file "{\"path\": \"$file\"}" > "/tmp/output-$(basename $file)"
  ) &
done

# Wait for all background jobs
wait

# Stop daemon
cllm-mcp daemon stop
```

## Daemon Mode (Performance Optimization)

For scripts making multiple MCP tool calls, daemon mode provides **10-60x performance improvement** by keeping servers running and reusing connections.

### How It Works

The daemon maintains persistent MCP server processes and communicates via Unix domain sockets:

```
┌──────────────────────┐
│   Your Bash Script   │
└──────────┬───────────┘
           │ TCP-like Unix Socket (fast IPC)
           │ Auto-detected by cllm-mcp
           ▼
┌──────────────────────┐
│   MCP Daemon         │ ◄─── Manages server pool
│   (auto-detects)     │      Reuses connections
└──────────┬───────────┘
           │
        ┌──┴──┬──────┬────────┐
        ▼     ▼      ▼        ▼
    [filesystem] [github] [sqlite] [time]
    (persistent MCP servers)
```

### Automatic Daemon Detection

The `cllm-mcp` command automatically detects and uses daemon when available:

```bash
# Step 1: Start daemon (usually once at script start)
cllm-mcp daemon start

# Step 2: Any subsequent cllm-mcp commands automatically use daemon
cllm-mcp call-tool filesystem read_file '{"path": "/tmp/file1.txt"}'
cllm-mcp call-tool filesystem read_file '{"path": "/tmp/file2.txt"}'
# ^ These run ~10-60x faster because daemon is reusing connections

# Step 3: Stop when done
cllm-mcp daemon stop
```

**No special flags needed!** The magic happens automatically.

### Performance Comparison

| Scenario | Direct Mode | Daemon Mode | Speedup |
|----------|-------------|-------------|---------|
| Single call | ~200ms | ~200ms | 1x |
| 10 calls | ~2000ms | ~100-200ms | 10-20x |
| 100 calls | ~20000ms | ~500-1000ms | 20-40x |

### Detailed Daemon Management

```bash
# Start daemon (initializes configured servers if autoStart: true)
cllm-mcp daemon start

# Start in foreground (for debugging)
cllm-mcp daemon start --foreground

# Check daemon status
cllm-mcp daemon status

# Check status with JSON output
cllm-mcp daemon status --json

# Restart daemon
cllm-mcp daemon restart

# Stop daemon
cllm-mcp daemon stop
```

### Auto-Initialization with ADR-0005

When daemon starts, it automatically initializes servers marked with `autoStart: true`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/tmp"],
      "autoStart": true,          // ← Starts automatically
      "optional": false           // ← Daemon startup fails if this fails
    },
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "autoStart": false,         // ← Manual start only
      "optional": true            // ← Won't fail daemon startup if fails
    }
  }
}
```

### Example: Batch File Processing

```bash
#!/bin/bash
# Process 100 files efficiently with daemon

# Start daemon once
cllm-mcp daemon start

# Process files (automatic daemon detection, fast IPC)
for i in {1..100}; do
    echo "Processing file $i..."
    cllm-mcp call-tool filesystem read_file "{\"path\": \"/tmp/file$i.txt\"}"
done

# Clean up
cllm-mcp daemon stop
```

Performance: ~100-200ms total vs ~20000ms without daemon

### Advanced: Custom Socket Path

Use non-default socket location:

```bash
# Start daemon with custom socket
cllm-mcp daemon start --socket /var/run/my-mcp.sock

# Commands automatically use custom socket
cllm-mcp call-tool filesystem read_file '{"path": "/tmp/test.txt"}'
```

### When to Use Daemon Mode

✅ **Use Daemon Mode When:**
- Making multiple MCP tool calls (3+)
- Batch processing files or data
- Performance is critical
- Running inside a container or service
- Script can manage daemon lifecycle

❌ **Skip Daemon Mode When:**
- Single one-off tool call
- Running in extremely restricted environments
- Cannot manage daemon lifecycle (e.g., serverless functions)

### Troubleshooting Daemon

**Daemon won't start:**

```bash
# Check if already running
cllm-mcp daemon status

# Clean up stale socket and retry
rm -f /tmp/mcp-daemon.sock
cllm-mcp daemon start
```

**Command slow despite daemon:**

```bash
# Verify daemon is running
cllm-mcp daemon status

# Check daemon logs
cllm-mcp daemon status --verbose
```

**Port/Socket conflicts:**

```bash
# Use custom socket location
cllm-mcp daemon start --socket /tmp/my-daemon.sock

# All subsequent commands will use it automatically
```

## Benefits

1. **Token Efficiency**: 80-95% reduction in context window usage by eliminating tool definitions
2. **Performance**: 10-60x speedup with daemon mode for batch operations
3. **Simplicity**: LLMs only need simple bash command syntax
4. **Flexibility**: Add new servers to configuration without updating LLM instructions
5. **Reusability**: Bash scripts are version-controllable and shareable
6. **Debugging**: Easier to test and debug tool invocations independently
7. **Zero Dependencies**: Uses only Python stdlib for maximum portability
8. **Seamless Integration**: Works transparently with or without daemon mode
9. **Standard Config Format**: CLLM-style configuration (`.cllm/mcp-config.json`)

## Limitations & Considerations

1. **No Dynamic Discovery**: Tools must be pre-configured (but LLM can call `list-tools`)
2. **JSON Parsing**: LLM must handle JSON responses (use `jq` for parsing)
3. **Direct Mode Overhead**: Each call spawns new server process (~200ms)
4. **Platform Dependency**: Requires Python 3.7+ and bash (Unix-like systems)
5. **Socket Files**: Daemon mode requires Unix socket support (not Windows WSL1)
6. **Manual Server Start**: Daemon doesn't auto-reconnect if server crashes (use health monitoring)

## Architecture Decision Records

All major design decisions are documented in `docs/decisions/`:

- **ADR-0001**: Adopted Vibe format for architecture decisions
- **ADR-0002**: Adopted `uv` package manager for dependency management
- **ADR-0003**: Unified daemon/client command architecture with smart detection
- **ADR-0004**: CLLM-style configuration hierarchy (`.cllm/mcp-config.json`)
- **ADR-0005**: Automatic daemon initialization of configured servers
- **ADR-0006**: Tool invocation examples in `list-tools` output
- **ADR-0007**: Dropped legacy Python scripts, modernized to single `cllm-mcp` command

See `docs/decisions/` directory for full details and rationale.

**Migration Note**: Legacy `python mcp_cli.py` and `python mcp_daemon.py` commands have been removed. Use `cllm-mcp` command instead. See [MIGRATION.md](docs/MIGRATION.md) for details.

## Future Enhancements

- [x] **Persistent server connections** (daemon mode) ✅ ADR-0005
- [x] **Unified command architecture** ✅ ADR-0003
- [x] **CLLM configuration** ✅ ADR-0004
- [x] **Auto-server initialization** ✅ ADR-0005
- [x] **Tool invocation examples in list output** ✅ ADR-0006
- [x] **Modernized entry points** ✅ ADR-0007
- [ ] Result formatting options (JSON, text, table)
- [ ] Caching of tool definitions
- [ ] Batch tool calling
- [ ] Retry and timeout policies
- [ ] Tool call logging and metrics

## Examples

The `examples/` directory contains working scripts demonstrating cllm-mcp:

- **quick-datetime-test.sh** - Simple time server test
- **file-operations.sh** - Read/write file examples
- **daemon-batch-processing.sh** - Efficient batch file processing with daemon
- **comprehensive-demo.sh** - Full feature walkthrough
- **README.md** - Detailed examples guide

Run examples with:
```bash
cd examples
./quick-datetime-test.sh
./daemon-batch-processing.sh
```

## Project Structure

```
.
├── cllm_mcp/                    # Package (entry point)
│   ├── main.py                  # Unified command dispatcher
│   ├── config.py                # Configuration management
│   ├── daemon_utils.py          # Daemon utilities
│   └── socket_utils.py          # Socket communication
├── docs/
│   ├── decisions/               # Architecture Decision Records
│   ├── MIGRATION.md             # Migration guide from legacy commands
│   └── testing/                 # Test documentation
├── examples/                    # Runnable example scripts
├── tests/                       # Comprehensive test suite
├── .cllm/mcp-config.json        # Project configuration
├── pyproject.toml               # Project metadata
├── README.md                    # This file
└── LICENSE                      # MIT License
```

## Testing

Run tests with:

```bash
# All tests
uv run pytest

# Specific markers
uv run pytest -m unit               # Fast unit tests
uv run pytest -m integration        # Integration tests
uv run pytest -m daemon             # Daemon tests

# With coverage
uv run pytest --cov=cllm_mcp
```

**Test Coverage**: 132+ tests across unit and integration suites

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-thing`)
3. Add tests for your changes
4. Ensure all tests pass (`uv run pytest`)
5. Submit a pull request

See CONTRIBUTING.md for detailed guidelines.

## License

MIT License - see LICENSE file for details

## Quick Reference

### Common Commands

```bash
# Start daemon
cllm-mcp daemon start

# List tools
cllm-mcp list-tools filesystem

# Call a tool
cllm-mcp call-tool filesystem read_file '{"path": "/tmp/file.txt"}'

# Interactive mode
cllm-mcp interactive filesystem

# Configuration
cllm-mcp config list
cllm-mcp config validate

# Daemon control
cllm-mcp daemon status
cllm-mcp daemon stop
```

### Configuration Locations

1. `~/.cllm/mcp-config.json` (global)
2. `./.cllm/mcp-config.json` (project)
3. `./mcp-config.json` (legacy)
4. `CLLM_MCP_CONFIG` environment variable
5. `--config` CLI argument

## Resources

- **Model Context Protocol**: https://modelcontextprotocol.io
- **MCP Servers**: https://github.com/modelcontextprotocol/servers
- **Claude Integration**: https://docs.anthropic.com/claude/docs/model-context-protocol
- **Vibe ADR Format**: https://github.com/toucanmeister/vibe-adr

---

**Project**: cllm-mcp v1.0.0
**Status**: Actively developed
**Last Updated**: November 2025

Generated with [Claude Code](https://claude.com/claude-code)
