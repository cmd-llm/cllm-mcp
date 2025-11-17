# cllm-mcp

CLI tool for calling MCP (Model Context Protocol) servers from bash. Reduces LLM token usage by offloading tool invocation to command-line, with daemon mode for batch operations.

**Key features:**
- Direct MCP tool invocation from bash (eliminating 80-95% of context overhead)
- Daemon mode with 10-60x speedup for batch operations
- Configuration management with CLLM-style hierarchy
- Zero external dependencies (Python stdlib only)

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

### Basic Usage

```bash
# List tools
cllm-mcp list-tools "npx -y @modelcontextprotocol/server-filesystem /tmp"

# Call a tool
cllm-mcp call-tool "npx -y @modelcontextprotocol/server-filesystem /tmp" \
  read_file '{"path": "/tmp/test.txt"}'

# Interactive REPL
cllm-mcp interactive "npx -y @modelcontextprotocol/server-filesystem /tmp"

# Daemon mode (for batch operations)
cllm-mcp daemon start
cllm-mcp call-tool filesystem read_file '{"path": "/tmp/file.txt"}'
cllm-mcp daemon stop
```

### Smart Daemon Detection

Commands automatically detect and use daemon when running, with graceful fallback to direct mode.

### Configuration

Configure servers in `.cllm/mcp-config.json`:

```bash
cllm-mcp config list       # List configured servers
cllm-mcp config validate   # Validate configuration
cllm-mcp config show       # Display full configuration
```

## Installation

```bash
# Clone and install
git clone <repository-url>
cd cllm-mcp
uv sync

# Run via uv or from installed location
uv run cllm-mcp --help
# or
cllm-mcp --help
```

## Usage Examples

### Direct Server Invocation

```bash
# List tools
cllm-mcp list-tools "npx -y @modelcontextprotocol/server-filesystem /tmp"

# Call a tool
cllm-mcp call-tool "npx -y @modelcontextprotocol/server-filesystem /tmp" \
  read_file '{"path": "/tmp/test.txt"}'
```

### Configuration-Based (Recommended)

Create `.cllm/mcp-config.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "autoStart": true
    },
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
      "autoStart": true
    }
  }
}
```

Then reference by name:

```bash
cllm-mcp list-tools filesystem
cllm-mcp call-tool filesystem read_file '{"path": "/tmp/test.txt"}'
cllm-mcp interactive filesystem
```

### Batch Operations with Daemon

```bash
cllm-mcp daemon start

# Multiple operations run fast (10-60x speedup)
for i in {1..100}; do
  cllm-mcp call-tool filesystem read_file '{"path": "/tmp/file'$i'.txt"}'
done

cllm-mcp daemon stop
```

## Integration with LLMs

LLMs can delegate MCP operations to bash, reducing context by 80-95%. Example system prompt:

```
You have access to MCP servers via bash commands:

cllm-mcp list-tools <server>         # List available tools
cllm-mcp call-tool <server> <tool>   # Execute tool with JSON args

Example:
cllm-mcp call-tool filesystem read_file '{"path": "/tmp/file.txt"}'
cllm-mcp call-tool github create_issue '{"owner": "user", "repo": "repo", "title": "..."}'

All results are returned as JSON.
```

## Common MCP Servers

Popular servers to configure:

- **filesystem**: `npx -y @modelcontextprotocol/server-filesystem /tmp`
- **github**: `npx @modelcontextprotocol/server-github` (requires `GITHUB_TOKEN`)
- **sqlite**: `npx @modelcontextprotocol/server-sqlite /path/to/db.sqlite`
- **brave-search**: `npx @modelcontextprotocol/server-brave-search` (requires `BRAVE_API_KEY`)
- **time**: `uvx mcp-server-time`

Use `cllm-mcp list-tools <server>` to see available tools.

## Configuration

Store in `.cllm/mcp-config.json` (searched in order: `--config` arg → `CLLM_MCP_CONFIG` env → `./mcp-config.json` → `./.cllm/mcp-config.json` → `~/.cllm/mcp-config.json`).

Schema:

```json
{
  "mcpServers": {
    "server_name": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-name", "arg1"],
      "env": {"API_KEY": "value"},
      "autoStart": true,
      "optional": false
    }
  }
}
```

- **command** (required): Executable (e.g., `npx`, `python`, `uvx`)
- **args** (required): Command arguments as array
- **env**: Environment variables
- **autoStart**: Auto-start when daemon launches
- **optional**: Don't fail daemon if server fails

## Advanced Usage

### Error Handling

Returns exit code `0` on success, `1` on error with message to stderr:

```bash
if ! output=$(cllm-mcp call-tool filesystem read_file '{"path": "/tmp/file.txt"}' 2>&1); then
  echo "Error: $output" >&2
  exit 1
fi
```

### Processing with jq

Chain operations using JSON processing:

```bash
# List files and process each
cllm-mcp daemon start
cllm-mcp call-tool filesystem list_directory '{"path": "/tmp"}' \
  | jq -r '.contents[].name' \
  | while read file; do
    cllm-mcp call-tool filesystem read_file "{\"path\": \"/tmp/$file\"}"
  done
cllm-mcp daemon stop
```

## Daemon Mode

Daemon keeps servers running for **10-60x speedup** on batch operations. Auto-detection: no flags needed.

```bash
cllm-mcp daemon start              # Start once
cllm-mcp call-tool fs read_file '{...'  # Auto-detects daemon
cllm-mcp daemon stop               # Stop when done
```

**Management:**

```bash
cllm-mcp daemon start              # Start background daemon
cllm-mcp daemon start --foreground  # Start in foreground (debug)
cllm-mcp daemon status             # Check if running
cllm-mcp daemon restart            # Restart
cllm-mcp daemon stop               # Stop
```

**Configuration:**

- Servers with `autoStart: true` initialize automatically
- Use `optional: true` to ignore startup failures for that server
- Custom socket: `cllm-mcp daemon start --socket /path/to/socket`

## Project Structure

```
cllm_mcp/
├── main.py              # Command dispatcher
├── client.py            # Client implementation
├── config.py            # Configuration management
├── daemon.py            # Daemon commands
├── daemon_server.py     # Daemon server
├── daemon_lifecycle.py   # Daemon lifecycle
├── daemon_utils.py      # Daemon utilities
├── json_rpc_client.py   # JSON-RPC communication
├── socket_utils.py      # Socket utilities
└── env_expansion.py     # Environment variable expansion

docs/
├── decisions/           # Architecture Decision Records (ADR 0001-0008)
├── MIGRATION.md         # Legacy command migration guide
└── testing/             # Test documentation

tests/                   # Comprehensive test suite (100+ tests)
examples/                # Example scripts
```

## Testing

```bash
uv run pytest              # All tests
uv run pytest -m unit      # Fast unit tests
uv run pytest -m daemon    # Daemon tests
uv run pytest --cov        # With coverage
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for your changes
4. Ensure tests pass
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Architecture Decisions

See `docs/decisions/` for ADRs:

- **ADR-0001**: Vibe format for decisions
- **ADR-0002**: `uv` package manager
- **ADR-0003**: Unified daemon/client command
- **ADR-0004**: CLLM-style configuration
- **ADR-0005**: Auto-initialize servers
- **ADR-0006**: Tool invocation examples
- **ADR-0007**: Modernized entry points
- **ADR-0008**: Environment variable support

## Resources

- [Model Context Protocol](https://modelcontextprotocol.io)
- [MCP Servers](https://github.com/modelcontextprotocol/servers)
- [Claude Integration Guide](https://docs.anthropic.com/claude/docs/model-context-protocol)

---

**License**: MIT
**Status**: Actively maintained
**Python**: 3.7+
