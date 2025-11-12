# ADR-0003 Test Suite Overview

**Status**: Implementation-Ready
**Date**: November 12, 2025
**Total Test Cases**: 203+ (organized and discoverable)
**Coverage Target**: 85% overall, 100% critical paths

---

## Executive Summary

This document provides an overview of the comprehensive test suite designed for ADR-0003 (Unified Daemon/Client Command Architecture). The test suite includes:

- **120 unit tests** covering individual components
- **83 integration tests** covering system behavior and workflows
- **Complete test infrastructure** with fixtures, mocks, and utilities
- **CI/CD integration** with multi-version Python testing and coverage tracking

All test cases are organized by functionality area and marked with appropriate pytest markers for easy discovery and execution.

---

## Test Organization

```
tests/
├── __init__.py                          # Package marker
├── conftest.py                          # Shared fixtures and configuration
├── unit/
│   ├── __init__.py
│   ├── test_main_dispatcher.py         # 45 test cases
│   ├── test_daemon_detection.py        # 40 test cases
│   └── test_config_management.py       # 35 test cases
└── integration/
    ├── __init__.py
    ├── test_daemon_mode_integration.py  # 35 test cases
    ├── test_direct_mode_integration.py  # 40 test cases
    └── test_fallback_behavior.py        # 30 test cases
```

---

## Test Categories

### Unit Tests (120 cases)

#### 1. Main Dispatcher (45 cases)

**File**: `tests/unit/test_main_dispatcher.py`

Tests for the unified command dispatcher (`cllm_mcp/main.py`):

- Command routing (list-tools, call-tool, daemon, config)
- Global options (--config, --socket, --no-daemon, --verbose, --daemon-timeout)
- Help text and version information
- Error handling (invalid commands, missing arguments)
- Argument parsing and validation

**Key test areas**:

- ✅ Routes all commands to correct handlers
- ✅ Passes global options to subcommands
- ✅ Provides helpful error messages
- ✅ Handles parsing errors gracefully

#### 2. Daemon Detection (40 cases)

**File**: `tests/unit/test_daemon_detection.py`

Tests for daemon availability detection (`cllm_mcp/daemon_utils.py`):

- Socket existence checking
- Connection success/failure handling
- Timeout behavior
- Fallback to direct mode
- Verbose logging

**Key test areas**:

- ✅ Detects responsive daemon
- ✅ Falls back when daemon unavailable
- ✅ Respects --no-daemon flag
- ✅ Respects timeout configuration
- ✅ Handles edge cases (stale socket, permission denied)

#### 3. Configuration Management (35 cases)

**File**: `tests/unit/test_config_management.py`

Tests for config file handling (`cllm_mcp/config.py`):

- Loading from standard locations
- Validation and error detection
- Server discovery and name resolution
- Config merging (file, environment, CLI)
- Edge cases (empty config, unicode, special characters)

**Key test areas**:

- ✅ Loads config from multiple locations
- ✅ Validates configuration structure
- ✅ Resolves server names to commands
- ✅ Handles missing or invalid configs
- ✅ Provides helpful validation messages

---

### Integration Tests (83 cases)

#### 4. Daemon Mode Integration (35 cases)

**File**: `tests/integration/test_daemon_mode_integration.py`

Tests for daemon-based tool execution:

- Daemon startup and socket creation
- Single and multiple tool calls
- Server process caching
- Performance measurement
- Error handling
- Concurrent requests
- Daemon status command
- Configuration interaction
- Shutdown behavior
- Health and stability

**Key test areas**:

- ✅ Daemon handles tool calls correctly
- ✅ Server processes are cached
- ✅ Performance improvement verified
- ✅ Status command shows accurate info
- ✅ Graceful shutdown and cleanup

#### 5. Direct Mode Integration (40 cases)

**File**: `tests/integration/test_direct_mode_integration.py`

Tests for direct mode (without daemon):

- Process spawning and server execution
- Tool execution and result handling
- --no-daemon flag behavior
- Tool execution variations (JSON, unicode, timeout, large output)
- list-tools command
- Backward compatibility with mcp-cli
- Error scenarios

**Key test areas**:

- ✅ Direct mode works without daemon
- ✅ --no-daemon flag forces direct mode
- ✅ Spawns and cleans up server processes
- ✅ Handles tool errors gracefully
- ✅ Compatible with existing mcp-cli usage

#### 6. Fallback Behavior (30 cases)

**File**: `tests/integration/test_fallback_behavior.py`

Tests for transparent fallback mechanism:

- Fallback when socket unavailable
- Fallback when socket unresponsive
- Fallback during daemon shutdown
- Performance during fallback
- Recovery when daemon restarts
- Error handling during fallback
- Configuration integration
- Feature compatibility during fallback

**Key test areas**:

- ✅ Transparent fallback works seamlessly
- ✅ Fallback preserves command arguments
- ✅ Returns same result as direct mode
- ✅ Silent by default, verbose when requested
- ✅ Detects daemon recovery automatically

---

## Test Infrastructure

### Fixtures (Shared Test Utilities)

**File**: `tests/conftest.py`

Provides 15+ pytest fixtures for testing:

#### Temporary Files

- `temp_socket_dir`: Temporary directory for socket files
- `socket_path`: Path for test socket
- `temp_config_dir`: Temporary directory for config files
- `config_file`: Sample config file

#### Mock Objects

- `mock_mcp_server`: Mock MCP server instance
- `mock_socket`: Mocked socket
- `mock_subprocess`: Mocked process spawning
- `mock_daemon_process`: Mocked daemon process

#### Environment

- `clean_env`: Clean environment without MCP variables
- `isolated_filesystem`: Isolated working directory

#### Daemon Setup

- `daemon_socket`: Real Unix socket for testing
- `running_daemon`: Running daemon process

#### Test Data

- `mock_args`: Mock argparse Namespace
- `cli_args`: Mock CLI arguments
- `daemon_args`: Mock daemon arguments
- `config_args`: Mock config arguments
- `sample_tools_response`: Sample tools JSON
- `sample_config`: Sample config JSON
- `sample_daemon_status`: Sample status JSON

### Pytest Configuration

**File**: `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: Unit tests - fast, isolated",
    "integration: Integration tests - may need processes",
    "slow: Tests that take longer to run",
    "socket: Tests requiring Unix socket",
    "daemon: Tests requiring daemon",
]
```

### CI/CD Pipeline

**File**: `.github/workflows/tests.yml`

- Tests across Python 3.7-3.12
- Unit tests fast execution
- Integration tests with timeout
- Coverage reporting (target: 85%)
- Codecov integration

---

## Running the Tests

### Quick Start

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest tests/ -v

# Run only unit tests (fast)
uv run pytest tests/unit/ -v

# Run only integration tests
uv run pytest tests/integration/ -v
```

### By Marker

```bash
# Run daemon-specific tests
uv run pytest -m daemon -v

# Run socket-based tests
uv run pytest -m socket -v

# Run slow tests
uv run pytest -m slow -v
```

### With Coverage

```bash
# Generate coverage report
uv run pytest tests/ --cov=cllm_mcp --cov-report=html

# Check coverage meets minimum
uv run pytest tests/ --cov=cllm_mcp --cov-fail-under=85
```

### Specific Test File

```bash
uv run pytest tests/unit/test_main_dispatcher.py -v
uv run pytest tests/integration/test_daemon_mode_integration.py -v
```

---

## Test Statistics

### By Category

| Category          | File                            | Test Cases | Type        |
| ----------------- | ------------------------------- | ---------- | ----------- |
| Main Dispatcher   | test_main_dispatcher.py         | 45         | Unit        |
| Daemon Detection  | test_daemon_detection.py        | 40         | Unit        |
| Config Management | test_config_management.py       | 35         | Unit        |
| Daemon Mode       | test_daemon_mode_integration.py | 35         | Integration |
| Direct Mode       | test_direct_mode_integration.py | 40         | Integration |
| Fallback          | test_fallback_behavior.py       | 30         | Integration |
| **TOTAL**         |                                 | **225**    |             |

### By Type

- **Unit Tests**: 120 (fast, isolated)
- **Integration Tests**: 105 (system behavior)
- **Total**: 225 test cases

### Expected Execution Time

- Unit tests: ~10-15 seconds
- Integration tests: ~30-60 seconds
- Full suite: ~1-2 minutes

---

## Coverage Goals

### Target: 85% overall, 100% critical paths

#### High Priority (100% coverage required)

- Daemon detection logic
- Fallback behavior
- Error handling
- Critical path execution

#### Medium Priority (90%+ coverage)

- Command routing
- Config loading and validation
- Socket communication
- Process management

#### Standard Priority (80%+ coverage)

- Verbose logging
- Status reporting
- Help text generation

---

## Test Execution Strategy

### Development Workflow

1. **Before committing**: Run unit tests

   ```bash
   uv run pytest tests/unit/ -v
   ```

2. **Before PR**: Run full test suite

   ```bash
   uv run pytest tests/ -v --cov=cllm_mcp
   ```

3. **CI/CD**: Automated on push/PR
   - Tests Python 3.7-3.12
   - Checks coverage minimum
   - Reports to Codecov

### Debugging Failed Tests

1. Run specific test with verbose output:

   ```bash
   uv run pytest tests/unit/test_main_dispatcher.py::TestMainDispatcher::test_dispatcher_routes_list_tools_command -vv
   ```

2. Show print statements:

   ```bash
   uv run pytest tests/ -v -s
   ```

3. Drop into debugger on failure:
   ```bash
   uv run pytest tests/ --pdb
   ```

---

## Test Writing Guide

### Template for New Tests

```python
@pytest.mark.unit  # or integration, slow, socket, daemon
def test_specific_behavior(self):
    """Clear description of what is being tested."""
    # Arrange: Set up test data and mocks
    mock_obj = MagicMock()

    # Act: Call the function being tested
    result = function_under_test(mock_obj)

    # Assert: Verify the result
    assert result == expected_value
```

### Best Practices

1. **One assertion per test** (generally)
2. **Clear naming**: `test_<unit>_<scenario>_<expected_result>`
3. **Use fixtures** instead of setup/teardown
4. **Mock external dependencies**
5. **Test both success and failure cases**
6. **Include edge cases**

---

## Next Steps

### Phase 1: Implementation

- [ ] Implement failing tests in order of priority
- [ ] Achieve 85% coverage
- [ ] Verify all critical paths covered

### Phase 2: Continuous Integration

- [ ] Run tests on every commit
- [ ] Track coverage trends
- [ ] Maintain or improve coverage

### Phase 3: Maintenance

- [ ] Update tests with code changes
- [ ] Add tests for bugs discovered
- [ ] Review and refactor tests periodically

---

## References

- **ADR-0003**: `docs/decisions/0003-unified-daemon-client-command.md`
- **Test Strategy**: `docs/testing/ADR-0003-testing-strategy.md`
- **Testing Guide**: `docs/testing/TESTING-GUIDE.md`
- **pytest Documentation**: https://docs.pytest.org/

---

## Questions & Troubleshooting

**Q: How do I run just the daemon tests?**
A: `uv run pytest -m daemon -v`

**Q: Tests are hanging, what do I do?**
A: Press Ctrl+C to interrupt. Check for infinite loops or mocked timeouts.

**Q: How do I debug a failing test?**
A: Run with `pytest --pdb` to drop into debugger, or `pytest -s` to see print output.

**Q: Can I run tests in parallel?**
A: Yes, install pytest-xdist: `uv pip install pytest-xdist` then `pytest -n auto`

---

**Last Updated**: November 12, 2025
**Status**: Ready for Implementation
