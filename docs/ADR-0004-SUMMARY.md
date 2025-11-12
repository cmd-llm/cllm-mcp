# ADR-0004 Summary: Standardize Configuration with CLLM Folder

## Quick Overview

**Title**: Standardize Configuration Using CLLM-Style Configuration Precedence

**Status**: Proposed

**Goal**: Adopt the CLLM ecosystem's well-established configuration precedence pattern and standardize the use of `.cllm` folder for MCP configuration management.

---

## The Problem

Currently, cllm-mcp has an ad-hoc configuration file search order that doesn't align with industry standards or the CLLM ecosystem conventions. This creates confusion about which configuration file is active and doesn't support the common pattern of global defaults with project-specific overrides.

## The Solution

Adopt CLLM's configuration precedence (lowest to highest priority):

```
1. ~/.cllm/mcp-config.json          (Global defaults)
2. ./.cllm/mcp-config.json          (Project-specific)
3. ./mcp-config.json                (Current directory)
4. Environment variables            (CLLM_MCP_* prefix)
5. CLI arguments                    (Highest priority)
```

## Key Benefits

✅ **Ecosystem Alignment**: Matches CLLM and other established tools (Terraform, Docker, etc.)

✅ **Clear Precedence**: Users understand which config is active and why

✅ **Flexible**: Supports global defaults with project overrides

✅ **CI/CD Friendly**: Environment variable support for automation

✅ **Well-Organized**: Separated into `.cllm` folders

✅ **Version Control Friendly**: Global vs. local configs managed separately

✅ **Verbose Tracing**: Show which config was chosen with `--verbose`

## Configuration Locations

| Location | File Name | Purpose | Checked First | Example |
|----------|-----------|---------|---------------|---------|
| Home | `~/.cllm/mcp-config.json` | Global defaults | 1st (lowest priority) | User's preferred servers |
| Project | `./.cllm/mcp-config.json` | Project-specific | 2nd | Project-specific server configs |
| CWD | `./mcp-config.json` | Current directory | 3rd | Temporary overrides |
| Env Vars | `CLLM_MCP_*` | Environment | 4th | CI/CD, containerized |
| CLI | `--config` | Command-line | 5th (highest) | Explicit overrides |

## Implementation Plan

### Phase 1: Foundation (Weeks 1-2)
- Update configuration search algorithm in `config.py`
- Add `.cllm` folder support
- Implement environment variable parsing
- Add verbose configuration tracing

### Phase 2: Tooling (Weeks 3-4)
- `cllm-mcp config show` - Display active configuration
- `cllm-mcp config migrate` - Automated migration tool
- Deprecation warnings for old paths
- Migration guide documentation

### Phase 3: Documentation (Week 5)
- Update README
- Create migration guide
- Document environment variables
- Provide example configurations

### Phase 4: Cleanup (Year 2+)
- Remove backward compatibility after deprecation period
- Archive migration tools

## Example Usage

```bash
# Create global default configuration
mkdir -p ~/.cllm
cat > ~/.cllm/mcp-config.json << 'EOF'
{
  "mcpServers": {
    "time": {
      "command": "uvx",
      "args": ["mcp-server-time"]
    }
  }
}
EOF

# Create project-specific configuration
mkdir -p .cllm
cat > .cllm/mcp-config.json << 'EOF'
{
  "mcpServers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem", "./data"]
    }
  }
}
EOF

# Use it - will check both configs, merging project-specific over global
cllm-mcp list-tools time       # Uses ~/.cllm/mcp-config.json
cllm-mcp list-tools filesystem # Uses .cllm/mcp-config.json
```

## Environment Variables

Configuration can be overridden via environment variables:

```bash
# Override config file path
export CLLM_MCP_CONFIG=/path/to/config.json

# Override daemon socket
export CLLM_MCP_SOCKET=/custom/socket.sock

# Disable daemon
export CLLM_MCP_NO_DAEMON=true

# Enable verbose mode
export CLLM_MCP_VERBOSE=true
```

## Configuration Tracing

With `--verbose` flag, see which configuration was chosen:

```bash
$ cllm-mcp --verbose list-tools time

[CONFIG] Searching for configuration...
[CONFIG] Checked: ~/.cllm/mcp-config.json (found)
[CONFIG] Checked: ./.cllm/mcp-config.json (not found)
[CONFIG] Checked: ./mcp-config.json (not found)
[CONFIG] Using: ~/.cllm/mcp-config.json
[CONFIG] Servers available: time, filesystem
```

## Migration Path

**Year 1**: Old configuration paths still work (with deprecation warnings)
- `~/.config/cllm-mcp/config.json` (deprecated)
- `/etc/cllm-mcp/config.json` (deprecated)

**Year 2**: Warnings become more prominent
- Provide automated `cllm-mcp config migrate` tool
- Update all documentation

**Year 3+**: Old paths no longer supported
- Users must use new `.cllm` structure

## Design Rationale

This approach was chosen because it:
1. Aligns with established CLLM ecosystem conventions
2. Follows patterns from Terraform, Docker, and similar tools
3. Provides flexibility for different deployment scenarios
4. Is familiar to developers who use these tools
5. Supports both global and project-specific configurations
6. Enables CI/CD automation through environment variables

## Related Decisions

- **ADR-0003**: Unified Daemon/Client Command Architecture
  - Provides the foundation for configuration management
  - This ADR builds upon the config subsystem from ADR-0003

- **ADR-0001**: Adopt Vibe ADR Framework
  - Follows the same ADR structure and process

---

## Questions?

**Q: Why `.cllm` instead of `.mcp`?**
A: The `.cllm` folder is recognized across the CLLM ecosystem, so tools can coordinate on a common location.

**Q: What about backward compatibility?**
A: Year 1 includes full backward compatibility with old paths (with warnings). Old configs will continue to work.

**Q: How are multiple configs merged?**
A: Highest priority config is used. Use `cllm-mcp config show` to see which file is active.

**Q: Can I use YAML?**
A: JSON is the primary format for MVP. YAML support can be added in Phase 2 if needed.

---

**Proposed**: November 12, 2025
**Status**: Awaiting Review and Approval
**Next Steps**: Team review, stakeholder feedback, implementation planning
