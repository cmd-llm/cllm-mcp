# ADR-0003: Unified Daemon/Client Command Architecture

## Status

Proposed

## Context

The cllm-mcp project currently provides two separate command-line entry points for interacting with MCP servers:

1. **`mcp-cli`** - Direct client mode that spawns a new MCP server process per invocation
2. **`mcp-daemon`** - Separate daemon management command with its own lifecycle

This separation creates friction in the user experience:

- Users must remember two different commands with different workflows
- Transitioning from direct to daemon mode requires understanding different CLIs
- Configuration-based usage (`mcp-wrapper.sh`) hides daemon complexity but adds indirection
- New users face a steeper learning curve
- The daemon benefits (10-60x faster for batch operations) aren't obvious without explicit `--use-daemon` awareness

### Current Architecture Issues

**Multiple command patterns:**
```bash
# Direct mode (current default)
mcp-cli list-tools "python -m server"
mcp-cli call-tool "python -m server" "tool-name" '{"param": "value"}'

# Daemon mode (requires explicit flag)
mcp-cli list-tools --use-daemon "python -m server"
mcp-daemon start
mcp-daemon status
mcp-daemon stop
```

**The ideal flow should be:**
```bash
# Single unified command
cllm-mcp list-tools "python -m server"           # Auto-uses daemon if available
cllm-mcp daemon start                            # Start persistent daemon
cllm-mcp daemon status                           # Check daemon status
```

### Design Goals

1. **Single entry point**: One command (`cllm-mcp`) for all operations
2. **Transparent daemon usage**: Automatically use daemon when available, fall back to direct mode
3. **Explicit daemon control**: Subcommands for daemon lifecycle management
4. **Zero breaking changes**: Maintain backward compatibility with `mcp-cli` and `mcp-daemon`
5. **Graceful degradation**: Works perfectly whether daemon is running or not
6. **Clear user intent**: Subcommand structure makes operation explicit

## Decision

We will implement a unified `cllm-mcp` command with the following architecture:

### CLI Structure

```
cllm-mcp [global-options] <command> [command-options]

Global Options:
  --config FILE                 Path to MCP configuration file
  --socket PATH                 Unix socket path for daemon (default: /tmp/mcp-daemon.sock)
  --no-daemon                   Force direct mode, don't use daemon
  --daemon-timeout SECONDS      Timeout for daemon operations (default: 30)

Commands:
  list-tools                    List available tools from MCP server
  call-tool                     Execute a tool on MCP server
  interactive                   Interactive REPL for MCP server
  daemon                        Daemon lifecycle management
    daemon start                Start the persistent MCP daemon
    daemon status               Show daemon status and running servers
    daemon stop                 Stop the daemon
    daemon shutdown             Graceful shutdown with cleanup
    daemon restart              Restart the daemon
  config                        Configuration management
    config list                 List available servers from config
    config validate             Validate configuration file
```

### Operational Modes

#### Mode 1: Direct Execution (Default, Transparent)
```bash
# Run tool immediately, spawn server if needed
$ cllm-mcp list-tools "python -m my_server"
```

**Behavior:**
1. Check if daemon is available (socket exists and responds)
2. If available: Use daemon to call tools (fast)
3. If unavailable: Spawn direct subprocess (degraded but functional)
4. No user configuration needed

#### Mode 2: Explicit Direct Mode
```bash
# Force direct mode without daemon, even if available
$ cllm-mcp --no-daemon list-tools "python -m my_server"
```

**Behavior:**
- Always spawn new server process
- Useful for debugging or when daemon is misbehaving
- Predictable performance characteristics

#### Mode 3: Daemon Mode (Explicit Control)
```bash
# Start the daemon
$ cllm-mcp daemon start

# Daemon now available for fast repeated calls
$ cllm-mcp list-tools "python -m my_server"
$ cllm-mcp call-tool "python -m my_server" "tool-name" '{"param": "value"}'

# Check what's running
$ cllm-mcp daemon status

# Clean shutdown
$ cllm-mcp daemon stop
```

**Behavior:**
- Explicit daemon lifecycle control
- All tool calls automatically use daemon when running
- Server processes cached across calls
- Manual cleanup with explicit `stop` command

### Implementation Details

#### Phase 1: Unified Command Wrapper
Create a new `cllm-mcp` entry point that dispatches to existing code:

```python
# cllm_mcp/main.py
def main():
    parser = create_unified_parser()
    args = parser.parse_args()

    if args.command == 'daemon':
        # Dispatch to mcp_daemon.py logic
        from . import mcp_daemon
        return mcp_daemon.handle_command(args)

    elif args.command in ['list-tools', 'call-tool', 'interactive']:
        # Dispatch to mcp_cli.py logic with daemon support
        from . import mcp_cli
        return mcp_cli.handle_command(args)

    elif args.command == 'config':
        # New: Configuration management
        from . import config
        return config.handle_command(args)
```

**Key features:**
- Minimal new code, reuses existing logic
- Global socket path management
- Consistent timeout handling
- Error messages guide users to solutions

#### Phase 2: Smart Daemon Detection
Enhance existing daemon client code to auto-detect availability:

```python
def should_use_daemon(socket_path: str, no_daemon_flag: bool) -> bool:
    """
    Determines if daemon should be used.

    Returns True if:
    - no_daemon_flag is False (not explicitly disabled)
    - Socket file exists
    - Daemon responds to a quick ping within timeout
    """
    if no_daemon_flag:
        return False

    try:
        # Attempt to connect and verify daemon is responsive
        return daemon_is_alive(socket_path)
    except (FileNotFoundError, ConnectionRefusedError, TimeoutError):
        return False
```

**Graceful fallback:**
- If daemon is not responding, silently fall back to direct mode
- Log message indicates fallback occurred (for debugging)
- User never sees error unless `--verbose` flag used

#### Phase 3: Configuration Management
New subcommand for config validation and discovery:

```bash
# List configured servers
$ cllm-mcp config list --config /etc/mcp-config.json
  filesystem    Read/write local filesystem
  github        GitHub API access
  postgres      PostgreSQL database

# Validate configuration syntax
$ cllm-mcp config validate --config /etc/mcp-config.json
  ✓ Configuration is valid
  ✓ 3 servers defined
  ✓ All server commands are executable

# Enhanced wrapper experience
$ cllm-mcp call-tool --config /etc/mcp-config.json filesystem list_files '{"path": "."}'
```

### Entry Points in pyproject.toml

```toml
[project.scripts]
# Main unified entry point
cllm-mcp = "cllm_mcp.main:main"

# Backward compatibility aliases
mcp-cli = "cllm_mcp.cli:main"
mcp-daemon = "cllm_mcp.daemon:main"
```

### Backward Compatibility

The existing `mcp-cli` and `mcp-daemon` commands remain unchanged:
- All existing scripts and integrations continue to work
- No breaking changes to command-line interfaces
- Users can migrate at their own pace
- Documentation encourages migration to `cllm-mcp`

**Migration path:**
```bash
# Old way (still works)
mcp-cli list-tools ...
mcp-daemon start

# New recommended way
cllm-mcp list-tools ...
cllm-mcp daemon start
```

## Consequences

### Positive

- **Unified user experience**: Single command for all operations
- **Lower barrier to entry**: New users don't need to understand daemon vs. direct mode upfront
- **Automatic optimization**: Daemon benefits achieved transparently when available
- **Clear intent**: Subcommand structure makes operation explicit
- **Minimal code churn**: Reuses existing `mcp_cli.py` and `mcp_daemon.py` implementations
- **Backward compatible**: No breaking changes to existing tools
- **Configuration discovery**: New `config` subcommand helps users explore available servers
- **Graceful degradation**: Works correctly whether daemon is running or not

### Negative

- **Additional entry point**: Three commands instead of two (`cllm-mcp`, `mcp-cli`, `mcp-daemon`)
- **Documentation burden**: Need to explain when to use daemon vs. direct mode
- **Possible confusion**: Users might not realize they're using daemon (good for UX, potentially harder to debug)
- **Socket collision**: Potential issues if multiple daemon instances try to use same socket
- **Development complexity**: Additional parser logic and dispatch code

### Mitigation

- **Lock file** for daemon: Ensure only one daemon process per socket path
- **Verbose logging**: `--verbose` flag shows which mode being used
- **Man pages**: Clear documentation of behavior and migration guide
- **Status command**: `cllm-mcp daemon status` explains current state
- **Health checks**: Regular automated verification that daemon is responsive

## Alternatives Considered

### 1. Keep Separate Commands (Current State)
**Pros:**
- No migration effort needed
- Clear separation of concerns

**Cons:**
- Continued friction in user experience
- Daemon benefits not transparent
- Configuration wrapper adds indirection

### 2. Replace mcp-cli with mcp-daemon (All-in-One Daemon)
**Pros:**
- Truly single command
- Daemon always available

**Cons:**
- Breaking change: existing scripts break
- Daemon startup overhead for simple one-off operations
- Harder to use in containers/ephemeral environments
- Forces daemon complexity on all users

### 3. Configuration-Only Approach
**Pros:**
- Simpler implementation
- Focuses on configuration management

**Cons:**
- Doesn't address the fundamental UX issue
- Still need to manage two command names
- Doesn't reduce cognitive load

### Decision Rationale

**Chosen: Unified wrapper (Option 1) with transparent daemon**

- Maintains backward compatibility (no breaking changes)
- Provides clear migration path
- Reduces cognitive load while preserving user control
- Automatic daemon detection is graceful and reliable
- Reuses existing battle-tested code
- Achieves benefits without forcing complexity

## Implementation Notes

### Phase 1: MVP (Critical Path)
1. Create `cllm_mcp/main.py` with unified dispatcher
2. Extract daemon detection logic into reusable function
3. Update `pyproject.toml` to add `cllm-mcp` entry point
4. Update README with new command documentation
5. Add examples of unified command usage

### Phase 2: Polish
1. Add `--verbose` flag for debugging daemon selection
2. Implement config management subcommand
3. Add health check to daemon status
4. Create migration guide from `mcp-cli` to `cllm-mcp`

### Phase 3: Ecosystem
1. Update `mcp-wrapper.sh` to use `cllm-mcp` by default
2. Add shell completions for `cllm-mcp`
3. Create quick-start guide emphasizing single command
4. Deprecate `mcp-daemon` in favor of `cllm-mcp daemon`

### Code Structure
```
cllm_mcp/
├── main.py              # New unified dispatcher
├── mcp_cli.py           # Existing client logic (unchanged)
├── mcp_daemon.py        # Existing daemon logic (unchanged)
├── config.py            # New configuration management
├── daemon_utils.py      # New: shared daemon utilities
└── __main__.py          # Allow: python -m cllm_mcp
```

## More Information

- **Related**: ADR-0001 (Adopt Vibe ADR framework)
- **Related**: ADR-0002 (Adopt uv package manager)
- **MCP Specification**: https://spec.modelcontextprotocol.io/
- **Unix Socket Programming**: https://en.wikipedia.org/wiki/Unix_domain_socket
- **CLI Design**: https://www.gnu.org/software/libc/manual/html_node/Argument-Syntax.html

## Timeline

- **Week 1-2**: Implement Phase 1 (MVP)
- **Week 3**: Add Phase 2 features (polish)
- **Week 4+**: Documentation and ecosystem updates

## Questions & Clarifications

**Q: Will daemon always start automatically?**
A: No, daemon is opt-in via `cllm-mcp daemon start`. Tool calls automatically use existing daemon if available.

**Q: What happens if daemon crashes?**
A: Tool calls automatically fall back to direct mode (transparent to user).

**Q: Can I force direct mode always?**
A: Yes, use `--no-daemon` flag to disable daemon usage.

**Q: Will this slow down direct mode?**
A: Negligible overhead (socket availability check). Direct mode remains unchanged if daemon not detected.
