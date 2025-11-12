# CLLM-MCP Daemon Architecture - Quick Reference

## Quick Facts

| Aspect | Detail |
|--------|--------|
| **Entry Point** | `cllm-mcp` (unified command) from `cllm_mcp/main.py` |
| **Daemon Server** | `mcp_daemon.py` - Listens on Unix socket, manages MCP server processes |
| **Config Discovery** | Auto-finds: `./mcp-config.json`, `~/.config/cllm-mcp/config.json`, `/etc/cllm-mcp/config.json` |
| **Socket Path** | Default: `/tmp/mcp-daemon.sock`, configurable via `--socket` or `MCP_DAEMON_SOCKET` env var |
| **Communication** | JSON over Unix sockets, 1MB message limit, newline-delimited |
| **Server Caching** | Server ID = MD5 hash of command (first 12 chars). Same command = cached server |
| **Mode Selection** | Auto-detects daemon, falls back to direct mode if unavailable |

---

## Daemon Initialization

What the daemon knows at startup:
- Socket path
- That it should listen for connections
- Zero servers initially (lazy loading)

What the daemon does NOT know:
- Configuration files
- Server definitions
- Which servers should auto-start
- Environment variables to apply

**Key principle**: Daemon is entirely reactive to client requests.

---

## Configuration System

### Discovery Order (First Match Wins)
1. `--config` argument (explicit path)
2. `./mcp-config.json` or `./.mcp-config.json` (current dir)
3. `~/.config/cllm-mcp/config.json` (home)
4. `/etc/cllm-mcp/config.json` (system)
5. No config found → None

### Config File Format
```json
{
  "mcpServers": {
    "server-name": {
      "command": "uvx mcp-server-name",
      "args": ["arg1", "arg2"],
      "description": "Human-readable description",
      "env": {
        "VAR_NAME": "value"
      }
    }
  }
}
```

### Server Resolution
- Input: `"time"` (server name) or `"uvx mcp-server-time"` (command)
- Output: `("uvx mcp-server-time", "time")` or `("uvx mcp-server-time", None)`
- If config exists and name matches → use config command + args
- If no config or name doesn't match → treat as literal command

---

## Daemon Protocol

### Socket Communication
- **Transport**: Unix domain socket (AF_UNIX, SOCK_STREAM)
- **Format**: JSON + newline delimiter
- **Timeout**: 1s for detection, 30s for tools, 5s for control

### Request Types

**Start Server**
```json
{"command": "start", "server": "ID", "server_command": "..."}
```

**Call Tool**
```json
{"command": "call", "server": "ID", "tool": "TOOL_NAME", "arguments": {...}}
```

**List Tools (Single Server)**
```json
{"command": "list", "server": "ID"}
```

**List All Tools (All Servers)**
```json
{"command": "list-all"}
```

**Get Status**
```json
{"command": "status"}
```

---

## Information Flow

### To Daemon
- Full server commands
- Tool names and parameters
- Control signals (start, stop, status, shutdown)

### From Daemon
- Tool definitions and results
- Status information
- Error messages

### NOT Shared
- Config file paths
- Config file contents
- Server metadata (descriptions, env vars)
- Client preferences

**Rationale**: Daemon stays stateless and config-agnostic.

---

## Unified Command Dispatcher Workflow

### For Tool Calls (list-tools, call-tool)

```
1. Parse global options (--config, --socket, --no-daemon, etc.)
2. Load config (if available)
   - find_config_file() → auto-discover
   - load_config() → parse JSON
   - validate_config() → check structure
3. Resolve server reference
   - "time" → "uvx mcp-server-time" (if in config)
   - "uvx mcp-server-time" → "uvx mcp-server-time" (literal)
4. Detect daemon availability
   - Check --no-daemon flag
   - Try to connect and ping daemon
   - Choose mode: daemon or direct
5. Execute
   - Daemon mode: Send JSON request via socket
   - Direct mode: Spawn subprocess with MCPClient
6. Display results
```

### For Daemon Commands (daemon start/stop/status)

```
1. Resolve socket path (arg > env > default)
2. Execute:
   - start: Fork daemon process, listen on socket
   - stop: Send shutdown command
   - status: Query running servers
   - restart: stop + start
```

### For Config Commands (config list/validate)

```
1. Find config file
2. Load and validate JSON
3. Display results
   - list: Show all servers with metadata
   - validate: Check syntax and executability
```

---

## Entry Points & Command Routing

### Current (main branch)
```
cllm-mcp → cllm_mcp/main.py:main()
```

### Commands
```
cllm-mcp list-tools [server]        → handle_list_tools()
cllm-mcp call-tool [server] [tool] [params] → handle_call_tool()
cllm-mcp interactive [server]       → handle_interactive()
cllm-mcp daemon start|stop|status|restart   → handle_daemon()
cllm-mcp config list|validate       → handle_config()
```

### Global Options
```
--config FILE           Config file path (overrides auto-discovery)
--socket PATH          Daemon socket path (default: /tmp/mcp-daemon.sock)
--no-daemon            Force direct mode (disable daemon detection)
--daemon-timeout SECS  Detection timeout (default: 1.0)
--verbose              Show debug output (mode selection, config resolution)
```

---

## Key Data Structures

### MCPDaemon
```python
{
  socket_path: "/tmp/mcp-daemon.sock",
  servers: {
    "a1b2c3d4e5f6": MCPClient(running subprocess),
    "f1e2d3c4b5a6": MCPClient(running subprocess),
    ...
  },
  lock: threading.Lock(),  # Thread-safe access
  running: bool  # Graceful shutdown flag
}
```

### Configuration
```python
{
  "mcpServers": {
    "name": {
      "command": "...",
      "args": [...],
      "description": "...",
      "env": {...}
    }
  }
}
```

---

## Testing Checklist

```bash
# Config discovery
cllm-mcp config list                    # Find config auto
cllm-mcp --config /path config list     # Use explicit path

# Daemon detection
cllm-mcp daemon start                   # Start daemon
cllm-mcp --verbose list-tools "..."     # Should say "daemon mode"
cllm-mcp daemon stop                    # Stop daemon
cllm-mcp --verbose list-tools "..."     # Should say "direct mode"

# Server resolution
cllm-mcp list-tools "server-name"       # Should resolve from config
cllm-mcp list-tools "uvx mcp-server-x"  # Should work as literal command

# Daemon control
cllm-mcp daemon status                  # Show active servers
cllm-mcp daemon restart                 # Restart daemon
```

---

## Current Gaps (Not Yet Implemented)

1. **Daemon config awareness** - Daemon can't load config file on startup
2. **Environment variable application** - Config has env vars, but daemon doesn't apply them
3. **Auto-start servers** - No way to pre-load servers on daemon startup
4. **Config in status output** - `daemon status` doesn't show config metadata
5. **Hot-reload config** - No way to update config without restarting daemon
6. **Backward compatibility aliases** - `mcp-cli` and `mcp-daemon` not in pyproject.toml yet

---

## Architecture Decision

The architecture intentionally keeps daemon and config separate:

**Client Responsibility:**
- Discover and load config
- Resolve server names to commands
- Apply environment variables
- Choose daemon vs. direct mode

**Daemon Responsibility:**
- Listen for requests
- Cache and manage server processes
- Execute tool calls
- Report status

This separation means:
- Daemon stays simple and stateless
- Multiple clients can share same daemon
- Config can change without daemon restart
- Direct mode works identically without daemon

---

## Files at a Glance

| File | Purpose |
|------|---------|
| `mcp_daemon.py` | Daemon server, request handling, process caching (436 lines) |
| `mcp_cli.py` | Client impl, direct mode, daemon client funcs (450 lines) |
| `cllm_mcp/main.py` | Unified dispatcher, command routing (400 lines) |
| `cllm_mcp/config.py` | Config loading, validation, resolution (310 lines) |
| `cllm_mcp/daemon_utils.py` | Daemon detection, socket path resolution (71 lines) |
| `cllm_mcp/socket_utils.py` | Socket communication protocol (186 lines) |

---

## Next Steps

To further integrate configuration:

1. Add `--config` option to `cllm-mcp daemon start`
2. Load and validate config at daemon startup
3. Apply environment variables when spawning server subprocesses
4. Include config metadata in daemon status output
5. Consider configuration hot-reload capability

---
