# ADR-0004: Standardize Configuration Using CLLM-Style Configuration Precedence

## Status

Proposed

## Context

The cllm-mcp project currently supports configuration file discovery across multiple locations, but lacks a standardized, hierarchical configuration approach. Current configuration search locations are ad-hoc and don't align with common practices in the CLLM (Claude Language Model Manager) ecosystem.

### Current State

The current configuration management (from ADR-0003) searches for `config.json` in:
1. Explicitly specified path (`--config` flag)
2. `~/.config/cllm-mcp/config.json` (user's XDG config directory)
3. `~/.cllm/config.json` (home directory)
4. `/etc/cllm-mcp/config.json` (system-wide)
5. Current working directory

**Issues with current approach**:
- Ad-hoc search order without clear precedence rules
- No project-specific configuration support
- Doesn't align with CLLM ecosystem conventions
- Difficult for users to understand which config is active
- Inconsistent with industry standards (Terraform, Docker Compose, etc.)

### CLLM Configuration Precedence Standard

The CLLM ecosystem defines a well-established configuration precedence (lowest to highest priority):

1. **Global defaults**: `~/.cllm/Cllmfile.yml` (or mcp-config.json)
2. **Project-specific**: `./.cllm/Cllmfile.yml` (or mcp-config.json)
3. **Current directory**: `./Cllmfile.yml` (or mcp-config.json)
4. **Environment variables**: `CLLM_MCP_*` prefixed variables
5. **CLI arguments**: Always take precedence

**Advantages of this approach**:
- Widely recognized pattern in development tools
- Allows global defaults and project-level overrides
- Clear, predictable resolution order
- Aligns with other CLLM tools
- Supports both global and local configurations
- Environment-based configuration for CI/CD

## Decision

We will adopt the CLLM configuration precedence pattern for mcp-config.json files:

### Configuration File Locations

The new standardized search order (lowest to highest priority):

```
1. ~/.cllm/mcp-config.json                    # Global defaults
2. ./.cllm/mcp-config.json                    # Project-specific
3. ./mcp-config.json                          # Current directory
4. Environment variables (CLLM_MCP_*)         # Environment configuration
5. CLI arguments (--config, etc.)             # Command-line (highest priority)
```

### File Names and Formats

Primary configuration file names (in order of preference):
- `mcp-config.json` (primary format, aligned with CLLM conventions)
- `Cllmfile.json` (alternative format)
- `Cllmfile.yml` (future support)

### Directory Structure

**Global configuration**:
```bash
~/.cllm/
├── mcp-config.json          # Global MCP server definitions
├── Cllmfile.json            # Global CLLM configuration
└── ...other configs...
```

**Project-specific configuration**:
```bash
project/
├── .cllm/
│   ├── mcp-config.json      # Project-specific servers
│   └── Cllmfile.json        # Project-specific settings
├── .gitignore               # Should include: .cllm/local-config.json
└── ...project files...
```

**Current directory**:
```bash
./mcp-config.json            # Can be checked into version control
./Cllmfile.json              # Can be checked into version control
```

### Configuration Search Algorithm

```python
def find_config_file(name: str = "mcp-config.json") -> Optional[Path]:
    """
    Find configuration file using CLLM precedence.

    Search order (lowest to highest priority):
    1. ~/.cllm/{name}
    2. ./.cllm/{name}
    3. ./{name}

    Returns the highest priority config file found.
    """
    search_paths = [
        Path.home() / ".cllm" / name,           # Global
        Path(".cllm") / name,                   # Project-specific
        Path(name),                             # Current directory
    ]

    # Return highest priority (last found)
    for path in reversed(search_paths):
        if path.exists():
            return path

    return None  # No config found
```

### Environment Variable Support

Configuration can be overridden via environment variables with `CLLM_MCP_` prefix:

```bash
# Override server command
export CLLM_MCP_SERVER_COMMAND="python -m custom_server"

# Override socket path
export CLLM_MCP_SOCKET="/custom/path/mcp.sock"

# Override daemon behavior
export CLLM_MCP_USE_DAEMON="false"
```

Environment variable naming convention:
- Prefix: `CLLM_MCP_`
- Format: `CLLM_MCP_{FEATURE}={value}`
- Examples:
  - `CLLM_MCP_CONFIG=/path/to/config.json`
  - `CLLM_MCP_SOCKET=/custom/socket.sock`
  - `CLLM_MCP_NO_DAEMON=true`
  - `CLLM_MCP_VERBOSE=true`

### CLI Argument Precedence

Command-line arguments always take highest priority:

```bash
# CLI args override all config sources
cllm-mcp --config /explicit/path/config.json list-tools <server>
cllm-mcp --socket /custom/socket.sock daemon status
cllm-mcp --no-daemon call-tool <server> <tool> <json>
```

### Configuration File Format

Standardized JSON schema for `mcp-config.json`:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "uvx",
      "args": ["mcp-server-time"],
      "description": "Time server"
    },
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem", "/home/user/Documents"],
      "description": "Filesystem access"
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

### Migration Path

#### For Existing Users

Current configs will continue to work through a compatibility layer:

1. **Backward Compatibility** (Year 1)
   - Continue supporting old search paths
   - Log deprecation warnings
   - Document migration path

2. **Deprecation Period** (Year 2)
   - Old paths still work but with warnings
   - Provide automated migration tools
   - Update all examples to use new pattern

3. **Removal** (Year 3+)
   - Old search paths no longer supported
   - Users must migrate to new system

#### Migration Commands

```bash
# Automated migration (proposed for future)
cllm-mcp config migrate
# Moves existing configs to appropriate .cllm folders

# Validate configuration
cllm-mcp config validate
# Checks all configuration sources and shows precedence

# Show active configuration
cllm-mcp config show
# Displays which config file is being used and why
```

## Consequences

### Positive

- **Aligned with ecosystem**: Matches CLLM tool ecosystem standards
- **Clear precedence**: Users understand which config is active
- **Flexible configuration**: Global defaults + project overrides
- **CI/CD friendly**: Environment variable support
- **Industry standard**: Similar to Terraform, Docker Compose, Ruby, etc.
- **Better organization**: Separated into `.cllm` folders
- **Version control friendly**: Global vs. local configs can be managed differently
- **Verbose mode**: Can show which config files were searched

### Negative

- **Migration effort**: Existing configs need to be moved
- **User documentation**: New users need to understand precedence
- **Transition period**: Must support both old and new paths
- **Initial confusion**: Users might have multiple config files
- **Backward compatibility**: Need to maintain old behavior temporarily

### Mitigation

- **Clear documentation**: Migrate guide with examples
- **Automated migration**: Tools to help move configs (Phase 2)
- **Graceful deprecation**: Warnings before removal
- **Verbose mode**: `--verbose` shows which config was chosen
- **Config validation**: Detect and warn about multiple configs

## Alternatives Considered

### 1. Keep Current Ad-Hoc Approach
**Pros**: No migration needed, works today
**Cons**: Inconsistent, confusing, not aligned with ecosystem

### 2. Single Configuration Location Only
**Pros**: Simplicity, no precedence confusion
**Cons**: No per-project overrides, forces global config

### 3. Adopt Terraform-style Approach
**Pros**: Well-known pattern
**Cons**: Heavier configuration format, less flexible

### 4. Use Environment Variables Only
**Pros**: Simple for CI/CD, no files needed
**Cons**: Not user-friendly, verbose to set many configs

## Decision Rationale

**Chosen**: CLLM configuration precedence with `.cllm` folder standard

This approach provides:
- Clear alignment with CLLM ecosystem
- Familiar pattern from established tools
- Flexibility for all deployment scenarios
- Path forward for community adoption
- Industry-standard configuration management

## Implementation Plan

### Phase 1: Foundation (Sprint 1-2)
- [ ] Update `config.py` to implement new search algorithm
- [ ] Add `.cllm` folder support
- [ ] Implement environment variable parsing
- [ ] Add verbose mode configuration tracing
- [ ] Update tests for new search order

### Phase 2: Tooling (Sprint 3-4)
- [ ] Create `cllm-mcp config show` command
- [ ] Create `cllm-mcp config migrate` command
- [ ] Add configuration validation enhancements
- [ ] Implement deprecation warnings
- [ ] Create migration guide documentation

### Phase 3: Documentation (Sprint 5)
- [ ] Update README with new config locations
- [ ] Create migration guide
- [ ] Document environment variables
- [ ] Provide example configurations
- [ ] Add troubleshooting guide

### Phase 4: Cleanup (Year 2+)
- [ ] Remove old search paths (with long deprecation)
- [ ] Remove backward compatibility code
- [ ] Archive migration tools

## Configuration Examples

### Global Configuration

```bash
~/.cllm/mcp-config.json
```

```json
{
  "mcpServers": {
    "time": {
      "command": "uvx",
      "args": ["mcp-server-time"],
      "description": "Global time server"
    }
  }
}
```

### Project-Specific Configuration

```bash
./.cllm/mcp-config.json
```

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem", "./data"],
      "description": "Project filesystem access"
    }
  }
}
```

### Usage Examples

```bash
# Uses ~/.cllm/mcp-config.json (global)
cllm-mcp list-tools time

# Uses ./.cllm/mcp-config.json (overrides global)
cllm-mcp list-tools filesystem

# Uses explicit config (highest priority)
cllm-mcp --config /etc/mcp-config.json list-tools custom

# Uses environment variable
export CLLM_MCP_CONFIG=/custom/config.json
cllm-mcp list-tools time

# Show which config is active
cllm-mcp --verbose list-tools time
# Output: Using config: ~/.cllm/mcp-config.json
```

## Testing Strategy

### Unit Tests
- [ ] Configuration file search algorithm
- [ ] Environment variable parsing
- [ ] CLI argument priority validation
- [ ] File format validation
- [ ] Precedence order verification

### Integration Tests
- [ ] Multiple config files present
- [ ] Config file not found (fallback)
- [ ] Mixed environment variables and files
- [ ] CLI args overriding all sources

### Migration Tests
- [ ] Backward compatibility with old paths
- [ ] Deprecation warnings
- [ ] Config migration command

## Monitoring & Observability

### Configuration Tracing
Enable with `--verbose` flag:

```bash
cllm-mcp --verbose list-tools time
# Output:
# [CONFIG] Searching for configuration...
# [CONFIG] Checked: ~/.cllm/mcp-config.json (found)
# [CONFIG] Checked: ./.cllm/mcp-config.json (not found)
# [CONFIG] Using: ~/.cllm/mcp-config.json
# [CONFIG] Servers available: time, filesystem
```

### Metrics
- Configuration source distribution (file vs. env vs. CLI)
- Configuration load times
- Configuration validation errors
- Migration completion rate

## Related ADRs

- **ADR-0003**: Unified Daemon/Client Command Architecture
  - Builds on configuration management from ADR-0003
  - Provides standardized configuration structure

- **ADR-0001**: Adopt Vibe ADR Framework
  - Follows same ADR process and structure

## Questions & Clarifications

**Q: Why use `.cllm` folder instead of `.mcp`?**
A: Aligns with CLLM ecosystem conventions and tools. The `.cllm` folder is recognized across CLLM-based tools.

**Q: What about YAML configuration?**
A: JSON is the primary format for MVP. YAML support can be added in Phase 3 if needed.

**Q: How long is the deprecation period?**
A: Minimum 2 years. Old paths supported with warnings in Year 1, removal in Year 3.

**Q: Can I have both global and project configs active?**
A: Yes! Project config files are merged with global config, with project-specific values taking precedence.

**Q: What if multiple config files exist?**
A: The highest priority file is used. Use `cllm-mcp config show` to see which is active.

## References

- **CLLM Configuration**: https://github.com/o3-cloud/cllm#configuration-precedence
- **Terraform Configuration**: https://www.terraform.io/language/settings/backends/configuration#file-credentials
- **Docker Compose Configuration**: https://docs.docker.com/compose/compose-file/compose-file-v3/
- **XDG Base Directory Specification**: https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html

---

## Timeline

- **Week 1-2**: Design and review
- **Week 3-4**: Phase 1 implementation
- **Week 5-6**: Phase 2 tooling
- **Week 7**: Phase 3 documentation
- **Ongoing**: Backward compatibility and deprecation

## Sign-Off

**Proposed by**: Claude Code
**Date**: November 12, 2025
**Status**: Proposed (awaiting team review and approval)

## Approval

- [ ] Reviewed by technical lead
- [ ] Approved by project maintainer
- [ ] Community feedback incorporated
