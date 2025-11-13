# CLLM-MCP Codebase Structure & Legacy Commands Analysis

## Executive Summary

The **cllm-mcp** project is a high-performance Python CLI utility for invoking MCP (Model Context Protocol) tools directly from bash scripts. It has evolved from legacy standalone scripts (`mcp_cli.py`, `mcp_daemon.py`) into a modern unified command structure (`cllm-mcp`) with intelligent daemon detection and configuration management.

**Legacy Commands** refers to the backward-compatible entry points that existed before the unified architecture:

- `python mcp_cli.py` - Direct MCP client (pre-ADR-0003)
- `python mcp_daemon.py` - Daemon management (pre-ADR-0003)

These commands are maintained for backward compatibility while the new unified `cllm-mcp` command serves as the primary interface.

---

## 1. PROJECT STRUCTURE

### Root Level Files

- **mcp_cli.py** (Legacy) - Direct MCP client implementation
- **mcp_daemon.py** (Legacy) - Daemon server implementation
- **pyproject.toml** - Project configuration and entry points
- **README.md** - Main documentation
- **llms.txt** - LLM context configuration

### Modern Package Structure

```
cllm_mcp/                      # Main package (post-ADR-0003)
├── main.py                    # Unified command dispatcher (entry point)
├── config.py                  # Configuration management (ADR-0004)
├── daemon_utils.py            # Daemon detection utilities
├── socket_utils.py            # Shared socket communication
└── __init__.py
```

### Documentation

```
docs/
├── decisions/                 # Architecture Decision Records (ADRs)
│   ├── 0001-adopt-vibe-adr.md
│   ├── 0002-adopt-uv-package-manager.md
│   ├── 0003-unified-daemon-client-command.md
│   ├── 0004-standardize-configuration-with-cllm-folder.md
│   ├── 0005-daemon-auto-initialize-mcp-servers.md
│   ├── 0005-IMPLEMENTATION.md
│   ├── 0005-RETROSPECTIVE.md
│   └── 0006-tool-invocation-examples-in-list-tools.md
├── testing/                   # Testing documentation
└── ADR-*.md                   # Summary and implementation reports
```

### Tests

```
tests/
├── unit/                      # Unit tests (fast, isolated)
│   ├── test_config_management.py
│   ├── test_daemon_detection.py
│   ├── test_main_dispatcher.py
│   ├── test_adr_0005_initialization.py
│   └── test_adr_0006_tool_examples.py
└── integration/               # Integration tests
    ├── test_direct_mode_integration.py
    ├── test_daemon_mode_integration.py
    └── test_fallback_behavior.py
```

---

## 2. UNDERSTANDING "LEGACY COMMANDS"

### What Are Legacy Commands?

The README explicitly identifies "Legacy Commands" in section "Legacy Commands (Backward Compatible)":

```markdown
### Legacy Commands (Backward Compatible)

For backward compatibility, the legacy entry points still work:

# Legacy direct client

python mcp_cli.py list-tools "..."
python mcp_cli.py call-tool "..." tool_name '{...}'

# Legacy daemon (deprecated)

python mcp_daemon.py start
python mcp_daemon.py stop
python mcp_daemon.py status

**Note**: New projects should use `cllm-mcp` command. Legacy commands are maintained for existing scripts.
```

**File References**:

- `/Users/owenzanzal/Projects/cllm-mcp/README.md` (Lines 84-99)
- `/Users/owenzanzal/Projects/cllm-mcp/README.md` (Lines 110-113)

### Legacy Implementation Files

#### mcp_cli.py (1-543 lines)

**Location**: `/Users/owenzanzal/Projects/cllm-mcp/mcp_cli.py`

**Purpose**: Direct MCP client that communicates with servers via JSON-RPC over stdio

**Key Classes**:

```python
class MCPClient:
    """Simple MCP client that communicates with MCP servers via stdio."""
    def __init__(self, server_command: str)
    def start(self)
    def stop(self)
    def list_tools(self) -> List[Dict[str, Any]]
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any
```

**Commands Supported**:

- `list-tools <server_command>` - List available tools
- `call-tool <server_command> <tool_name> <json_params>` - Execute a tool
- `interactive <server_command>` - Interactive REPL mode

**Key Functions**:

- `daemon_list_tools()` - Use daemon if available
- `daemon_call_tool()` - Call tool via daemon
- `generate_json_example()` - Generate examples from schemas
- `cmd_list_tools()`, `cmd_call_tool()`, `cmd_interactive()` - Command handlers

#### mcp_daemon.py (1-100+ lines)

**Location**: `/Users/owenzanzal/Projects/cllm-mcp/mcp_daemon.py`

**Purpose**: Persistent MCP server manager using Unix domain sockets

**Key Components**:

```python
class InitializationResult:
    """Result of server initialization process (ADR-0005)"""

def build_server_command(server_config: Dict[str, Any]) -> str
def initialize_servers_async(...)
```

**Commands Supported**:

- `start [--socket PATH]` - Start daemon
- `stop [--socket PATH]` - Stop daemon
- `status [--socket PATH]` - Check daemon status

**Features**:

- Persistent process caching to avoid startup overhead
- Unix domain socket IPC for communication
- Configuration-based server initialization (ADR-0005)

---

## 3. MODERN UNIFIED ARCHITECTURE

### Primary Entry Point: cllm-mcp (ADR-0003)

**File**: `/Users/owenzanzal/Projects/cllm-mcp/cllm_mcp/main.py`

**Entry Point Configuration** (pyproject.toml):

```toml
[project.scripts]
cllm-mcp = "cllm_mcp.main:main"
```

**Command Structure**:

```bash
cllm-mcp list-tools <server>          # List tools
cllm-mcp call-tool <server> <tool> <json>  # Call a tool
cllm-mcp interactive <server>         # Interactive mode
cllm-mcp daemon [start|stop|status|restart]  # Manage daemon
cllm-mcp config [list|validate|show|migrate]  # Configuration
```

**Key Features**:

1. **Unified command dispatcher** - Single entry point for all operations
2. **Smart daemon detection** - 1s timeout check; falls back gracefully
3. **Configuration-driven** - Uses CLLM-style precedence (ADR-0004)
4. **Auto-initialization** - Configures servers on daemon start (ADR-0005)

---

## 4. ARCHITECTURE DECISION RECORDS (ADRs)

### Format & Location

- **Framework**: Vibe ADR
- **Location**: `/Users/owenzanzal/Projects/cllm-mcp/docs/decisions/`
- **Numbering**: Sequential (0001, 0002, etc.)
- **Status**: Proposed, Accepted, Implemented, Superseded
- **Template**: `/Users/owenzanzal/Projects/cllm-mcp/templates/VIBE_ADR_TEMPLATE.md`

### ADR-0001: Adopt Vibe ADR

**File**: `/Users/owenzanzal/Projects/cllm-mcp/docs/decisions/0001-adopt-vibe-adr.md`

- **Status**: Accepted
- **Purpose**: Standardized architecture decision documentation process
- **Key Sections**: Status, Context, Decision, Consequences, Alternatives, Implementation Notes

### ADR-0003: Unified Daemon/Client Command

**File**: `/Users/owenzanzal/Projects/cllm-mcp/docs/decisions/0003-unified-daemon-client-command.md`

- **Status**: Accepted
- **Purpose**: Replace dual `mcp_cli.py` and `mcp_daemon.py` with single `cllm-mcp` command
- **Key Achievement**: Smart daemon detection with graceful fallback
- **Impact**: Legacy commands continue to work for backward compatibility

### ADR-0004: CLLM-Style Configuration

**File**: `/Users/owenzanzal/Projects/cllm-mcp/docs/decisions/0004-standardize-configuration-with-cllm-folder.md`

- **Status**: Accepted (Implemented & Deployed)
- **Purpose**: Standardized hierarchical configuration approach
- **Configuration Precedence** (lowest to highest):
  1. `~/.cllm/mcp-config.json` (Global defaults)
  2. `./.cllm/mcp-config.json` (Project-specific)
  3. `./mcp-config.json` (Current directory)
  4. `CLLM_MCP_CONFIG` environment variable
  5. `--config` CLI argument (Explicit override)
- **Features**:
  - Backward compatibility for old paths (Year 1)
  - Deprecation warnings in verbose mode
  - Configuration validation
  - Migration commands

### ADR-0005: Auto-Initialize Configured Servers

**File**: `/Users/owenzanzal/Projects/cllm-mcp/docs/decisions/0005-daemon-auto-initialize-mcp-servers.md`

- **Status**: Accepted (Implemented November 12, 2025)
- **Purpose**: Automatically launch all configured servers on daemon start
- **Benefits**:
  - Eliminates warm-up cost
  - Provides immediate server availability
  - Optimal caching from first call
- **Implementation**: `/Users/owenzanzal/Projects/cllm-mcp/docs/decisions/0005-IMPLEMENTATION.md`
- **Retrospective**: `/Users/owenzanzal/Projects/cllm-mcp/docs/decisions/0005-RETROSPECTIVE.md`

### ADR-0006: Tool Invocation Examples in list-tools

**File**: `/Users/owenzanzal/Projects/cllm-mcp/docs/decisions/0006-tool-invocation-examples-in-list-tools.md`

- **Status**: Proposed
- **Purpose**: Add concrete examples to `list-tools` output
- **Problem**: Users must parse JSON schemas to understand how to invoke tools
- **Solution**: Generate type-based example invocations automatically

---

## 5. CONFIGURATION STRUCTURE

### Configuration File Locations

**Priority Order** (highest to lowest):

1. CLI argument: `--config /path/to/config.json`
2. Environment variable: `CLLM_MCP_CONFIG=/path/to/config.json`
3. Current directory: `./mcp-config.json`
4. Project-specific: `./.cllm/mcp-config.json`
5. Global: `~/.cllm/mcp-config.json`
6. (Deprecated) `~/.config/cllm-mcp/config.json`
7. (Deprecated) `/etc/cllm-mcp/config.json`

**File**: `/Users/owenzanzal/Projects/cllm-mcp/cllm_mcp/config.py` (Lines 40-151)

### Configuration Schema

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem", "/home/user/Documents"],
      "description": "Filesystem access",
      "autoStart": true,
      "optional": false
    },
    "time": {
      "command": "uvx",
      "args": ["mcp-server-time"],
      "description": "Time server",
      "autoStart": true
    }
  },
  "daemon": {
    "socket": "/tmp/mcp-daemon.sock",
    "timeout": 30,
    "maxServers": 10
  },
  "logging": {
    "level": "info",
    "format": "json"
  }
}
```

### Configuration Management Functions

**File**: `/Users/owenzanzal/Projects/cllm-mcp/cllm_mcp/config.py`

Key functions:

```python
def find_config_file(explicit_path=None, verbose=False) -> Tuple[Optional[Path], List[str]]
def load_config(config_path: str) -> Dict[str, Any]
def validate_config(config: Dict[str, Any]) -> List[str]
def cmd_config_list(args)
def cmd_config_validate(args)
def cmd_config_show(args)
def cmd_config_migrate(args)
def resolve_server_ref(server_ref: str, config: Dict[str, Any]) -> str
```

---

## 6. TESTS STRUCTURE

### Test Configuration

**File**: `/Users/owenzanzal/Projects/cllm-mcp/pyproject.toml` (Lines 44-68)

**Test Markers**:

- `@pytest.mark.unit` - Fast, isolated tests
- `@pytest.mark.integration` - Tests with dependencies
- `@pytest.mark.daemon` - Daemon functionality tests
- `@pytest.mark.socket` - Unix socket tests
- `@pytest.mark.asyncio` - Async tests

### Unit Tests

#### test_config_management.py

**File**: `/Users/owenzanzal/Projects/cllm-mcp/tests/unit/test_config_management.py`

**Test Classes**:

- `TestCLLMConfigPrecedence` - Configuration precedence and resolution
  - `test_find_config_returns_tuple` - Verify return type
  - `test_precedence_explicit_path_highest` - Explicit path priority
  - `test_precedence_current_directory` - Current directory detection
  - `test_verbose_tracing_enabled` - Verbose output
  - `test_environment_variable_override` - Environment variable override
  - `test_backward_compatibility_deprecation_warning` - Deprecation warnings

- `TestConfigLoading` - Configuration loading
  - `test_load_config_from_explicit_path` - Load from path
  - Additional template tests for validation

#### test_daemon_detection.py

**File**: `/Users/owenzanzal/Projects/cllm-mcp/tests/unit/test_daemon_detection.py`

Tests for `daemon_utils.py`:

- Daemon socket path resolution
- Smart daemon detection logic
- Fallback behavior

#### test_main_dispatcher.py

**File**: `/Users/owenzanzal/Projects/cllm-mcp/tests/unit/test_main_dispatcher.py`

Tests for unified command router:

- Command parsing
- Handler delegation
- Argument passing

#### test_adr_0005_initialization.py

**File**: `/Users/owenzanzal/Projects/cllm-mcp/tests/unit/test_adr_0005_initialization.py`

Tests for server auto-initialization:

- Configuration-based startup
- Initialization status reporting
- Error handling

#### test_adr_0006_tool_examples.py

**File**: `/Users/owenzanzal/Projects/cllm-mcp/tests/unit/test_adr_0006_tool_examples.py`

Tests for tool invocation examples:

- JSON example generation
- Type-based placeholder generation
- Schema parsing

### Integration Tests

#### test_direct_mode_integration.py

**File**: `/Users/owenzanzal/Projects/cllm-mcp/tests/integration/test_direct_mode_integration.py`

Tests direct client functionality:

- Direct tool listing
- Tool invocation without daemon
- Error scenarios

#### test_daemon_mode_integration.py

**File**: `/Users/owenzanzal/Projects/cllm-mcp/tests/integration/test_daemon_mode_integration.py`

Tests daemon-based operations:

- Daemon startup
- Tool operations via daemon
- Server initialization

#### test_fallback_behavior.py

**File**: `/Users/owenzanzal/Projects/cllm-mcp/tests/integration/test_fallback_behavior.py`

Tests graceful degradation:

- Daemon detection with timeout
- Fallback to direct mode
- Transparent mode switching

---

## 7. KEY LEGACY COMMAND REFERENCES IN CODEBASE

### README.md References

- **Line 84**: "### Legacy Commands (Backward Compatible)"
- **Line 89-96**: Examples of legacy command usage
- **Line 99**: "Note: New projects should use `cllm-mcp` command. Legacy commands are maintained for existing scripts."
- **Line 110-113**: Directory structure showing legacy vs. modern files

### Daemon Architecture References

- **DAEMON-ARCHITECTURE-DIAGRAMS.txt** (Line 268-270):

  ```
  ├─ mcp-cli           → mcp_cli.main()                [TODO - Legacy alias]
  └─ mcp-daemon        → mcp_daemon.main()             [TODO - Legacy alias]
  ```

- **DAEMON-ARCHITECTURE.md** (Line 14):
  ```
  - **Legacy aliases** (for backward compatibility, not yet configured in pyproject.toml):
  ```

### Configuration Precedence References

- **README.md** (Line 968):
  ```
  3. `./mcp-config.json` (legacy)
  ```

---

## 8. IMPLEMENTATION STATUS

### Completed (Production Ready)

- [x] ADR-0001: Vibe ADR Framework
- [x] ADR-0002: UV Package Manager
- [x] ADR-0003: Unified Daemon/Client Command
- [x] ADR-0004: CLLM Configuration with retrospective
- [x] ADR-0005: Auto-Initialize Servers with implementation and retrospective

### In Progress/Proposed

- [ ] ADR-0006: Tool Invocation Examples (Proposed)
- [ ] Legacy command aliases in pyproject.toml (TODO)

### Testing Coverage

- 7/7 core configuration precedence tests passing
- 23 template tests prepared for edge cases
- Integration tests covering direct, daemon, and fallback modes
- Comprehensive test fixtures in `conftest.py`

---

## 9. RECOMMENDED ADR TOPIC AREAS FOR LEGACY COMMANDS

If you're creating an ADR about Legacy Commands, consider these angles:

### Option A: Legacy Command Support Strategy

**Scope**: Formal strategy for maintaining backward compatibility

- **Decision**: How long to support legacy commands?
- **Deprecation Timeline**: Year 1, 2, 3+ phases
- **Warning Levels**: Info → Warnings → Errors
- **Migration Path**: Tools to help users transition

### Option B: Alias Entry Points for Legacy Commands

**Scope**: Implementing `mcp-cli` and `mcp-daemon` aliases

- **Problem**: Legacy scripts expect these commands
- **Decision**: Register aliases in pyproject.toml
- **Implementation**: Wrapper functions or direct dispatch
- **Testing**: Ensure aliases work identically to new command

### Option C: Deprecation of Direct Script Execution

**Scope**: Transitioning from `python mcp_cli.py` to installed commands

- **Problem**: Direct execution has different semantics than installed scripts
- **Decision**: Encourage installation via package manager
- **Mechanism**: Clear error messages and migration guidance

### Option D: Configuration Migration for Legacy Users

**Scope**: Helping users migrate from old config locations to new CLLM structure

- **Problem**: Existing configs in old locations won't work with new precedence
- **Decision**: Support both old and new locations during transition
- **Feature**: `cllm-mcp config migrate` command (already implemented!)

---

## 10. KEY CODE SNIPPETS FOR REFERENCE

### Configuration Discovery (ADR-0004)

**File**: `/Users/owenzanzal/Projects/cllm-mcp/cllm_mcp/config.py` (Lines 40-151)

```python
def find_config_file(
    explicit_path: Optional[str] = None, verbose: bool = False
) -> Tuple[Optional[Path], List[str]]:
    """
    Find configuration file using CLLM precedence.

    ADR-0004 Configuration Precedence (lowest to highest priority):
    1. ~/.cllm/mcp-config.json         (Global defaults)
    2. ./.cllm/mcp-config.json         (Project-specific)
    3. ./mcp-config.json               (Current directory)
    4. Environment variables (CLLM_MCP_CONFIG)
    5. Explicit path argument (highest priority)
    """
    # Implementation includes verbose tracing and backward compatibility
```

### Legacy Command Handler

**File**: `/Users/owenzanzal/Projects/cllm-mcp/mcp_cli.py` (Lines 481-543)

```python
def main():
    """Main entry point for the MCP CLI."""
    parser = argparse.ArgumentParser(
        description="MCP CLI - Make MCP tool calls without an LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # list-tools command
    list_parser = subparsers.add_parser("list-tools", help="List all available tools")
    # ... additional commands
```

### Modern Unified Command Dispatcher

**File**: `/Users/owenzanzal/Projects/cllm-mcp/cllm_mcp/main.py` (Lines 1-50)

```python
"""
Unified command dispatcher for cllm-mcp (ADR-0003, ADR-0004).

Routes commands to appropriate handlers with smart daemon detection.
Supports:
  - list-tools: List available MCP tools
  - call-tool: Execute a specific MCP tool
  - interactive: Interactive REPL for exploring tools
  - daemon: Manage persistent daemon (start, stop, status, restart)
  - config: Manage configurations (list, validate, show, migrate)
"""
```

---

## SUMMARY FOR ADR CREATION

### Findings at a Glance

| Aspect                 | Details                                                               |
| ---------------------- | --------------------------------------------------------------------- |
| **Legacy Commands**    | `python mcp_cli.py`, `python mcp_daemon.py` (pre-ADR-0003)            |
| **Modern Entry Point** | `cllm-mcp` (unified command via ADR-0003)                             |
| **ADR Format**         | Vibe ADR with Status, Context, Decision, Consequences, Implementation |
| **ADR Location**       | `/docs/decisions/` with numbered sequence                             |
| **Configuration**      | CLLM-style precedence (ADR-0004) with 5-level hierarchy               |
| **Current Status**     | ADR-0001 through 0005 Accepted/Implemented; ADR-0006 Proposed         |
| **Test Coverage**      | Unit + Integration tests; 7 core tests passing                        |
| **Backward Compat**    | Legacy commands work; new unified command preferred                   |

### What "Legacy Commands" Really Means

In the context of this project, "Legacy Commands" refers to:

1. **The original dual-command approach**: Separate `mcp_cli.py` for direct operations and `mcp_daemon.py` for daemon management
2. **Why they exist**: Pre-ADR-0003, before unified command architecture was designed
3. **Current status**: Maintained for backward compatibility but deprecated for new projects
4. **How they work**: Same underlying logic as before, but called directly as Python scripts
5. **Migration path**: Users should transition to `cllm-mcp` command with smart daemon detection

This is a classic "keep old interfaces working for backward compatibility while encouraging migration to new unified interface" pattern.
