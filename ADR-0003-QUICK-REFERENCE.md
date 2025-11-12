# ADR-0003: Quick Reference Guide

## What is ADR-0003?

**Unified Daemon/Client Command Architecture** - A proposal to consolidate the current `mcp-cli` and `mcp-daemon` commands into a single `cllm-mcp` command with transparent daemon support.

## Documents

### Architecture & Decision
- **docs/decisions/0003-unified-daemon-client-command.md** - Main ADR document with:
  - Problem statement
  - Proposed solution
  - Design alternatives
  - Implementation phases
  - Consequences and tradeoffs

### Testing Strategy
- **docs/testing/ADR-0003-testing-strategy.md** - Comprehensive testing plan with:
  - 150+ test cases
  - Unit and integration test categories
  - Mock and fixture strategy
  - Acceptance criteria
  - Coverage targets

### Testing Implementation
- **docs/testing/README.md** - Overview of testing infrastructure
- **docs/testing/TESTING-GUIDE.md** - Practical guide for running tests
- **docs/testing/IMPLEMENTATION-SUMMARY.md** - What was created and built
- **tests/** - Complete test suite (203 test cases)

## The Vision

### Current State
```bash
# Two separate commands
mcp-cli list-tools <server>        # Direct mode
mcp-daemon start                   # Daemon management
mcp-daemon status
```

### Proposed State
```bash
# Single unified command
cllm-mcp list-tools <server>       # Auto-uses daemon if available
cllm-mcp daemon start              # Explicit daemon control
cllm-mcp daemon status
cllm-mcp config list               # New: discover servers
```

## Key Features

1. **Single Entry Point**
   - One command for all operations
   - Familiar for users

2. **Transparent Daemon**
   - Automatically uses daemon if available
   - Falls back to direct mode gracefully
   - No user configuration needed

3. **Explicit Control**
   - `cllm-mcp daemon start|stop|status`
   - Clear what's happening
   - Optional `--no-daemon` flag

4. **Backward Compatible**
   - `mcp-cli` and `mcp-daemon` still work
   - No breaking changes
   - Smooth migration path

## Commands (Proposed)

### Tool Execution
```bash
cllm-mcp list-tools <server>           # List available tools
cllm-mcp call-tool <server> <tool>     # Execute a tool
cllm-mcp interactive <server>          # Interactive REPL
```

### Daemon Management
```bash
cllm-mcp daemon start                  # Start persistent daemon
cllm-mcp daemon status                 # Show daemon status
cllm-mcp daemon stop                   # Stop daemon
cllm-mcp daemon restart                # Restart daemon
```

### Configuration
```bash
cllm-mcp config list                   # List configured servers
cllm-mcp config validate               # Validate config file
```

### Global Options
```bash
--config FILE                          # Config file path
--socket PATH                          # Daemon socket path
--no-daemon                            # Force direct mode
--daemon-timeout SECONDS               # Daemon timeout
--verbose                              # Detailed output
```

## Performance Benefits

### Daemon Mode (When Available)
- **First call**: ~2-3 seconds (server startup)
- **Subsequent calls**: ~100-500ms (server cached)
- **5+ calls**: 5-10x faster than direct mode

### Direct Mode (Fallback)
- **Each call**: ~1-3 seconds (independent process)
- **Reliable**: Works without daemon
- **Predictable**: No state sharing

## Architecture

```
User Command
    │
    ├─→ Check daemon availability
    │
    ├─→ If available & not --no-daemon
    │   └─→ Use Unix socket IPC (fast)
    │
    └─→ Else
        └─→ Spawn direct subprocess (reliable)
```

## Implementation Phases

### Phase 1: MVP (Weeks 1-2)
- [ ] Create unified dispatcher in `main.py`
- [ ] Implement daemon detection logic
- [ ] Add `cllm-mcp` entry point
- [ ] Update `pyproject.toml`
- [ ] Write README with new commands

### Phase 2: Features (Weeks 2-3)
- [ ] Config management subcommand
- [ ] Verbose logging (`--verbose` flag)
- [ ] Health checks
- [ ] Migration guide

### Phase 3: Polish (Week 3-4)
- [ ] Shell completions
- [ ] Updated documentation
- [ ] Performance benchmarks
- [ ] Deprecation notices for old commands

## Testing

### 203 Test Cases
- **120 unit tests** (fast, isolated)
- **105 integration tests** (realistic scenarios)

### Coverage Targets
- Overall: 85%
- Critical paths: 100%
- New code: 90%

### Running Tests
```bash
# All tests
uv run pytest tests/ -v

# Unit tests only (fast)
uv run pytest tests/unit/ -v

# With coverage
uv run pytest tests/ --cov=cllm_mcp --cov-report=html

# Specific test
uv run pytest tests/unit/test_daemon_detection.py -v
```

## Code Structure

### New Files to Create
- `cllm_mcp/main.py` - Unified dispatcher
- `cllm_mcp/daemon_utils.py` - Shared utilities
- `cllm_mcp/config.py` - Configuration management

### Modified Files
- `pyproject.toml` - Add `cllm-mcp` entry point
- `README.md` - Document new command
- `CONTRIBUTING.md` - Update contribution guide

### Existing Files (Unchanged)
- `mcp_cli.py` - Existing client logic
- `mcp_daemon.py` - Existing daemon logic

## Backward Compatibility

### Old Commands Still Work
```bash
# These continue to work
mcp-cli list-tools <server>
mcp-daemon start
```

### New Commands Preferred
```bash
# These are the recommended way going forward
cllm-mcp list-tools <server>
cllm-mcp daemon start
```

## Benefits

1. **Better User Experience**
   - Single command to learn
   - Automatic optimization
   - Transparent fallback

2. **Performance**
   - 5-10x faster for batch operations
   - Automatic when daemon available
   - No user configuration needed

3. **Reliability**
   - Works without daemon
   - Graceful degradation
   - Clear error messages

4. **Maintainability**
   - Reuses existing code
   - Clear separation of concerns
   - Comprehensive tests

## Current Status

✅ **Completed:**
- Main ADR document
- Testing strategy document
- 203 test cases defined
- Complete test infrastructure
- pytest configuration
- GitHub Actions workflow
- Documentation

🔄 **Next Steps:**
- Implement main.py dispatcher
- Implement daemon detection
- Implement config management
- Run test suite and fix failures
- Achieve coverage targets
- Create shell completions

## Quick Links

| Document | Purpose |
|----------|---------|
| [ADR-0003](docs/decisions/0003-unified-daemon-client-command.md) | Main architecture decision |
| [Testing Strategy](docs/testing/ADR-0003-testing-strategy.md) | Comprehensive test plan |
| [Testing Guide](docs/testing/TESTING-GUIDE.md) | How to run tests |
| [Test Summary](docs/testing/IMPLEMENTATION-SUMMARY.md) | What was implemented |
| [Test Files](tests/) | 203 test cases |

## Questions?

### What is a daemon?
A persistent background process that caches MCP servers, making repeated tool calls faster (5-10x speedup).

### Will my existing scripts break?
No. The old `mcp-cli` command continues to work exactly as before.

### Do I need to run the daemon manually?
No. The `cllm-mcp` command automatically detects and uses the daemon if it's running. You can optionally start it with `cllm-mcp daemon start` for better performance.

### What if the daemon crashes?
No problem. Tool calls automatically fall back to direct mode. Everything continues to work.

### How do I force direct mode?
Use the `--no-daemon` flag: `cllm-mcp --no-daemon list-tools <server>`

### What's the expected timeline?
- Design complete ✅
- Testing infrastructure complete ✅
- Implementation: 3-4 weeks
- Release: End of sprint

## Architecture Decision Timeline

1. **Proposal** (This ADR)
2. **Design Review** (Stakeholder feedback)
3. **Implementation** (Code and tests)
4. **Testing** (Full test suite)
5. **Review** (Code and design review)
6. **Merge** (PR approval)
7. **Release** (Public availability)

## Related ADRs

- [ADR-0001: Vibe ADR Framework](docs/decisions/0001-adopt-vibe-adr.md)
- [ADR-0002: Adopt uv Package Manager](docs/decisions/0002-adopt-uv-package-manager.md)
- [ADR-0003: Unified Daemon/Client Command](docs/decisions/0003-unified-daemon-client-command.md) ← You are here

---

For detailed information, see the full ADR document at `docs/decisions/0003-unified-daemon-client-command.md`
