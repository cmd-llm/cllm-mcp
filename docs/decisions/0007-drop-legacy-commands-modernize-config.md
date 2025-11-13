# ADR-0007: Drop Legacy Commands (Backward Compatible) and Modernize Entry Points

## Status

Accepted (Implemented November 13, 2025)

## Context

The cllm-mcp project currently maintains backward compatibility with legacy command entry points that predate the unified architecture established in ADR-0003.

### Legacy Entry Points

Currently, users can run MCP tools in three ways:

**1. Legacy Direct Python Scripts** (Pre-ADR-0003, deprecated):
```bash
python mcp_cli.py list-tools <server>          # Direct MCP client
python mcp_daemon.py daemon start              # Daemon manager
```

**2. Modern Unified Command** (ADR-0003, recommended):
```bash
cllm-mcp list-tools <server>
cllm-mcp daemon start
```

**3. Manual Installation (Not standardized)**:
- Manual setup via `pip install -e .`
- No standard installation mechanism
- Users must manage entry points themselves

### Current Issues

1. **Code Duplication**: Legacy scripts duplicate core functionality available in `cllm_mcp/main.py`
2. **Maintenance Burden**: Every bug fix/feature requires updates in multiple places:
   - `mcp_cli.py` (543 lines)
   - `mcp_daemon.py` (100+ lines)
   - `cllm_mcp/main.py` (modern version)
3. **Configuration Inconsistency**: Legacy scripts may not fully support CLLM config precedence (ADR-0004)
4. **Installation Confusion**: Documentation mentions both approaches; users unsure which to use
5. **Distribution Issues**: Legacy scripts complicate packaging and distribution
6. **Deprecation Not Enforced**: Backward compatibility creates false assumption these are supported long-term

### Migration Readiness

ADR-0003 established unified command architecture; users have had time to migrate. Recent implementation of ADR-0004 (CLLM configuration standard) and ADR-0005 (daemon auto-initialization) are all built on modern `cllm_mcp/` package structure, not legacy scripts.

**Current adoption metrics**:
- README includes both legacy and modern approaches (confusing)
- Test suite focuses on modern unified commands
- All documentation examples favor `cllm-mcp` command
- Legacy code path represents technical debt

### Ecosystem Alignment

CLLM ecosystem standard is to distribute via:
1. Package installation via `pip` (or `uv`)
2. Entry points defined in `pyproject.toml`
3. Single command-line interface (standardized in `main.py`)

Legacy Python scripts don't align with this pattern.

## Decision

We will drop support for legacy direct Python script execution and fully modernize to package-based command entry points. The `mcp_cli.py` and `mcp_daemon.py` files will be retained as internal implementation modules (not user-facing), and removed from distribution when code is properly refactored into the `cllm_mcp/` package.

### What's Being Removed

**Immediate (v1.0+)**:
- Remove execution of `python mcp_cli.py` as a user-facing command
- Remove execution of `python mcp_daemon.py` as a user-facing command
- Remove all documentation references to direct Python script execution
- Remove these files from package distribution (not installed to user systems)
- Ensure no entry points in `pyproject.toml` for legacy scripts

**Future (when code is refactored)**:
- Migrate `mcp_cli.py` and `mcp_daemon.py` code into `cllm_mcp/` package modules
- Remove these files from the repository entirely
- Complete the modernization

### Modern Entry Points

All users will use the single, standardized entry point:

```bash
cllm-mcp [command] [options]
```

**Available through**:
1. **Installed via pip/uv**:
   ```bash
   pip install cllm-mcp
   cllm-mcp list-tools <server>
   ```

2. **Development mode**:
   ```bash
   uv run cllm-mcp list-tools <server>
   ```

3. **Direct module**:
   ```bash
   python -m cllm_mcp list-tools <server>
   ```

### Entry Points Definition

Standardized in `pyproject.toml`:

```toml
[project.scripts]
cllm-mcp = "cllm_mcp.main:cli"

[project.optional-dependencies]
# Convenience aliases for CLLM ecosystem alignment
mcp-cli = "cllm_mcp.main:cli"
mcp-daemon = "cllm_mcp.main:cli"
```

### Configuration Migration

Users currently relying on legacy scripts may have older configuration paths. With ADR-0004 already deployed, migration is straightforward:

**Old paths (legacy scripts used)**:
```
~/.config/cllm-mcp/config.json    # Old XDG path
/etc/cllm-mcp/config.json          # System-wide
```

**New CLLM standard paths**:
```
~/.cllm/mcp-config.json            # Global
./.cllm/mcp-config.json            # Project
./mcp-config.json                  # Current dir
```

The modern `cllm-mcp` command already supports both via backward compatibility layer in `config.py` (ADR-0004), so migration is automatic.

### CLI Compatibility

The unified `cllm-mcp` command provides all functionality of legacy scripts:

| Use Case | Legacy | Modern |
|----------|--------|--------|
| List tools | `python mcp_cli.py list-tools fs` | `cllm-mcp list-tools fs` |
| Call tool | `python mcp_cli.py call-tool fs read /path` | `cllm-mcp call-tool fs read /path` |
| Interactive | `python mcp_cli.py interact fs` | `cllm-mcp interact fs` |
| Daemon start | `python mcp_daemon.py daemon start` | `cllm-mcp daemon start` |
| Daemon stop | `python mcp_daemon.py daemon stop` | `cllm-mcp daemon stop` |
| Daemon status | `python mcp_daemon.py daemon status` | `cllm-mcp daemon status` |

## Consequences

### Positive

- **Eliminates technical debt**: No duplicate code to maintain
- **Simpler codebase**: One authoritative implementation (`cllm_mcp/main.py`)
- **Reduced maintenance**: Bug fixes, features implemented once
- **Clear migration path**: No ambiguity about "official" command
- **Ecosystem alignment**: Follows CLLM standard distribution model
- **Smaller distribution**: Cleaner package without legacy files
- **Better testing**: Focus test suite on single code path
- **Clearer documentation**: Single recommended approach
- **CI/CD friendly**: No need to test multiple entry points
- **Future-proof**: Standardized entry point supported by build tools

### Negative

- **Breaking change**: Users on legacy scripts must update habits
- **Migration effort**: Users need to update scripts/aliases
- **Documentation changes**: Must update all examples and guides
- **One-time pain**: Initial transition period requires communication
- **Potential support burden**: Users may need help migrating (short-term)

### Mitigation

- **Clear migration guide**: Step-by-step instructions for all scenarios
- **Graceful deprecation**: Long transition period (full major version)
- **Helpful error messages**: If user runs old scripts, clear guidance
- **Installation guide**: Document the `pip install` approach prominently
- **Example scripts**: Provide template scripts users can adapt
- **Breaking change notice**: Prominent in changelog and release notes
- **Support period**: Help users migrate during transition

## Alternatives Considered

### 1. Keep Legacy Scripts Indefinitely
**Pros**: No breaking changes, no migration needed
**Cons**: Perpetual maintenance burden, technical debt, confusing documentation, larger codebase

### 2. Auto-generate Shims from Modern Code
**Pros**: Single source of truth
**Cons**: Still creates confusion, wrapper overhead, doesn't solve root issue

### 3. Gradual Deprecation Only (No Removal)
**Pros**: Never breaking, users can stay on legacy indefinitely
**Cons**: Technical debt never resolved, ongoing maintenance forever, confuses new users

### 4. Provide Wrapper Scripts Without Installation
```bash
#!/bin/bash
exec python -m cllm_mcp "$@"
```
**Pros**: Simpler than full removal, familiar entry point
**Cons**: Still requires explanation, doesn't provide actual `cllm-mcp` command, users still confused

## Decision Rationale

**Chosen**: Remove legacy scripts entirely, standardize on single modern entry point

This approach:
- **Eliminates technical debt**: No more duplicate code
- **Aligns with CLLM ecosystem**: Standard distribution model
- **Provides clear path forward**: No ambiguity for new users
- **Reduces maintenance**: Fewer code paths to maintain and test
- **Improves documentation**: Single recommended approach
- **Enables better distribution**: Cleaner package structure
- **Supports long-term sustainability**: Simpler codebase for contributions

The migration is straightforward because:
1. Modern `cllm-mcp` command provides 100% feature parity
2. CLLM configuration (ADR-0004) already handles old config paths
3. Clear CLI for installation: `pip install cllm-mcp`
4. Full documented migration guide

## Implementation Status

### Completed

✅ **Documentation Updates**
- Updated README to remove legacy script references
- Added ADR-0007 reference and migration notes
- Created comprehensive MIGRATION.md guide

✅ **Configuration Changes**
- Updated pyproject.toml to remove legacy scripts from coverage
- Verified single entry point: `cllm-mcp = "cllm_mcp.main:main"`
- No entry points defined for `mcp_cli` or `mcp_daemon`

✅ **User Communication**
- Created MIGRATION.md with clear upgrade path
- Updated README with installation instructions
- Added migration guidance for all use cases

### Internal Implementation Files

The code from `mcp_cli.py` and `mcp_daemon.py` has been refactored into internal package modules:
- `cllm_mcp/client.py` - MCP client implementation (formerly `mcp_cli.py`)
- `cllm_mcp/daemon.py` - Daemon server implementation (formerly `mcp_daemon.py`)

These are internal implementation modules used by `main.py` and not exposed to users. Root-level files no longer exist.

**Refactoring Completed**: All legacy code is now properly organized within the `cllm_mcp/` package with clean relative imports.



## Related ADRs

- **ADR-0001**: Adopt Vibe ADR Framework
  - Follows same ADR process

- **ADR-0002**: Adopt UV Package Manager
  - Using uv for development and distribution

- **ADR-0003**: Unified Daemon/Client Command Architecture
  - Established the modern unified command structure
  - This ADR cleans up the transition fully

- **ADR-0004**: Standardize Configuration Using CLLM-Style Configuration Precedence
  - Modernizes configuration handling
  - Backward compatibility layer handles old paths

- **ADR-0005**: Automatically Initialize Configured MCP Servers on Daemon Start
  - Built on modern architecture
  - Requires modern entry point only

## Questions & Clarifications

**Q: Can't I just keep the legacy scripts around "just in case"?**
A: This perpetuates technical debt and confuses users. The migration is simple and the modern command is feature-complete. Time to make a clean break.

**Q: What if someone has hardcoded scripts using legacy commands?**
A: We'll provide a clear migration guide and help during the transition period. The commands are 1-to-1 compatible with minor syntax adjustments.

**Q: Does this break Docker containers using `python mcp_*.py`?**
A: Yes, but it's a simple change in the Dockerfile `CMD` instruction. See migration guide examples.

**Q: How long will the transition period be?**
A: The deprecation warnings will stay for at least one full major version. Users have plenty of time to adapt.

**Q: Will the `cllm-mcp` command work if I don't install the package?**
A: You can still use `python -m cllm_mcp` if developing locally, but the entry point requires installation (or `uv run`).

**Q: What about shell aliases or scripts in my `/usr/local/bin`?**
A: Just update them to call `cllm-mcp` instead. See migration guide.

**Q: Is there a wrapper I can use temporarily?**
A: Yes, create a simple `mcp_cli.py` in your project:
```python
#!/usr/bin/env python
"""Wrapper for legacy compatibility during migration"""
import subprocess
import sys
subprocess.run(["cllm-mcp"] + sys.argv[1:])
```

## References

- **CLLM Configuration Standard**: https://github.com/o3-cloud/cllm
- **Python Entry Points**: https://packaging.python.org/specifications/entry-points/
- **ADR-0003**: Unified Daemon/Client Command Architecture
- **ADR-0004**: Standardize Configuration Using CLLM-Style Configuration Precedence
- **Semantic Versioning**: https://semver.org/ (Major version bump for breaking changes)
- **Package Distribution Best Practices**: https://packaging.python.org/

## Sign-Off

**Proposed by**: Claude Code
**Date**: November 13, 2025
**Implemented by**: Claude Code
**Implementation Date**: November 13, 2025
**Status**: Accepted and Implemented

## Implementation Details

- ✅ Removed legacy script entry points from `pyproject.toml`
- ✅ Updated README to remove legacy command documentation
- ✅ Created MIGRATION.md user guide
- ✅ Added ADR-0007 reference to README
- ✅ Updated pyproject.toml coverage configuration
- ✅ Refactored `mcp_cli.py` → `cllm_mcp/client.py` with clean imports
- ✅ Refactored `mcp_daemon.py` → `cllm_mcp/daemon.py` with clean imports
- ✅ Updated `cllm_mcp/main.py` to use relative imports
- ✅ Deleted root-level legacy files
- ✅ Verified all commands work (list-tools, call-tool, daemon, config)
- ✅ Users can only access via `cllm-mcp` command
