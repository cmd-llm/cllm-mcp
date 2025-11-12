# Testing Documentation for ADR-0003

This directory contains comprehensive testing documentation and strategy for ADR-0003: Unified Daemon/Client Command Architecture.

## Documents

### 1. ADR-0003-testing-strategy.md
**Comprehensive testing strategy document**

This is the main testing specification document that defines:
- Testing framework and tools (pytest)
- Test structure and organization
- Complete test categories and coverage goals
- Mock and fixture strategies
- Acceptance criteria for ADR-0003
- Test execution strategies
- CI/CD integration
- Coverage targets and critical paths

**Use this for:**
- Understanding the complete testing approach
- Test case design and specification
- Coverage requirements
- Acceptance criteria validation

### 2. TESTING-GUIDE.md
**Practical guide for running tests**

Quick reference guide for developers explaining how to:
- Install test dependencies
- Run all tests or specific subsets
- Organize tests by category
- Generate coverage reports
- Use fixtures and mocks
- Troubleshoot common issues
- Write new tests

**Use this for:**
- Running tests during development
- Understanding test organization
- Debugging test failures
- Learning available fixtures
- CI/CD test execution

## Test Files Created

### Unit Tests (`tests/unit/`)
Fast, isolated tests with no external dependencies:

- `test_main_dispatcher.py` - Command routing and dispatch logic
- `test_daemon_detection.py` - Smart daemon detection
- `test_config_management.py` - Configuration loading and validation
- (Future) `test_cli_parser.py` - Argument parsing
- (Future) `test_mcp_client.py` - MCPClient class
- (Future) `test_mcp_daemon.py` - MCPDaemon class

### Integration Tests (`tests/integration/`)
Slower tests that interact with processes, files, or network:

- `test_daemon_mode_integration.py` - End-to-end daemon functionality
- (Future) `test_direct_mode_integration.py` - Direct mode operation
- `test_fallback_behavior.py` - Transparent daemon-to-direct fallback
- (Future) `test_socket_communication.py` - Unix socket IPC
- (Future) `test_config_loading.py` - Configuration integration

### Shared Test Infrastructure (`tests/`)
- `conftest.py` - Pytest configuration, fixtures, and mocks
- `__init__.py` - Python package marker
- `unit/__init__.py`
- `integration/__init__.py`

## Quick Start

### Run All Tests
```bash
cd /Users/owenzanzal/Projects/cllm-mcp
uv sync
uv run pytest tests/ -v
```

### Run Unit Tests Only (Fast)
```bash
uv run pytest tests/unit/ -v
```

### Run with Coverage Report
```bash
uv run pytest tests/ --cov=cllm_mcp --cov-report=html
open htmlcov/index.html
```

### Run Specific Test
```bash
uv run pytest tests/unit/test_daemon_detection.py::TestDaemonDetection::test_daemon_detected_when_socket_exists -v
```

## Test Coverage Goals

According to ADR-0003 testing strategy:

| Component | Target | Status |
|-----------|--------|--------|
| mcp_cli.py | 85% | Pending implementation |
| mcp_daemon.py | 85% | Pending implementation |
| main.py (new) | 90% | Test cases defined |
| config.py (new) | 85% | Test cases defined |
| Overall | 85% | In progress |

**Critical Paths (100% coverage):**
- Command dispatch logic
- Daemon detection logic
- Fallback behavior
- Error handling paths

## Test Organization

Tests are organized by:

### By Type
- **Unit tests** (`-m unit`) - Fast, isolated
- **Integration tests** (`-m integration`) - Require processes
- **Slow tests** (Skip with `-m "not slow"`) - Long running

### By Feature
- **Daemon tests** (`-m daemon`) - Daemon functionality
- **Socket tests** (`-m socket`) - Unix socket operations

### By Component
- `test_main_dispatcher.py` - Command dispatch
- `test_daemon_detection.py` - Daemon detection
- `test_config_management.py` - Configuration
- `test_fallback_behavior.py` - Fallback logic

## Fixtures Available

Defined in `tests/conftest.py`:

- `temp_socket_path` - Temporary socket path
- `temp_config_file` - Temporary config file with sample servers
- `isolated_temp_dir` - Isolated temporary directory
- `mock_mcp_server` - Mock MCP server instance
- `mock_server_with_crash` - Mock server that crashes on specific tool
- `mock_server_custom_tools` - Mock server with custom tools
- `clean_env` - Clean environment without MCP variables
- `mock_daemon_socket` - Mocked daemon socket
- `mock_subprocess` - Mocked subprocess

## CI/CD Integration

### GitHub Actions Workflow
File: `.github/workflows/tests.yml`

Runs:
- Unit tests on all Python versions (3.7-3.12)
- Integration tests with timeout
- Coverage report generation
- Codecov upload

Triggers on:
- Push to main/develop
- Pull requests to main/develop

### Local CI Check
Run before committing:
```bash
uv run pytest tests/ -v --cov=cllm_mcp --cov-fail-under=80
```

## Implementation Status

### ✅ Completed
- [x] ADR-0003 main architecture document
- [x] Comprehensive testing strategy document
- [x] Test file structure and organization
- [x] Unit test specifications (3 files with 80+ test cases)
- [x] Integration test specifications (2 files with 60+ test cases)
- [x] Shared fixtures and mock utilities in conftest.py
- [x] pytest configuration in pyproject.toml
- [x] GitHub Actions CI/CD workflow
- [x] Testing guide documentation

### 🔄 In Progress
- Unit test implementation (test case stubs created)
- Integration test implementation (test case stubs created)

### 📋 Next Steps
1. Implement actual test code (replace pass statements)
2. Implement main.py dispatcher
3. Implement daemon_detection.py logic
4. Implement config.py management
5. Run full test suite and achieve coverage targets
6. Create shell completion for cllm-mcp command

## Test Cases Summary

### Unit Tests
- **35 test cases** in test_main_dispatcher.py
- **25 test cases** in test_daemon_detection.py
- **35 test cases** in test_config_management.py
- **Total: 95+ unit test cases**

### Integration Tests
- **25 test cases** in test_fallback_behavior.py
- **30 test cases** in test_daemon_mode_integration.py
- **Total: 55+ integration test cases**

### Total Test Cases: 150+

## Key Features Tested

### Command Dispatcher
- Command routing
- Global options handling
- Argument passing
- Error handling
- Help text

### Daemon Detection
- Socket existence checking
- Daemon responsiveness
- Timeout handling
- Fallback behavior
- Configuration

### Configuration Management
- File loading
- Validation
- Server listing
- Environment variables
- Error handling

### Daemon Mode
- Server startup
- Tool execution
- Performance
- Error handling
- Stability

### Fallback Behavior
- Transparent fallback
- Error recovery
- Performance transparency
- Socket handling

## Acceptance Criteria

All tests in this suite must pass before ADR-0003 is considered complete:

1. ✅ All unit tests pass
2. ✅ All integration tests pass
3. ✅ Coverage >= 85% overall
4. ✅ Critical paths have 100% coverage
5. ✅ CI/CD pipeline passes
6. ✅ No performance regressions
7. ✅ All acceptance criteria in testing strategy met

## Running Tests in Different Environments

### Local Development
```bash
uv run pytest tests/unit/ -v --tb=short  # Fast iteration
```

### Before Committing
```bash
uv run pytest tests/ -v --cov=cllm_mcp --cov-fail-under=80
```

### Full CI Check
```bash
uv run pytest tests/ -v --cov=cllm_mcp --cov-report=html
python -m pytest tests/ --cov=cllm_mcp --cov-fail-under=85
```

### Debugging
```bash
uv run pytest tests/unit/test_daemon_detection.py -v -s --pdb
```

## Related Documents

- [ADR-0003: Unified Daemon/Client Command](../decisions/0003-unified-daemon-client-command.md)
- [ADR-0001: Vibe ADR Framework](../decisions/0001-adopt-vibe-adr.md)
- [ADR-0002: Adopt uv Package Manager](../decisions/0002-adopt-uv-package-manager.md)
- [Contributing Guide](../../CONTRIBUTING.md)
- [README](../../README.md)

## Support and Questions

For questions about testing:

1. Check the [TESTING-GUIDE.md](./TESTING-GUIDE.md) for how-to questions
2. Check [ADR-0003-testing-strategy.md](./ADR-0003-testing-strategy.md) for design questions
3. Review test docstrings in test files for specific test details
4. Check test conftest.py for fixture documentation
5. Open a GitHub issue for bugs or feature requests
