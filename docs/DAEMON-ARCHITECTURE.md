# CLLM-MCP Daemon Architecture Analysis

## Overview

The cllm-mcp project implements a unified Model Context Protocol (MCP) command-line interface with daemon support for persistent server management. The architecture follows ADR-0003 (Unified Daemon/Client Command Architecture) to provide a single entry point while transparently leveraging daemon caching for performance.

---

## 1. Current Daemon Initialization and Configuration

### Entry Points

- **Main unified entry**: `cllm-mcp` (from `cllm_mcp/main.py`)
- **Legacy aliases** (for backward compatibility, not yet configured in pyproject.toml):
  - `mcp-cli` (from `mcp_cli.py`)
  - `mcp-daemon` (from `mcp_daemon.py`)

### Daemon Initialization Flow

#### What MCPDaemon Knows At Startup

1. **Socket path** - Unix domain socket location for IPC
   - Default: `/tmp/mcp-daemon.sock`
   - Configurable via command-line: `--socket PATH`
   - Environment variable: `MCP_DAEMON_SOCKET`

2. **Server cache** - Dictionary mapping server IDs to MCPClient instances
   - Key: MD5 hash of server command (first 12 chars)
   - Value: Active MCPClient object managing the subprocess
3. **Process management state**
   - Lock mechanism for thread-safe operations
   - Running flag for graceful shutdown
   - Zero initial servers (lazy loading)

#### Daemon Startup Process (mcp_daemon.py)

```python
# Startup sequence in daemon_start()
1. Check if daemon already running at socket path
2. Create MCPDaemon instance with socket_path
3. Register signal handlers (SIGINT, SIGTERM)
4. Run daemon server:
   - Clean up old socket
   - Create Unix socket and bind
   - Listen for connections
   - Accept connections in threads
   - Handle requests via handle_request()
```

### What Daemon Does NOT Know Initially

- Configuration files (config.json)
- Server definitions (commands, args, env vars)
- Which servers should be auto-started
- Client preferences or requirements
- Network topology or dependencies

**Key insight**: Daemon is entirely reactive - it learns about servers when clients request them.

---

## 2. Configuration Loading and Discovery

### config.py Module Architecture

#### Config Discovery Pipeline

**find_config_file()** implements priority-based discovery:

```
Priority order (first match wins):
1. Explicit path passed via --config argument
2. Current working directory:
   - mcp-config.json
   - .mcp-config.json
3. User home directory:
   - ~/.config/cllm-mcp/config.json
4. System directory:
   - /etc/cllm-mcp/config.json
5. Return None if nothing found
```

#### Configuration Structure

Expected JSON format in mcp-config.json:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "uvx mcp-server-name",
      "args": ["/path/to/arg1", "arg2"],
      "description": "Server description",
      "env": {
        "VAR_NAME": "value"
      }
    }
  }
}
```

#### Config Loading Workflow

```
load_config(path)
  └─ Expand home directory paths
  └─ Check file exists
  └─ Parse JSON
  └─ Return dict or raise ConfigError

validate_config(config)
  └─ Check 'mcpServers' exists
  └─ Validate each server has:
     ├─ 'command' field (required)
     ├─ 'args' is list (if present)
     ├─ 'env' is dict (if present)
     └─ 'description' is string (if present)
  └─ Collect all validation errors

resolve_server_ref(server_ref, config)
  └─ If server_ref matches config server name:
     ├─ Get server config
     ├─ Build full command (command + args)
     └─ Return (command, server_name)
  └─ Else treat as literal command:
     └─ Return (server_ref, None)

build_server_command(server_config)
  └─ Combine 'command' and 'args' into shell command string
```

#### Example Usage Flows

**Scenario 1: Named server from config**

```
Input: "time" (server name from config)
Config contains: {
  "mcpServers": {
    "time": {
      "command": "uvx mcp-server-time"
    }
  }
}
resolve_server_ref("time", config)
  └─ Returns: ("uvx mcp-server-time", "time")
```

**Scenario 2: Direct command (no config)**

```
Input: "uvx mcp-server-time" (full command)
resolve_server_ref("uvx mcp-server-time", None)
  └─ Returns: ("uvx mcp-server-time", None)
```

**Scenario 3: Config not found**

```
find_config_file() returns None
  └─ No config available
  └─ All server refs treated as literal commands
```

---

## 3. Daemon Protocol - Communication Format

### Socket Communication Layer (socket_utils.py)

#### Connection Protocol

**Transport**: Unix domain sockets (AF_UNIX, SOCK_STREAM)
**Message format**: JSON + newline delimiter
**Message size limit**: 1MB per message

#### Request-Response Cycle

```
1. Client creates SocketClient(socket_path, timeout)
2. Client calls connect():
   - Creates socket.socket(AF_UNIX, SOCK_STREAM)
   - Sets timeout
   - Connects to daemon socket
   - Raises ConnectionError if daemon not running

3. Client calls send_request(dict):
   - Encodes request as JSON + newline
   - Sends via socket
   - Receives response (up to first newline)
   - Decodes and returns as dict

4. Daemon receives:
   - handle_connection() reads up to 1MB or first newline
   - Parses JSON request
   - Routes to handle_request()
   - Returns JSON response + newline
```

#### Timeout Configuration

```python
DAEMON_CHECK_TIMEOUT = 1.0      # Quick availability check
DAEMON_TOOL_TIMEOUT = 30.0      # Extended timeout for tool execution
DAEMON_CTRL_TIMEOUT = 5.0       # Control commands (stop, status)
```

### Request Command Types

#### 1. Server Management

**Start Server**

```json
{
  "command": "start",
  "server": "server_id",
  "server_command": "full command string"
}

Response: {"success": true, "message": "..."}
          or {"success": false, "error": "..."}
```

**Stop Server**

```json
{
  "command": "stop",
  "server": "server_id"
}

Response: {"success": true, "message": "..."}
```

#### 2. Tool Operations

**Call Tool**

```json
{
  "command": "call",
  "server": "server_id",
  "tool": "tool_name",
  "arguments": {"param": "value"}
}

Response: {"success": true, "result": {...}}
          or {"success": false, "error": "...", "retry": true}
```

**List Tools**

```json
{
  "command": "list",
  "server": "server_id"
}

Response: {"success": true, "tools": [
  {
    "name": "tool_name",
    "description": "...",
    "inputSchema": {...}
  }
]}
```

**List All Tools (All Servers)**

```json
{
  "command": "list-all"
}

Response: {
  "success": true,
  "servers": {
    "server_id": {
      "tools": [...],
      "tool_count": N
    }
  },
  "server_count": M,
  "total_tools": P
}
```

#### 3. Daemon Control

**Get Status**

```json
{
  "command": "status"
}

Response: {
  "status": "running",
  "servers": ["server1", "server2"],
  "server_count": 2
}
```

**Shutdown**

```json
{
  "command": "shutdown"
}

Response: {"success": true, "message": "Daemon shutting down"}
```

### Server ID Generation

Server IDs are deterministic MD5 hashes of the command string:

```python
server_id = hashlib.md5(command.encode()).hexdigest()[:12]
```

This ensures:

- Same command always gets same ID
- Different commands get different IDs
- Multiple calls to same command reuse cached server
- Server IDs are predictable and reproducible

---

## 4. Information Flow Between Daemon and Client

### Data Flowing TO Daemon

1. **Server Commands**
   - Full command string (e.g., "uvx mcp-server-time")
   - Server ID (generated by client)
   - Arguments and parameters for tool calls

2. **Control Signals**
   - Start/stop requests
   - Status queries
   - Shutdown notification

### Data Flowing FROM Daemon

1. **Tool Information**
   - Tool names, descriptions, input schemas
   - Tool availability and capabilities

2. **Execution Results**
   - Tool call return values
   - Error messages and retry hints

3. **Status Information**
   - Running servers list
   - Server counts and tool counts
   - Daemon health status

### What Is NOT Shared

The daemon intentionally does NOT receive:

- Configuration file paths
- Configuration file contents
- Server descriptions or metadata
- Client preferences
- User identity or authentication

**Rationale**: Daemon remains stateless and configuration-agnostic. Clients are responsible for resolving server references to commands before sending to daemon.

---

## 5. Unified Command Dispatcher (main.py)

### Architecture Overview

The main.py module implements the unified command dispatcher that routes all operations through a single entry point while managing:

1. **Global configuration**
   - Config file discovery and loading
   - Configuration validation
2. **Daemon detection**
   - Check if daemon is running and responsive
   - Graceful fallback to direct mode
3. **Server reference resolution**
   - Convert server names to full commands
   - Use config if available, literal command if not
4. **Mode selection**
   - Automatically choose daemon vs. direct mode
   - Respect --no-daemon flag
   - Apply appropriate timeouts

### Command Flow for list-tools

```
cllm-mcp list-tools [server_name_or_command]
  │
  ├─ Parse args (extract --config, --socket, --no-daemon, etc.)
  │
  ├─ Call handle_list_tools(args)
  │   ├─ Load config (if available)
  │   │   ├─ find_config_file()
  │   │   └─ load_config() + validate_config()
  │   │
  │   ├─ Resolve server reference
  │   │   └─ resolve_server_ref(server_name, config)
  │   │       └─ Returns: (resolved_command, server_name_or_none)
  │   │
  │   ├─ Detect daemon availability
  │   │   └─ should_use_daemon()
  │   │       ├─ Check --no-daemon flag
  │   │       └─ Check if daemon socket is responsive
  │   │
  │   └─ Dispatch to cmd_list_tools()
  │       └─ Either daemon_list_tools() or direct MCPClient.list_tools()
  │
  └─ Display results
```

### Command Flow for call-tool

```
cllm-mcp call-tool server_name_or_command tool_name '{"param": "value"}'
  │
  ├─ Parse args
  │
  ├─ Call handle_call_tool(args)
  │   ├─ Load config (if available)
  │   ├─ Resolve server reference
  │   ├─ Detect daemon availability
  │   └─ Dispatch to cmd_call_tool()
  │       └─ Either daemon_call_tool() or direct MCPClient.call_tool()
  │
  └─ Display result
```

### Daemon Subcommands

```
cllm-mcp daemon start [--foreground]
  └─ Calls daemon_start(args)
  └─ Handles socket path resolution
  └─ May daemonize (double fork) unless --foreground

cllm-mcp daemon stop
  └─ Calls daemon_stop(args)
  └─ Sends shutdown command to daemon
  └─ Waits for cleanup

cllm-mcp daemon status [--json]
  └─ Calls daemon_status(args)
  └─ Displays running servers and tool counts

cllm-mcp daemon restart
  └─ Calls daemon_stop() then daemon_start()
  └─ Restarts with clean state
```

### Config Subcommands

```
cllm-mcp config list [--json]
  └─ Lists all configured servers with details
  └─ Shows command, args, description, env vars

cllm-mcp config validate
  └─ Checks configuration syntax and structure
  └─ Reports validation errors
  └─ Verifies commands are executable (if possible)
```

---

## 6. Configuration Integration Points

### Where Configuration is Needed

#### 1. Server Command Resolution (main.py, line 267)

```python
resolved_command, server_name = resolve_server_ref(args.server_command, config)
```

Clients pass server names instead of full commands.

#### 2. Daemon Initialization (mcp_daemon.py)

Currently: NOT integrated - daemon receives full commands only

**Integration needed for**:

- Auto-starting configured servers on daemon startup
- Server health checks using config metadata
- Applying environment variables from config
- Server descriptions in status output

#### 3. Environment Variable Application

Config supports per-server environment variables:

```json
{
  "env": {
    "OPENAI_API_KEY": "...",
    "LOG_LEVEL": "debug"
  }
}
```

**Current state**: NOT applied - clients must handle
**Integration needed**: Daemon should apply when starting servers

#### 4. Server Arguments

Config supports per-server command arguments:

```json
{
  "command": "python -m my_server",
  "args": ["/path/to/data", "--config", "settings.ini"]
}
```

**Current state**: Handled by build_server_command()
**Status**: READY to use, client-side

#### 5. Server Descriptions

Config supports metadata:

```json
{
  "description": "Provides access to local filesystem"
}
```

**Current state**: Displayed by `cllm-mcp config list`
**Status**: READY to use

---

## 7. Current Architecture Gaps and Next Steps

### Gap 1: Daemon Configuration Loading

**Current**: Daemon has zero knowledge of config files
**Needed**: Option to pre-load servers from config on startup

```bash
cllm-mcp daemon start --config /etc/mcp-config.json
  └─ Should auto-start configured servers
  └─ Should apply environment variables
```

### Gap 2: Environment Variable Application

**Current**: Config defines env vars but daemon ignores them
**Needed**: When starting server subprocess, apply env vars from config

### Gap 3: Server Auto-Registration

**Current**: Servers only exist after client requests them
**Needed**: Option to auto-start configured servers at daemon startup

### Gap 4: Configuration Hot-Reload

**Current**: No way to update config without restarting daemon
**Potential**: Add `cllm-mcp daemon reload-config` command

### Gap 5: Configuration Status in Daemon

**Current**: Daemon status doesn't show config-based metadata
**Needed**: Display server descriptions, args, env vars in `daemon status` output

---

## 8. Testing the Current Architecture

### Manual Test: Config Discovery

```bash
# Create config in current directory
echo '{"mcpServers": {"test": {"command": "echo hello"}}}' > mcp-config.json

# Test discovery
cllm-mcp config list
# Should find and display the config

# Test with explicit path
cllm-mcp --config /tmp/other-config.json config list
```

### Manual Test: Daemon Detection

```bash
# Start daemon
cllm-mcp daemon start

# Check detection (with verbose)
cllm-mcp --verbose list-tools "uvx mcp-server-time"
# Should show: "[mode] Using daemon mode (auto-detected)"

# Force direct mode
cllm-mcp --no-daemon --verbose list-tools "uvx mcp-server-time"
# Should show: "[mode] Using direct mode (daemon explicitly disabled)"

# Stop daemon
cllm-mcp daemon stop

# Check fallback
cllm-mcp --verbose list-tools "uvx mcp-server-time"
# Should show: "[mode] Using direct mode (daemon not available, fallback)"
```

### Manual Test: Configuration Resolution

```bash
# With server name from config
cllm-mcp list-tools "time"
# Should resolve to: "uvx mcp-server-time"

# With full command
cllm-mcp list-tools "uvx mcp-server-time"
# Should work directly without config lookup
```

---

## 9. Key Files and Their Responsibilities

| File                       | Lines | Purpose                                                        |
| -------------------------- | ----- | -------------------------------------------------------------- |
| `mcp_daemon.py`            | 436   | Daemon server implementation, request handling, server caching |
| `mcp_cli.py`               | 450   | Client implementation, direct mode and daemon client functions |
| `cllm_mcp/main.py`         | 400   | Unified dispatcher, command routing, daemon detection          |
| `cllm_mcp/config.py`       | 310   | Configuration loading, validation, server resolution           |
| `cllm_mcp/daemon_utils.py` | 71    | Daemon availability checking, socket path resolution           |
| `cllm_mcp/socket_utils.py` | 186   | Socket communication protocol, client implementation           |

---

## 10. Summary: Current State vs. Target State

### Current (As of main branch)

- Unified `cllm-mcp` entry point EXISTS
- Config discovery and loading: IMPLEMENTED
- Server reference resolution: IMPLEMENTED
- Daemon detection and fallback: IMPLEMENTED
- Configuration validation: IMPLEMENTED
- Daemon communication protocol: STABLE

### Still Needed for Full Integration

- [ ] Daemon configuration file awareness (--config on daemon start)
- [ ] Environment variable application from config
- [ ] Configuration-based server auto-start
- [ ] Config metadata in daemon status output
- [ ] Configuration hot-reload support
- [ ] Backward compatibility aliases in pyproject.toml (mcp-cli, mcp-daemon)

---
