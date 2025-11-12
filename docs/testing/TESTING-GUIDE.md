# Testing Guide for cllm-mcp

This guide explains how to run the test suite for the cllm-mcp project, specifically for ADR-0003 (Unified Daemon/Client Command).

## Quick Start

### Install Test Dependencies

```bash
# Install pytest and testing tools
uv sync

# Or manually
uv pip install pytest pytest-mock
```

### Run All Tests

```bash
# Run entire test suite with verbose output
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ -v --cov=cllm_mcp --cov-report=html
```

## Test Organization

Tests are organized by type:

### Unit Tests
Fast, isolated tests that don't require external processes or files.

```bash
# Run all unit tests
uv run pytest tests/unit/ -v

# Run specific test file
uv run pytest tests/unit/test_main_dispatcher.py -v

# Run specific test
uv run pytest tests/unit/test_main_dispatcher.py::TestMainDispatcher::test_dispatch_list_tools_command -v
```

**Test Files:**
- `test_main_dispatcher.py` - Command routing and dispatch
- `test_daemon_detection.py` - Smart daemon detection logic
- `test_config_management.py` - Configuration loading and validation
- `test_cli_parser.py` - Command-line argument parsing
- (Existing) `test_mcp_client.py` - MCPClient class
- (Existing) `test_mcp_daemon.py` - MCPDaemon class

### Integration Tests
Slower tests that may spawn processes, use network, or filesystem.

```bash
# Run all integration tests
uv run pytest tests/integration/ -v

# Run with extended timeout (some tests are slow)
uv run pytest tests/integration/ -v --timeout=10

# Run only fallback tests
uv run pytest tests/integration/test_fallback_behavior.py -v

# Run only daemon tests
uv run pytest -m daemon -v
```

**Test Files:**
- `test_daemon_mode_integration.py` - End-to-end daemon functionality
- `test_direct_mode_integration.py` - Direct mode without daemon
- `test_fallback_behavior.py` - Transparent daemon->direct fallback
- `test_socket_communication.py` - Unix socket communication
- `test_config_loading.py` - Config file integration

## Running Tests by Category

### By Test Type

```bash
# Run only unit tests (fast)
uv run pytest -m unit -v

# Run only integration tests (slower)
uv run pytest -m integration -v

# Run both unit and integration
uv run pytest -v

# Skip slow tests
uv run pytest -m "not slow" -v
```

### By Feature

```bash
# Run all daemon-related tests
uv run pytest -m daemon -v

# Run all socket-related tests
uv run pytest -m socket -v

# Run all unit tests except socket tests
uv run pytest tests/unit/ -m "not socket" -v
```

### By Performance

```bash
# Run only fast tests (good for development)
uv run pytest -m "not slow" -v --durations=5

# Run and show slowest tests
uv run pytest tests/ -v --durations=10

# Run with timeout (fail if test takes too long)
uv run pytest tests/ --timeout=5
```

## Coverage Analysis

### Generate Coverage Report

```bash
# Run tests with coverage
uv run pytest tests/ --cov=cllm_mcp --cov-report=html

# View HTML report
open htmlcov/index.html

# Show coverage in terminal
uv run pytest tests/ --cov=cllm_mcp --cov-report=term-missing
```

### Coverage Targets

According to ADR-0003 testing strategy:
- Overall: 85% minimum
- New code (main.py, config.py): 90%
- Modified code (mcp_cli.py, mcp_daemon.py): 85%
- Critical paths: 100% (daemon detection, fallback, dispatch)

### Coverage by Module

```bash
# Show coverage for specific modules
uv run pytest tests/unit/test_main_dispatcher.py --cov=cllm_mcp.main --cov-report=term-missing
```

## Development Workflow

### Test-Driven Development

```bash
# 1. Write a test
# 2. Run tests (should fail)
uv run pytest tests/unit/test_main_dispatcher.py::TestMainDispatcher::test_dispatch_list_tools_command -v

# 3. Implement feature
# 4. Run tests again (should pass)
uv run pytest tests/unit/test_main_dispatcher.py::TestMainDispatcher::test_dispatch_list_tools_command -v

# 5. Run full test suite to check for regressions
uv run pytest tests/ -v
```

### Continuous Testing During Development

```bash
# Watch mode (if pytest-watch installed)
pip install pytest-watch
ptw tests/unit/

# Or simply re-run tests frequently
uv run pytest tests/ --maxfail=1 -x  # Stop on first failure
```

### Debugging Test Failures

```bash
# Show print statements
uv run pytest tests/unit/test_main_dispatcher.py -v -s

# Show full tracebacks
uv run pytest tests/unit/test_main_dispatcher.py -v --tb=long

# Drop into debugger on failure
uv run pytest tests/unit/test_main_dispatcher.py -v --pdb

# Don't capture output
uv run pytest tests/ -v --capture=no
```

## Common Commands

### Quick Unit Test Run
```bash
uv run pytest tests/unit/ -v --tb=short
```

### Full Test Suite with Coverage
```bash
uv run pytest tests/ -v --cov=cllm_mcp --cov-report=term-missing
```

### Test Specific Component
```bash
# Test daemon detection
uv run pytest tests/unit/test_daemon_detection.py -v

# Test config management
uv run pytest tests/unit/test_config_management.py -v

# Test dispatcher
uv run pytest tests/unit/test_main_dispatcher.py -v
```

### Find and Run Tests
```bash
# List all tests without running them
uv run pytest tests/ --collect-only -q

# Find tests matching pattern
uv run pytest tests/ -k "daemon" --collect-only

# Run tests matching pattern
uv run pytest tests/ -k "daemon" -v
```

### Parallel Test Execution
```bash
# Install pytest-xdist
uv pip install pytest-xdist

# Run tests in parallel (default: use all cores)
uv run pytest tests/ -n auto -v

# Run with specific number of workers
uv run pytest tests/ -n 4 -v
```

## Fixtures and Mocks

### Using Test Fixtures

Fixtures are defined in `tests/conftest.py` and automatically available:

```python
def test_something(temp_socket_path):
    """temp_socket_path provides a unique socket path"""
    assert temp_socket_path.startswith("/tmp/test-mcp-")

def test_with_config(temp_config_file):
    """temp_config_file provides a temporary config file"""
    # config_file is a Path object
    config = json.loads(config_file.read_text())

def test_with_mock_server(mock_mcp_server):
    """mock_mcp_server provides a MockMCPServer instance"""
    tools = mock_mcp_server.list_tools()
```

### Available Fixtures

- `temp_socket_path` - Temporary Unix socket path for testing
- `temp_config_file` - Temporary config file with sample servers
- `isolated_temp_dir` - Temporary directory as working directory
- `mock_mcp_server` - Mock MCP server instance
- `mock_server_with_crash` - Mock server that crashes on specific tool
- `mock_server_custom_tools` - Mock server with custom tools
- `clean_env` - Clean environment without MCP variables
- `mock_daemon_socket` - Mocked daemon socket
- `mock_subprocess` - Mocked subprocess for testing

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

### GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v2
      - run: uv sync
      - run: uv run pytest tests/ -v --cov=cllm_mcp
      - uses: codecov/codecov-action@v3
```

### Local CI Check

Run this before committing:

```bash
# Run all tests with coverage
uv run pytest tests/ -v --cov=cllm_mcp --cov-report=xml

# Check coverage meets minimum
uv run pytest tests/ --cov=cllm_mcp --cov-fail-under=85
```

## Troubleshooting

### Tests fail with "module not found"

```bash
# Ensure you're in the right directory
cd /path/to/cllm-mcp

# Ensure tests can import modules
export PYTHONPATH="${PYTHONPATH}:."

# Run tests
uv run pytest tests/
```

### Socket-related tests fail

```bash
# Clean up any old socket files
rm -f /tmp/test-mcp-*.sock

# Run socket tests
uv run pytest -m socket -v
```

### Daemon tests hang or timeout

```bash
# Run with timeout
uv run pytest tests/ --timeout=10

# Run only unit tests (skip slow integration tests)
uv run pytest tests/unit/ -v
```

### Coverage report shows wrong numbers

```bash
# Clear coverage cache
rm -rf .coverage htmlcov/

# Regenerate coverage
uv run pytest tests/ --cov=cllm_mcp --cov-report=html --cov-report=term-missing
```

## Test Data

Test data and constants are in `tests/conftest.py`:

- `SAMPLE_TOOLS` - Sample MCP tool definitions
- `SAMPLE_TOOL_RESPONSE` - Sample tool response
- `SAMPLE_CONFIG` - Sample configuration object
- `MOCK_MCP_SERVER` - Mock server instance

## Performance Benchmarking

### Compare daemon vs direct mode

```bash
# Run performance comparison test
uv run pytest tests/integration/test_daemon_mode_integration.py::TestDaemonPerformance -v

# Show timing information
uv run pytest tests/ -v --durations=5
```

### Profiling Tests

```bash
# Profile a specific test
uv run pytest tests/unit/test_daemon_detection.py::TestDaemonDetection::test_daemon_detected_when_socket_exists -v --profile
```

## Writing New Tests

### Test File Template

```python
"""
Unit tests for [component].

Tests for [feature description].
"""

import pytest

@pytest.mark.unit
class TestComponentName:
    """Tests for [component]."""

    def test_specific_behavior(self):
        """Test that [behavior] works correctly."""
        # Arrange

        # Act

        # Assert
        pass

    def test_error_handling(self):
        """Test that [error] is handled correctly."""
        pass
```

### Using Fixtures in Tests

```python
def test_with_config_file(temp_config_file):
    """Test using temporary config file."""
    # temp_config_file is a pathlib.Path
    config = json.loads(temp_config_file.read_text())
    assert "mcpServers" in config

def test_with_socket_path(temp_socket_path):
    """Test using temporary socket path."""
    # temp_socket_path is a str
    assert temp_socket_path.startswith("/tmp/test-mcp-")
```

## Documentation References

- [pytest documentation](https://docs.pytest.org/)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [pytest markers](https://docs.pytest.org/en/stable/mark.html)
- [pytest coverage plugin](https://pytest-cov.readthedocs.io/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)

## Questions?

For questions about testing or to report test issues, please check:

1. This guide for common commands
2. The ADR-0003 testing strategy document
3. The test docstrings for specific test details
4. GitHub issues for known problems
