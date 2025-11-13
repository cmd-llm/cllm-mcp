# Migration Guide: From Legacy Commands to cllm-mcp

This guide helps you migrate from the deprecated legacy Python script entry points to the modern `cllm-mcp` command.

## Quick Start (Already Updated! ✅)

The modern `cllm-mcp` command is the only way to use the tool. Legacy `python mcp_cli.py` and `python mcp_daemon.py` commands no longer work as user-facing entry points.

### Using cllm-mcp

```bash
# The only command you need
cllm-mcp list-tools filesystem
cllm-mcp daemon status
cllm-mcp call-tool filesystem read-file '{"path": "/tmp/file.txt"}'
```

That's it! All functionality is available through `cllm-mcp`.

## What Changed?

Starting with **v2.0.0**, the legacy Python script entry points have been removed:

| What | Before (v1.x) | After (v2.0+) |
|------|---------------|---------------|
| Direct script | `python mcp_cli.py` | ❌ Removed |
| Daemon script | `python mcp_daemon.py` | ❌ Removed |
| Modern command | `cllm-mcp` | ✅ Still works |

**Good news**: The `cllm-mcp` command has all the same functionality!

## Why This Change?

✅ **Cleaner code**: Single code path to maintain
✅ **Simpler package**: Smaller distribution
✅ **Aligned standards**: Follows CLLM ecosystem conventions
✅ **Better UX**: Clear, modern entry point for new users
✅ **Easier maintenance**: Fewer code paths to test and maintain

## Migration by Use Case

### Individual Developers

#### Before (v1.x)
```bash
# List available tools
python mcp_cli.py list-tools filesystem

# Call a tool
python mcp_cli.py call-tool filesystem read-file /path/to/file

# Start daemon
python mcp_daemon.py daemon start

# Check daemon status
python mcp_daemon.py daemon status

# Stop daemon
python mcp_daemon.py daemon stop
```

#### After (v2.0+)
```bash
# Install (one time)
pip install --upgrade cllm-mcp

# List available tools
cllm-mcp list-tools filesystem

# Call a tool
cllm-mcp call-tool filesystem read-file /path/to/file

# Start daemon
cllm-mcp daemon start

# Check daemon status
cllm-mcp daemon status

# Stop daemon
cllm-mcp daemon stop
```

#### Update Aliases

If you have shell aliases:
```bash
# Remove or update these lines from ~/.bashrc or ~/.zshrc

# Old way (won't work anymore)
# alias mcp-cli="python mcp_cli.py"
# alias mcp-daemon="python mcp_daemon.py"

# New way (optional, works with v2.0+)
alias mcp="cllm-mcp"
alias mcp-cli="cllm-mcp"
alias mcp-daemon="cllm-mcp daemon"
```

Then reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc
```

### Project Maintainers

#### Update Your Project Scripts

If your project calls MCP commands:

**Before** (docs/examples/run-mcp.sh):
```bash
#!/bin/bash
set -e

python mcp_cli.py list-tools filesystem
python mcp_daemon.py daemon start
```

**After**:
```bash
#!/bin/bash
set -e

# Ensure cllm-mcp is installed
command -v cllm-mcp >/dev/null || pip install cllm-mcp

cllm-mcp list-tools filesystem
cllm-mcp daemon start
```

#### Update Documentation Examples

Replace all documentation examples:
```markdown
<!-- Before -->
```bash
python mcp_cli.py list-tools filesystem
```

<!-- After -->
```bash
cllm-mcp list-tools filesystem
```

#### Update CI/CD Workflows

**Before** (.github/workflows/test.yml):
```yaml
- run: python mcp_cli.py list-tools filesystem
- run: python mcp_daemon.py daemon start
```

**After**:
```yaml
- run: pip install cllm-mcp
- run: cllm-mcp list-tools filesystem
- run: cllm-mcp daemon start
```

Or if you're testing the package itself:
```yaml
- run: pip install -e .
- run: cllm-mcp list-tools filesystem
- run: cllm-mcp daemon start
```

### Docker/Container Users

#### Before (Dockerfile)
```dockerfile
FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["python", "mcp_daemon.py", "daemon", "start"]
```

#### After (Dockerfile)
```dockerfile
FROM python:3.12
WORKDIR /app
RUN pip install cllm-mcp
CMD ["cllm-mcp", "daemon", "start"]
```

Or if building from source:
```dockerfile
FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["cllm-mcp", "daemon", "start"]
```

#### Docker Compose

**Before** (docker-compose.yml):
```yaml
services:
  mcp-daemon:
    build: .
    command: python mcp_daemon.py daemon start
    volumes:
      - ./config:/etc/mcp-config.json
```

**After**:
```yaml
services:
  mcp-daemon:
    build: .
    command: cllm-mcp daemon start
    volumes:
      - ~/.cllm:/root/.cllm  # Use CLLM standard config location
```

### Development Setup

#### Before (local development)
```bash
# Clone repo
git clone https://github.com/o3-cloud/cllm-mcp.git
cd cllm-mcp

# Install in development mode
pip install -e .

# Run legacy scripts
python mcp_cli.py list-tools filesystem
```

#### After (local development)
```bash
# Clone repo
git clone https://github.com/o3-cloud/cllm-mcp.git
cd cllm-mcp

# Install in development mode
pip install -e .

# OR use uv for simpler commands
uv run cllm-mcp list-tools filesystem

# Run modern command
cllm-mcp list-tools filesystem
```

## Configuration: No Changes Required

Your configuration files don't need to change! The CLLM configuration system (ADR-0004) is fully backward compatible:

**Your existing configs in these locations will still work**:
```
~/.config/cllm-mcp/config.json      ← Still works (old path)
~/.cllm/mcp-config.json             ← Recommended (CLLM standard)
./.cllm/mcp-config.json             ← Project config
./mcp-config.json                   ← Current directory
```

**No migration needed** - just upgrade to v2.0+!

## Troubleshooting

### "Command not found: cllm-mcp"

**Solution**: Install the package:
```bash
pip install --upgrade cllm-mcp
```

Verify installation:
```bash
cllm-mcp --version
```

### "ImportError: Cannot import mcp_cli"

**Solution**: You're trying to import the legacy module directly. Use the command instead:
```bash
# Don't do this:
python -c "from mcp_cli import ..."

# Do this instead:
cllm-mcp [command]
```

### Old scripts still in my project

**Solution**: Update all references to use `cllm-mcp`:
```bash
# Find all old references
grep -r "mcp_cli.py" .
grep -r "mcp_daemon.py" .

# Replace them with cllm-mcp
# Example: sed -i 's/python mcp_cli.py/cllm-mcp/g' <file>
```

### Configuration not found

**Solution**: Verify config location using debug mode:
```bash
cllm-mcp --verbose list-tools filesystem
# This will show which config file was used
```

See [ADR-0004: Configuration Documentation](docs/decisions/0004-standardize-configuration-with-cllm-folder.md) for details.

### Daemon won't start

**Solution**: Check the logs:
```bash
# Start with verbose output
cllm-mcp daemon start --verbose

# Or check daemon status
cllm-mcp daemon status
```

## FAQ

### Q: Do I need to update my configuration files?
**A**: No! Configuration is fully backward compatible. See "Configuration: No Changes Required" section above.

### Q: What if I'm still on v1.x?
**A**: Legacy scripts still work, but with deprecation warnings. You can upgrade at your own pace. We recommend upgrading before v2.0 to avoid any issues.

### Q: Can I have a wrapper script for backward compatibility?
**A**: Sure! Create a simple wrapper:

**mcp_cli.py** (wrapper):
```python
#!/usr/bin/env python
"""Wrapper for backward compatibility during migration"""
import subprocess
import sys

print("Warning: mcp_cli.py is deprecated. Use 'cllm-mcp' instead.")
sys.exit(subprocess.call(["cllm-mcp"] + sys.argv[1:]))
```

**mcp_daemon.py** (wrapper):
```python
#!/usr/bin/env python
"""Wrapper for backward compatibility during migration"""
import subprocess
import sys

print("Warning: mcp_daemon.py is deprecated. Use 'cllm-mcp daemon' instead.")
sys.exit(subprocess.call(["cllm-mcp", "daemon"] + sys.argv[1:]))
```

### Q: What if I have a complex setup with the old scripts?
**A**: [Create an issue](https://github.com/o3-cloud/cllm-mcp/issues) with details, and we'll help you migrate.

### Q: Is the daemon auto-initialization still available?
**A**: Yes! Daemon auto-initialization (ADR-0005) works with the modern command:
```bash
cllm-mcp daemon start  # Servers auto-initialize from config
```

### Q: Do I need to change my CI/CD configuration?
**A**: Yes, update your workflows to use `cllm-mcp` instead of the Python scripts. See examples above.

### Q: How long will the transition period last?
**A**:
- **v1.x**: Legacy scripts work with deprecation warnings
- **v2.0+**: Legacy scripts removed
- **Recommended**: Migrate before v2.0 release

### Q: What if I find a bug while migrating?
**A**: [Report it](https://github.com/o3-cloud/cllm-mcp/issues) with:
- Your current v1.x or v2.0+ version
- The command you're trying to run
- The error message
- Your setup details

## Need More Help?

- 📖 **Documentation**: [cllm-mcp docs](https://github.com/o3-cloud/cllm-mcp/docs)
- 📝 **Architecture Decision**: [ADR-0007](docs/decisions/0007-drop-legacy-commands-modernize-config.md)
- 💬 **GitHub Discussions**: [Ask questions](https://github.com/o3-cloud/cllm-mcp/discussions)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/o3-cloud/cllm-mcp/issues)

## Timeline

| Version | Status | Legacy Support | Recommendation |
|---------|--------|-----------------|-----------------|
| v1.0-1.1 | Current | ✅ Works | Use freely, both ways work |
| v1.2+ | Deprecated | ⚠️ Warnings | Update to modern command |
| v2.0+ | Latest | ❌ Removed | Must use modern command |
| v3.0+ | Future | ❌ Removed | Modern command only |

---

**Last Updated**: November 13, 2025
**Status**: Proposed with ADR-0007
**Related**: [ADR-0003], [ADR-0004], [ADR-0005]
