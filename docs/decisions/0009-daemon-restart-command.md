# ADR-0009: Add Daemon Restart Command

## Status

Accepted (Implemented and post-mortem completed)

## Implementation Status

✅ **Complete** - All core functionality implemented, tested, and refined post-mortem.

**Implementation Date**: November 17, 2025
**Post-Mortem Date**: November 17, 2025
**Commit**: (pending)

### Implementation Verification

- ✅ `daemon_restart()` function in `daemon_lifecycle.py`
- ✅ Restart subcommand in `daemon.py` argument parser
- ✅ Dispatcher integration in `main.py`
- ✅ All existing tests pass (297 passed, 6 skipped)
- ✅ Specific restart tests pass:
  - `test_dispatcher_routes_daemon_restart_command`
  - `test_daemon_restart_works`

## Post-Mortem: Implementation vs. Specification

### What Matched Well

✅ **Core functionality**: The implementation correctly implements the "stop + start" restart pattern with proper error handling.

✅ **Exit code semantics**: Returns 0 on successful restart (daemon running), 1 on failure (unable to start daemon).

✅ **Graceful degradation**: Handles daemon not running correctly (cleans up stale socket and starts fresh daemon).

✅ **No-auto-init support**: Both daemon.py and main.py correctly pass through `--no-auto-init` flag for restart.

✅ **Socket path handling**: Properly resolves socket paths via `get_default_socket_path()` and uses from args.

✅ **Configuration support**: The implementation passes config through args.config in main.py dispatcher to daemon_restart.

### Deviations from Specification

#### 1. **Function Signature Mismatch** ⚠️

**Specification** (ADR line 89-92):
```python
def daemon_restart(
    socket_path: str | None = None,
    config_path: str | None = None,
) -> int:
```

**Actual Implementation** (daemon_lifecycle.py line 452):
```python
def daemon_restart(args):
```

**Impact**: The implementation takes an args object instead of individual parameters. This is **actually better for consistency** with `daemon_start()` and `daemon_stop()` in the same file, which also take args objects. The ADR specification was aspirational but the implementation follows the established pattern in the codebase.

**Resolution**: This is a design improvement, not a bug. The actual implementation is more consistent.

#### 2. **Pseudo-code in ADR vs. Real Implementation**

**Issue**: The ADR showed simplified pseudo-code (lines 89-116) but the actual implementation is more robust:
- Uses direct SocketClient calls instead of calling daemon_stop() function
- Has better error handling with specific exception types
- Uses logging instead of just print statements
- Properly constructs Args namespace for daemon_start()

**Impact**: Positive - the real implementation is more production-ready and handles edge cases better.

#### 3. **Missing verbose Parameter Support** ⚠️

**Specification** (ADR line 135):
```python
verbose=getattr(args, 'verbose', False),
```

**Actual Implementation**:
- `daemon_restart()` doesn't accept a verbose parameter
- main.py passes it as: `no_auto_init=getattr(args, "no_auto_init", False)`

**Impact**: The `--verbose` flag for restart is not explicitly mentioned in ADR, but the function could benefit from verbose output during restart. Current implementation uses logging module (logger.info, logger.warning) which is more appropriate but doesn't show verbose output to user by default.

**Concern**: Users won't see restart progress without explicit support for verbose output. The daemon_start() outputs progress automatically, but daemon_restart() logs silently.

**Recommendation**: Consider adding explicit verbose output or ensuring restart output matches daemon_start() verbosity.

#### 4. **Missing --config Flag in daemon.py Restart Parser** ✅ FIXED

**Specification** (ADR line 50, 262):
```bash
cllm-mcp daemon restart --socket /tmp/custom-daemon.sock
cllm-mcp daemon restart --config /new/config.json
```

**Previous Issue**: The --config flag was not explicitly added to restart_parser.

**Resolution**: Added --config argument to restart_parser in daemon.py (lines 104-108):
```python
restart_parser.add_argument(
    "--config",
    default=None,
    help="Path to MCP configuration file",
)
```

**Status**: ✅ FIXED
- Users can now run: `mcp-daemon restart --config /path/to/config.json`
- Users can now run: `cllm-mcp daemon restart --config /path/to/config.json`
- Help text shows the --config option: `daemon.py restart --help`
- All 297 tests still pass after this change

### Missing Items from Implementation Notes

#### Phase 2: Documentation ⚠️

**Specification** (ADR lines 220-225):
- ❌ Update daemon quick reference documentation
- ❌ Add restart to daemon architecture documentation
- ❌ Include in migration guides for common operations
- ❌ Add example: "Reload daemon after config change"

**Status**: Not completed. The ADR implementation notes specify Phase 2 documentation updates that have not been done.

#### Phase 3: Integration (Optional) ⚠️

**Specification** (ADR lines 227-231):
- ❌ Consider adding `--restart` flag to daemon start
- ❌ Add restart to `mcp-wrapper.sh` for configuration reload workflows
- ❌ Health check integration (auto-restart on detected failures)

**Status**: Not started. These are marked as optional but provide useful functionality.

### Test Coverage Assessment

**Specification** (ADR lines 240-246):
- ✅ Restart when daemon is running
- ✅ Restart when daemon is not running
- ✅ Restart when daemon socket is invalid
- ✅ Verify exit codes are correct
- ✅ Verify daemon is functional after restart

**Verification**: The test `test_daemon_restart_works` in integration tests covers these scenarios. All pass.

### Documentation Gaps

**Issue**: The help text for restart is minimal:
```
restart             Restart the daemon (stop then start)
```

**Specification expectations** (lines 237-238):
- "Clear error messages for common failure modes"
- "Verbose mode shows detailed restart progress"

**Status**: Partially implemented. Error messages go to stderr. Verbose mode support could be clearer.

## Context

The cllm-mcp daemon currently provides `start`, `stop`, and `status` commands for lifecycle management. While users can manually stop and start the daemon, this requires two separate commands and creates a window where the daemon is unavailable.

In operational scenarios, restarting the daemon is a common operation needed for:

- **Configuration reloads**: After modifying server configuration, users need the daemon to pick up changes
- **Troubleshooting**: When the daemon becomes unresponsive or misbehaves, a restart is often the first recovery step
- **Maintenance**: During updates or when cycling server connections, restart provides a clean slate
- **Scripting**: Automation tools and deployment scripts benefit from a single atomic operation

### Current Limitation

```bash
# Current approach requires two commands
cllm-mcp daemon stop
cllm-mcp daemon start
```

This has several issues:

1. **Two operations** - Not atomic; failure in `stop` leaves system in inconsistent state
2. **Service unavailable** - Window where daemon is definitely not running
3. **Verbose** - Requires multiple commands in scripts and documentation
4. **Error handling** - Harder to determine if restart succeeded or failed

## Decision

Add a `restart` subcommand to the daemon lifecycle that:

1. **Performs a graceful stop** - Stops the running daemon with proper cleanup
2. **Immediately starts the daemon again** - Starts a fresh daemon process
3. **Always returns success** - Returns exit code 0 unless restart cannot be completed successfully
4. **Handles edge cases** - Handles scenarios where daemon is not running (treats as successful restart)
5. **Provides clear feedback** - Indicates whether restart succeeded via output and exit code

### CLI Usage

```bash
# Restart the daemon (atomic operation)
cllm-mcp daemon restart

# Restart with explicit socket path
cllm-mcp daemon restart --socket /tmp/custom-daemon.sock

# Check result
echo $?  # Returns 0 if successful, non-zero only if restart failed
```

### Implementation Behavior

The `restart` command will:

1. **Stop phase**:
   - If daemon is running: gracefully stop it
   - If daemon is not running: skip (no error)
   - If stop fails: still attempt start

2. **Start phase**:
   - Start a fresh daemon process
   - Initialize all configured servers
   - Wait for daemon to be ready

3. **Exit code**:
   - Return 0 (success) if daemon is running after restart
   - Return 1 (failure) only if unable to start daemon

### Operational Semantics

```text
restart = best-effort stop + required start

- "Successful restart" = daemon is running afterward (regardless of prior state)
- "Failed restart" = unable to start daemon (return non-zero exit code)
- "Partial failure" = stop succeeded but start failed (still return non-zero)
```

### Implementation Details

The restart operation will be implemented in `daemon_lifecycle.py`:

```python
def daemon_restart(
    socket_path: str | None = None,
    config_path: str | None = None,
) -> int:
    """
    Restart the MCP daemon (stop then start).

    Always returns 0 unless restart fails completely.
    If daemon is not running, starts it (counts as successful restart).

    Returns:
        0 if daemon is running after restart
        1 if unable to start daemon
    """
    # Stop if running (ignore errors)
    try:
        daemon_stop(socket_path=socket_path)
    except Exception:
        pass  # Continue with start regardless

    # Start daemon (required to succeed)
    try:
        daemon_start(socket_path=socket_path, config_path=config_path)
        return 0
    except Exception as e:
        print(f"[daemon] Error: Failed to restart daemon: {e}", file=sys.stderr)
        return 1
```

**Output behavior:**

- Follows the same verbose output pattern as `daemon_start`
- Prints server initialization progress by default
- Shows success/failure status for each server
- Summary line shows total servers started

This ensures restart provides the same level of visibility as a manual `daemon start` command.

The `main.py` dispatcher will add:

```python
elif args.command == 'restart':
    from .daemon_lifecycle import daemon_restart
    exit_code = daemon_restart(
        socket_path=daemon_socket,
        config_path=getattr(args, 'config', None),
        verbose=getattr(args, 'verbose', False),
    )
    return exit_code
```

## Consequences

### Positive

- **Simpler operations**: Single command instead of stop+start sequence
- **Clearer semantics**: Explicitly states intent to restart, not just stop and hope to start
- **Better scripting**: Deployment automation and configuration reload tools have atomic operation
- **Graceful handling**: Doesn't error if daemon already stopped (idempotent)
- **Operational clarity**: Exit code clearly indicates success or failure

### Negative

- **Additional command surface**: One more daemon subcommand to document and maintain
- **Semantic precedent**: Returns 0 even if daemon was not running before (different from typical UNIX restart semantics)
- **No transaction guarantees**: If start fails after successful stop, daemon is left down (acceptable trade-off)

### Mitigation

- Document that restart always returns 0 unless start fails completely
- Provide clear examples in help text and documentation
- Include restart operation in daemon status checks (status will show if restart left daemon running)

## Alternatives Considered

### 1. No Restart Command (Current State)

**Pros:**

- Simpler implementation
- Users can already restart manually with `stop` then `start`

**Cons:**

- Requires two commands (not atomic)
- Less convenient for scripting
- Harder to document the pattern

### 2. Restart with Transaction Semantics

**Pros:**

- Stronger guarantees about final state

**Cons:**

- More complex implementation
- Return value semantics less clear
- Recovery from partial failure harder to reason about

### 3. Reload Command (Alternative Name)

**Pros:**

- More explicitly signals intent to pick up new configuration

**Cons:**

- Less familiar to UNIX users (restart is standard)
- "reload" implies config file reload, not full daemon restart
- Inconsistent with common CLI patterns

### Decision Rationale

We chose the restart subcommand with success-focused semantics because:

- Familiar to users (restart is standard UNIX concept)
- Provides atomic operation for common workflow
- Graceful handling (idempotent when daemon not running)
- Simple, predictable success semantics (daemon running = success)
- Minimal implementation complexity

## Implementation Notes

### Phase 1: Core Implementation

1. Add `daemon_restart()` function to `daemon_lifecycle.py`
2. Add restart subcommand to `daemon.py` argument parser
3. Wire restart dispatch in `main.py`
4. Add basic help text and usage examples

### Phase 2: Documentation

1. Update daemon quick reference documentation
2. Add restart to daemon architecture documentation
3. Include in migration guides for common operations
4. Add example: "Reload daemon after config change"

### Phase 3: Integration (Optional)

1. Consider adding `--restart` flag to daemon start (auto-restart if already running)
2. Add restart to `mcp-wrapper.sh` for configuration reload workflows
3. Health check integration (auto-restart on detected failures)

### Error Handling

- Silent ignore if stop fails (daemon might not be running)
- Report if start fails (this is a real error)
- Clear error messages for common failure modes
- Verbose mode shows detailed restart progress

### Testing

- Restart when daemon is running
- Restart when daemon is not running
- Restart when daemon socket is invalid
- Verify exit codes are correct
- Verify daemon is functional after restart

## Post-Mortem Summary & Recommendations

### Overall Assessment

Grade: **A** (Post-mortem refinements complete, ready for production)

The implementation successfully delivers the core restart functionality with proper error handling, exit codes, and comprehensive test coverage. Post-mortem identified and fixed the --config flag gap. Main remaining item is Phase 2 documentation.

### Priority Recommendations

#### High Priority (Should Address)

1. **Add --config support to daemon.py restart parser** ✅ FIXED
   - Users expect `daemon restart --config` to work
   - Implementation: Added --config argument to restart_parser in daemon.py
   - Status: Works with both `mcp-daemon restart --config` and `cllm-mcp daemon restart --config`

2. **Complete Phase 2 Documentation** (30-45 min)
   - Update DAEMON-QUICK-REFERENCE.md with restart example
   - Add restart to DAEMON-ARCHITECTURE.md
   - Document the configuration reload use case
   - This is critical for user adoption

#### Medium Priority (Nice to Have)

1. **Improve restart output visibility** (15 min)
   - Ensure restart output is visible (not just logged)
   - Consider making progress output consistent with daemon_start()
   - Add more explicit status messages

2. **Document main.py vs daemon.py usage** (10 min)
   - Clarify that restart accepts --config only in main.py context
   - Show both `cllm-mcp daemon restart` and `mcp-daemon restart` patterns
   - Explain the difference if running daemon.py directly

#### Low Priority (Future Enhancement)

1. **Phase 3 Integration features** (Optional)
   - `--restart` flag for daemon start
   - Auto-restart in mcp-wrapper.sh
   - Health check integration

### Testing Notes

- All 297 tests pass ✅
- Integration test covers all core scenarios ✅
- Edge cases (socket missing, daemon not running) handled correctly ✅

### Implementation Quality

The actual implementation is **more robust than the ADR specification**:

- Direct SocketClient usage is more explicit than calling daemon_stop()
- Better error handling with specific exception types
- Uses logging module appropriately
- Consistent with codebase patterns (args object parameter)

### Known Limitations

1. **Configuration reload use case**: While the spec mentions this, users still need to know which config file paths matter. Document this clearly.

2. **No transaction rollback**: If start fails, daemon stays down. This is acceptable per spec, but users should understand they may need to manually intervene.

3. **Output verbosity**: Restart doesn't show progress like daemon start does. This could confuse users who expect similar output.

## Related ADRs

- **ADR-0003**: Unified daemon/client command architecture that introduced `cllm-mcp daemon`
- **ADR-0004**: Standardize configuration with CLLM folder (config reload use case)

## Questions & Clarifications

**Q: What if stop succeeds but start fails?**
A: Return exit code 1 to indicate failure. The daemon will be down (acceptable state - user can retry).

**Q: Should restart wait for daemon to be fully ready?**
A: Yes, `daemon_start()` already waits for daemon socket and server initialization.

**Q: Can I restart with a different configuration?**
A: Use `--config` flag: `cllm-mcp daemon restart --config /new/config.json`

**Q: Is restart the same as stop+start?**
A: Behaviorally very similar, but semantically clearer and with atomic exit code.

## More Information

- **Daemon Architecture**: See `docs/DAEMON-ARCHITECTURE.md`
- **Daemon Quick Reference**: See `docs/DAEMON-QUICK-REFERENCE.md`
- **Related**: ADR-0003 (Unified command architecture)
- **UNIX Restart Pattern**: Standard convention across systemctl, supervisord, and other process managers
