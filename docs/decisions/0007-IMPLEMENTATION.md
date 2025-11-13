# ADR-0007 Implementation Guide: Dropping Legacy Commands

## Overview

This document provides specific implementation details, version timelines, and step-by-step migration guidance for ADR-0007: Drop Legacy Commands (Backward Compatible) and Modernize Entry Points.

## Deprecation Timeline & Version Roadmap

### v1.x Series - Current & Transition Period

#### v1.0.0 - Foundation (Current)

- **Status**: Pre-release or recent
- **Legacy Scripts**: `mcp_cli.py` and `mcp_daemon.py` still present and functional
- **Modern Command**: `cllm-mcp` works via installed package
- **Configuration**: Full CLLM precedence support (ADR-0004)
- **User Action**: None required; both paths work

#### v1.1.0 - Deprecation Warnings (Recommended)

- **Timeline**: 1-2 releases after v1.0.0
- **Status**: Add warnings to legacy scripts
- **Changes**:

  ```python
  # mcp_cli.py and mcp_daemon.py startup
  import warnings
  warnings.warn(
      "Running MCP via direct Python scripts is deprecated. "
      "Please upgrade to: pip install --upgrade cllm-mcp && cllm-mcp [command]\n"
      "See: https://github.com/o3-cloud/cllm-mcp/docs/MIGRATION.md",
      DeprecationWarning,
      stacklevel=2
  )
  ```

- **Exit Status**: Commands succeed but print warning to stderr
- **Documentation**: Add "Deprecation" section to README
- **User Action**: Update scripts/aliases to use `cllm-mcp` command

#### v1.2.0+ - Transition Series

- **Status**: Legacy scripts still work with warnings
- **Focus**: Bug fixes and improvements to modern command only
- **No new features**: Added only to modern code path
- **Configuration**: Continued support for old config paths (ADR-0004 backward compatibility)
- **User Action**: Continue migration to modern command

### v2.0.0 - Major Breaking Release

#### v2.0.0 - Legacy Removal (First Major Version Bump)

- **Timeline**: After v1.x transition period (suggest 6+ months or 3+ minor releases)
- **Status**: Legacy scripts completely removed
- **Changes**:
  - Delete `mcp_cli.py` (543 lines)
  - Delete `mcp_daemon.py` (100+ lines)
  - Remove from source distribution
  - Remove from package data

- **Documentation**: Add prominent migration notice
- **CHANGELOG**: Major breaking change clearly marked
- **User Action**: MUST have migrated to `cllm-mcp` command

#### v2.0.0+ - Modern Era

- **Status**: Single authoritative code path
- **Focus**: New features, improvements
- **Distribution**: Cleaner, smaller package
- **Configuration**: Old config paths deprecated but still supported via compatibility layer

### v3.0.0+ - Future (Complete Modernization)

#### v3.0.0 - Configuration Migration

- **Status**: Remove old config path support
- **Changes**: Old paths (`~/.config/cllm-mcp/`) no longer checked
- **Migration Path**: `cllm-mcp config migrate` command to help (if not done already)
- **Documentation**: Clear guide on `.cllm/` folder structure
- **User Action**: Must have config in CLLM paths

## Implementation Phases Detailed

### Phase 1: Preparation (Sprint 1)

#### 1.1 Create Migration Materials

**File**: `docs/MIGRATION.md` (new)

```markdown
# Migration Guide: From Legacy Scripts to cllm-mcp

## Quick Start

- Install: `pip install --upgrade cllm-mcp`
- Update scripts: Replace `python mcp_cli.py` with `cllm-mcp`
- Done!

## Detailed Migration

[See section below for detailed guide]

## FAQ

[See section below for frequently asked questions]
```

#### 1.2 Add Deprecation Warnings

**File**: `mcp_cli.py` (modify)

```python
#!/usr/bin/env python
"""
DEPRECATED: Direct MCP client script

This script is deprecated. Please use the installed cllm-mcp command instead:
    pip install --upgrade cllm-mcp
    cllm-mcp [command]

See: https://github.com/o3-cloud/cllm-mcp/docs/MIGRATION.md
"""

import sys
import warnings

def main():
    warnings.warn(
        "Running MCP via 'python mcp_cli.py' is deprecated. "
        "Please use the installed command instead:\n\n"
        "  pip install --upgrade cllm-mcp\n"
        "  cllm-mcp list-tools <server>\n\n"
        "See: https://github.com/o3-cloud/cllm-mcp/docs/MIGRATION.md",
        DeprecationWarning,
        stacklevel=2
    )

    # Continue with existing implementation
    # ... rest of code unchanged ...

if __name__ == "__main__":
    main()
```

**File**: `mcp_daemon.py` (modify)

```python
#!/usr/bin/env python
"""
DEPRECATED: Direct MCP daemon script

This script is deprecated. Please use the installed cllm-mcp command instead:
    pip install --upgrade cllm-mcp
    cllm-mcp daemon start

See: https://github.com/o3-cloud/cllm-mcp/docs/MIGRATION.md
"""

import sys
import warnings

def main():
    warnings.warn(
        "Running MCP daemon via 'python mcp_daemon.py' is deprecated. "
        "Please use the installed command instead:\n\n"
        "  pip install --upgrade cllm-mcp\n"
        "  cllm-mcp daemon start\n\n"
        "See: https://github.com/o3-cloud/cllm-mcp/docs/MIGRATION.md",
        DeprecationWarning,
        stacklevel=2
    )

    # Continue with existing implementation
    # ... rest of code unchanged ...

if __name__ == "__main__":
    main()
```

#### 1.3 Update README

**File**: `README.md` (modify)

- Move legacy commands section to "Deprecated Commands" at end of document
- Add prominent "Installation" section near top:

  ````markdown
  ## Installation

  ```bash
  pip install cllm-mcp
  cllm-mcp --version
  cllm-mcp list-tools <server>
  ```
  ````

  ```

  ```

- Add deprecation notice:
  ```markdown
  > **Note**: Direct Python script execution (`python mcp_cli.py`, `python mcp_daemon.py`) is deprecated.
  > Please use the installed `cllm-mcp` command. See [Migration Guide](docs/MIGRATION.md).
  ```

#### 1.4 Update CI/CD

**File**: `.github/workflows/*.yml` (modify)

Replace all instances of:

```yaml
- run: python mcp_cli.py list-tools
- run: python mcp_daemon.py daemon start
```

With:

```yaml
- run: uv run cllm-mcp list-tools
- run: uv run cllm-mcp daemon start
```

Or after install:

```yaml
- run: pip install -e .
- run: cllm-mcp list-tools
- run: cllm-mcp daemon start
```

#### 1.5 Create .gitignore Updates

**File**: `.gitignore` (verify)

```
# Remove if present (legacy scripts no longer distributed)
# mcp_cli.py
# mcp_daemon.py

# These should already be there
__pycache__/
*.egg-info/
.venv/
```

### Phase 2: Removal (Sprint 2)

#### 2.1 Delete Legacy Scripts

```bash
git rm mcp_cli.py
git rm mcp_daemon.py
```

#### 2.2 Update Package Configuration

**File**: `pyproject.toml` (verify/update)

Before:

```toml
[project]
name = "cllm-mcp"
# ... other config ...
scripts = {
    cllm-mcp = "cllm_mcp.main:cli",
    # No mcp_cli or mcp_daemon entry
}
```

After (verify same, legacy already removed from scripts):

```toml
[project]
name = "cllm-mcp"
# ... other config ...

[project.scripts]
cllm-mcp = "cllm_mcp.main:cli"

# Optional: convenience aliases (discuss with team)
# mcp-cli = "cllm_mcp.main:cli"
# mcp-daemon = "cllm_mcp.main:cli"
```

#### 2.3 Update Package Manifest

**File**: `MANIFEST.in` (if exists, verify)

- Ensure legacy scripts are NOT included in distribution
- Typical pattern:

```
include README.md
include LICENSE
recursive-include cllm_mcp *.py
recursive-include tests *.py
recursive-include docs *.md
# NOT including mcp_*.py scripts
```

#### 2.4 Update Version in Code

**File**: `cllm_mcp/__init__.py` or version file

```python
__version__ = "2.0.0"  # Major version bump for breaking change
```

#### 2.5 Update CHANGELOG

**File**: `CHANGELOG.md` or `NEWS.md` (create/update)

````markdown
# Changelog

## [2.0.0] - 2025-XX-XX (Breaking Release)

### BREAKING CHANGES

- **REMOVED**: Legacy Python scripts (`mcp_cli.py`, `mcp_daemon.py`)
  - Users must use the installed `cllm-mcp` command instead
  - Migration is simple: `pip install cllm-mcp && cllm-mcp [command]`
  - See [Migration Guide](docs/MIGRATION.md) for details

### Reasons for Removal

- Reduces technical debt and code duplication
- Aligns with CLLM ecosystem distribution standards
- Simplifies maintenance and testing
- Cleaner, smaller package distribution
- Single authoritative code path

### Upgrade Path

1. Install latest: `pip install --upgrade cllm-mcp>=2.0.0`
2. Update scripts: Replace `python mcp_cli.py` with `cllm-mcp`
3. Configuration: Unchanged (fully backward compatible via ADR-0004)

### Migration Examples

```bash
# Before (deprecated)
python mcp_cli.py list-tools filesystem
python mcp_daemon.py daemon start

# After (required)
cllm-mcp list-tools filesystem
cllm-mcp daemon start
```
````

### What's Unchanged

- All command functionality is identical
- Configuration system fully backward compatible
- All features work exactly the same
- No breaking changes to APIs or configuration

### Support

- [Migration Guide](docs/MIGRATION.md) - Detailed instructions for all scenarios
- [FAQ](docs/FAQ.md#migration) - Common migration questions
- GitHub Issues - Ask for help if needed

## [1.2.x] - Legacy Warning Phase

- Added deprecation warnings to `mcp_cli.py` and `mcp_daemon.py`
- Recommended upgrading to use `cllm-mcp` command
- Full backward compatibility maintained

## [1.0.0] - Initial Unified Architecture

- [Previous release notes...]

````

### Phase 3: Release & Communication (Sprint 2-3)

#### 3.1 Create Release Notes

**File**: GitHub Release Draft

```markdown
# 🎯 v2.0.0: Modernization Release

## What's New

### ✨ Simplified Entry Point
We've removed the legacy Python script entry points and now offer a single,
clean command-line interface aligned with CLLM ecosystem standards.

## Breaking Changes ⚠️

**Removed**: Direct Python script execution
- ❌ `python mcp_cli.py` (use `cllm-mcp` instead)
- ❌ `python mcp_daemon.py` (use `cllm-mcp daemon` instead)

## Migration (Takes 2 Minutes)

### Step 1: Install
```bash
pip install --upgrade cllm-mcp
````

### Step 2: Update Your Scripts

```bash
# Before
python mcp_cli.py list-tools filesystem

# After
cllm-mcp list-tools filesystem
```

### Step 3: Done! 🎉

```bash
cllm-mcp --version
```

## Detailed Migration Guide

See [MIGRATION.md](https://github.com/o3-cloud/cllm-mcp/docs/MIGRATION.md)

- [For Individual Users](docs/MIGRATION.md#for-individual-users)
- [For Project Maintainers](docs/MIGRATION.md#for-project-maintainers)
- [For Container/Docker Users](docs/MIGRATION.md#for-containerdocker-users)
- [FAQ](docs/MIGRATION.md#faq)

## Why This Change?

✅ **Cleaner Code**: Single authoritative implementation
✅ **Easier Maintenance**: Fewer code paths to maintain
✅ **Aligned Standards**: Follows CLLM ecosystem conventions
✅ **Better Distribution**: Cleaner, smaller package
✅ **Clear Path**: No ambiguity for new users

## What's NOT Changing

✅ **Configuration**: Fully backward compatible (ADR-0004)
✅ **Commands**: All CLI features work identically
✅ **APIs**: No changes to programmatic interfaces
✅ **Functionality**: Everything works exactly the same

## Questions?

- 📖 [Migration Guide](docs/MIGRATION.md)
- ❓ [FAQ](docs/FAQ.md#migration)
- 💬 [GitHub Discussions](https://github.com/o3-cloud/cllm-mcp/discussions)
- 📝 [ADR-0007: Architecture Decision](docs/decisions/0007-drop-legacy-commands-modernize-config.md)

```

#### 3.2 Create Announcement

**Channels**:
- GitHub Release notes (above)
- README prominent badge
- GitHub Discussions announcement
- Documentation site banner
- Any project documentation

Sample announcement:
```

🎯 v2.0.0 Released - Simplified Entry Points

We've modernized the command-line interface by removing legacy Python script entry points.
All functionality is available via the single 'cllm-mcp' command.

⏱️ Migration takes ~2 minutes: pip install cllm-mcp && update your scripts

📖 Full guide: https://github.com/o3-cloud/cllm-mcp/docs/MIGRATION.md

````

### Phase 4: Support & Cleanup (Sprint 3+)

#### 4.1 Monitor for Issues

Set up GitHub issue template for migration:

```markdown
---
name: Migration Help
about: Need help migrating from legacy scripts to cllm-mcp
---

## Current Setup
- How are you currently running MCP? (e.g., `python mcp_cli.py`)
- OS/Python version:
- Current configuration location:

## Help Needed
- What command are you trying to run?
- What errors are you seeing?

## Resources
- [Migration Guide](docs/MIGRATION.md)
- [FAQ](docs/FAQ.md#migration)
````

#### 4.2 Create FAQ

**File**: `docs/FAQ.md` (add section)

````markdown
## FAQ: Migration from Legacy Scripts

### Q: Why was this change made?

**A**: To reduce technical debt, align with CLLM standards, and provide a cleaner distribution.

### Q: Do I need to migrate immediately?

**A**: No, v1.x continues to work, but v2.0+ requires migration. See [timeline](docs/decisions/0007-drop-legacy-commands-modernize-config.md#deprecation-timeline--version-roadmap).

### Q: Will my existing configurations still work?

**A**: Yes! The configuration system (ADR-0004) is fully backward compatible. Old paths still work.

### Q: What if I have `mcp_cli.py` in my PATH?

**A**: After upgrading to v2.0, the script won't exist. Update your PATH or use `cllm-mcp` directly.

### Q: How do I update my shell scripts?

**A**: Replace:

```bash
# Before
python mcp_cli.py list-tools filesystem

# After
cllm-mcp list-tools filesystem
```
````

### Q: What if I'm developing locally?

**A**: Use `uv run cllm-mcp` or `python -m cllm_mcp` instead.

### Q: Will the daemon still auto-initialize servers?

**A**: Yes, ADR-0005 daemon auto-initialization works with the modern command.

### Q: Where do I report migration issues?

**A**: [GitHub Issues](https://github.com/o3-cloud/cllm-mcp/issues) with label "migration"

[More FAQ items...]

````

#### 4.3 Provide Support

Create a GitHub Discussions category for migration help and monitor it during the first few releases.

## Detailed Migration Paths by Use Case

### Use Case 1: Individual Developer Using Legacy Commands

**Before (v1.x or earlier)**:
```bash
# In shell or scripts
python mcp_cli.py list-tools filesystem
python mcp_cli.py call-tool filesystem read-file /path
python mcp_daemon.py daemon start
````

**Migration Steps**:

```bash
# Step 1: Install
pip install --upgrade cllm-mcp

# Step 2: Replace in scripts
# Just replace 'python mcp_cli.py' with 'cllm-mcp'
cllm-mcp list-tools filesystem
cllm-mcp call-tool filesystem read-file /path
cllm-mcp daemon start

# Step 3: Update shell aliases (if you have them)
# Before: alias mcp-cli="python mcp_cli.py"
# After: remove or change to: alias mcp="cllm-mcp"
```

**After (v2.0+)**:

```bash
cllm-mcp list-tools filesystem
```

### Use Case 2: Development Setup with `uv`

**Before**:

```bash
# Would use uv run with python command
uv run python mcp_cli.py list-tools filesystem
```

**After**:

```bash
# Direct uv run with cllm-mcp
uv run cllm-mcp list-tools filesystem
```

### Use Case 3: Docker/Container

**Before**:

```dockerfile
FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["python", "mcp_daemon.py", "daemon", "start"]
```

**After**:

```dockerfile
FROM python:3.12
WORKDIR /app
RUN pip install cllm-mcp
CMD ["cllm-mcp", "daemon", "start"]
```

### Use Case 4: Project Integration Script

**Before**:

```bash
#!/bin/bash
set -e

cd "$(dirname "$0")"
python mcp_cli.py list-tools filesystem
python mcp_daemon.py daemon start
```

**After**:

```bash
#!/bin/bash
set -e

# Ensure cllm-mcp is installed
command -v cllm-mcp >/dev/null || pip install cllm-mcp

cd "$(dirname "$0")"
cllm-mcp list-tools filesystem
cllm-mcp daemon start
```

### Use Case 5: GitHub Actions / CI/CD

**Before**:

```yaml
name: Test MCP

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      - run: pip install -e .
      - run: python mcp_cli.py list-tools filesystem
      - run: python -m pytest tests/
```

**After**:

```yaml
name: Test MCP

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      - run: pip install -e .
      - run: cllm-mcp list-tools filesystem
      - run: python -m pytest tests/
```

## Testing the Migration

### Verification Checklist

- [ ] New package installs cleanly: `pip install cllm-mcp`
- [ ] Help works: `cllm-mcp --help`
- [ ] List tools works: `cllm-mcp list-tools <server>`
- [ ] Call tool works: `cllm-mcp call-tool <server> <tool> <args>`
- [ ] Daemon starts: `cllm-mcp daemon start`
- [ ] Daemon status: `cllm-mcp daemon status`
- [ ] Daemon stops: `cllm-mcp daemon stop`
- [ ] Config precedence works (ADR-0004)
- [ ] Old config paths still found (backward compat)
- [ ] Help references are accurate

### Edge Case Testing

- [ ] User with old scripts in PATH still gets clear error
- [ ] User with shell aliases that reference old scripts
- [ ] User with Docker containers using old commands
- [ ] User with deployment scripts calling legacy paths
- [ ] User with venv containing old entry points

## Rollback Plan (If Needed)

If critical issues discovered after removing legacy scripts:

1. **Patch Release**: v2.0.1
   - Restore legacy scripts with deprecation warnings
   - Document the issue
   - Fix the underlying issue

2. **New Release**: v2.1.0
   - Remove legacy scripts again after fixing
   - Extensive testing

3. **Version Strategy**:
   - v2.0.0: Initial removal (potential rollback)
   - v2.1.0+: Stable without legacy scripts

## Success Metrics

Measure success of migration through:

1. **GitHub Issues**: Track migration-related issues
   - Target: <5 migration questions in first month of v2.0
   - Resolution time: <24 hours

2. **Installation Stats**: Track pip installs
   - Should see smooth upgrade path to v2.0

3. **Documentation**: Monitor engagement
   - Migration guide visits
   - FAQ views
   - Documentation clarity feedback

4. **Support Load**: Track support requests
   - Migration-related issues should decrease over time
   - FAQ should cover 95% of questions

5. **Release Adoption**:
   - v2.0 adoption rate after 1 month
   - v1.x usage rate after 3 months (should be declining)
   - Full migration by v2.2 or v3.0
