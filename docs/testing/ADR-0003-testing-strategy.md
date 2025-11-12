# ADR-0003 Testing Strategy and Test Plan

## Overview

This document defines the comprehensive testing strategy for ADR-0003 (Unified Daemon/Client Command Architecture). It covers unit tests, integration tests, and acceptance criteria for the new `cllm-mcp` unified command.

## Testing Framework

- **Framework**: pytest (Python standard testing framework)
- **Mocking**: unittest.mock (Python standard library)
- **Fixtures**: pytest fixtures with conftest.py
- **Coverage Target**: Minimum 80% for new code
- **Dependencies**: None (uses Python standard library only)

## Test Structure

```
tests/
├── conftest.py                           # Shared fixtures and configuration
├── __init__.py
├── unit/
│   ├── test_main_dispatcher.py           # Unified command dispatch logic
│   ├── test_daemon_detection.py          # Smart daemon detection
│   ├── test_mcp_client.py                # MCPClient class (existing logic)
│   ├── test_mcp_daemon.py                # MCPDaemon class (existing logic)
│   ├── test_config_management.py         # Config subcommand logic
│   └── test_cli_parser.py                # Argument parsing
├── integration/
│   ├── test_daemon_mode_integration.py   # Daemon-based tool execution
│   ├── test_direct_mode_integration.py   # Direct-based tool execution
│   ├── test_fallback_behavior.py         # Daemon fallback to direct
│   ├── test_socket_communication.py      # Unix socket IPC
│   └── test_config_loading.py            # Configuration file loading
└── fixtures/
    ├── mock_servers.py                   # Mock MCP servers for testing
    ├── test_data.py                      # Test data and constants
    └── socket_helpers.py                 # Unix socket testing utilities
```

## Test Categories and Coverage

### 1. Unit Tests: Command Dispatcher (test_main_dispatcher.py)

**Test Coverage**: Command routing and dispatch logic

```python
# Tests for unified command dispatcher
def test_dispatch_list_tools_command()
def test_dispatch_call_tool_command()
def test_dispatch_interactive_command()
def test_dispatch_daemon_start_command()
def test_dispatch_daemon_status_command()
def test_dispatch_daemon_stop_command()
def test_dispatch_daemon_restart_command()
def test_dispatch_config_list_command()
def test_dispatch_config_validate_command()
def test_unknown_command_returns_error()
def test_dispatch_with_global_options()
def test_help_text_displays_all_commands()
```

**Expected**: All commands correctly routed to handlers with arguments preserved

### 2. Unit Tests: Daemon Detection (test_daemon_detection.py)

**Test Coverage**: Smart daemon availability detection

```python
# Tests for daemon detection logic
def test_daemon_detected_when_socket_exists()
def test_daemon_not_detected_when_socket_missing()
def test_daemon_not_detected_when_unresponsive()
def test_daemon_detection_timeout_respected()
def test_no_daemon_flag_forces_direct_mode()
def test_daemon_detection_with_custom_socket_path()
def test_daemon_detection_handles_permission_errors()
def test_daemon_detection_handles_connection_refused()
def test_fallback_to_direct_on_detection_failure()
def test_verbose_logging_shows_which_mode_used()
```

**Expected**: Daemon correctly detected when running, proper fallback when unavailable

### 3. Unit Tests: Client Mode (test_mcp_client.py)

**Test Coverage**: Existing MCPClient class with new mode awareness

```python
# Tests for MCPClient class
def test_client_initialization_with_command()
def test_client_start_subprocess()
def test_client_stop_subprocess()
def test_client_list_tools_from_running_server()
def test_client_call_tool_with_arguments()
def test_client_handles_invalid_json_response()
def test_client_handles_subprocess_timeout()
def test_client_handles_subprocess_crash()
def test_client_json_rpc_message_format()
def test_client_handles_multiple_sequential_calls()
def test_client_cleanup_on_stop()
```

**Expected**: MCPClient functions correctly with existing behavior unchanged

### 4. Unit Tests: Daemon Mode (test_mcp_daemon.py)

**Test Coverage**: Existing MCPDaemon class with new coordination

```python
# Tests for MCPDaemon class
def test_daemon_initialization()
def test_daemon_socket_creation()
def test_daemon_start_server()
def test_daemon_call_tool_on_cached_server()
def test_daemon_list_tools_on_cached_server()
def test_daemon_stop_server()
def test_daemon_handles_crashed_server()
def test_daemon_thread_safe_operations()
def test_daemon_concurrent_requests()
def test_daemon_timeout_enforcement()
def test_daemon_signal_handling_sigint()
def test_daemon_signal_handling_sigterm()
def test_daemon_cleanup_on_stop()
```

**Expected**: MCPDaemon maintains existing behavior with thread safety

### 5. Unit Tests: Configuration Management (test_config_management.py)

**Test Coverage**: New config subcommand logic

```python
# Tests for configuration management
def test_config_load_valid_json()
def test_config_load_invalid_json_returns_error()
def test_config_list_shows_all_servers()
def test_config_list_with_descriptions()
def test_config_validate_correct_format()
def test_config_validate_detects_missing_command()
def test_config_validate_detects_invalid_paths()
def test_config_validate_checks_executable_permissions()
def test_config_with_environment_variables()
def test_config_with_custom_file_path()
def test_config_missing_file_returns_error()
```

**Expected**: Configuration files correctly parsed and validated

### 6. Unit Tests: CLI Parser (test_cli_parser.py)

**Test Coverage**: Argument parsing and validation

```python
# Tests for argument parser
def test_parser_accepts_list_tools_command()
def test_parser_accepts_call_tool_command()
def test_parser_accepts_daemon_subcommands()
def test_parser_accepts_config_subcommands()
def test_parser_with_global_socket_option()
def test_parser_with_global_config_option()
def test_parser_with_no_daemon_flag()
def test_parser_with_daemon_timeout()
def test_parser_validates_required_arguments()
def test_parser_shows_help_text()
def test_parser_invalid_command_returns_error()
```

**Expected**: All valid arguments accepted, invalid arguments rejected

### 7. Integration Tests: Daemon Mode (test_daemon_mode_integration.py)

**Test Coverage**: End-to-end daemon mode operation

```python
# Integration tests for daemon mode
def test_list_tools_via_daemon()
def test_call_tool_via_daemon()
def test_multiple_servers_in_daemon()
def test_daemon_performance_improvement_over_direct()
def test_daemon_caching_behavior()
def test_daemon_server_restart_on_crash()
def test_daemon_handles_tool_errors_gracefully()
def test_daemon_timeout_on_slow_tool()
def test_concurrent_tool_calls_via_daemon()
def test_daemon_status_accuracy()
```

**Expected**: Daemon mode provides 5-10x performance improvement for sequential calls

### 8. Integration Tests: Direct Mode (test_direct_mode_integration.py)

**Test Coverage**: End-to-end direct mode operation

```python
# Integration tests for direct mode
def test_list_tools_direct_mode()
def test_call_tool_direct_mode()
def test_multiple_servers_in_direct_mode()
def test_direct_mode_independent_processes()
def test_direct_mode_no_shared_state()
def test_direct_mode_cleanup()
def test_interactive_mode_basic_commands()
def test_error_handling_in_direct_mode()
def test_tool_output_formatting()
```

**Expected**: Direct mode works correctly without daemon

### 9. Integration Tests: Fallback Behavior (test_fallback_behavior.py)

**Test Coverage**: Daemon detection and fallback logic

```python
# Integration tests for fallback behavior
def test_tool_call_uses_daemon_when_available()
def test_tool_call_falls_back_when_daemon_unavailable()
def test_no_daemon_flag_prevents_daemon_usage()
def test_daemon_crash_triggers_fallback()
def test_socket_deletion_triggers_fallback()
def test_daemon_timeout_triggers_fallback()
def test_verbose_flag_logs_mode_decision()
def test_fallback_is_transparent_to_user()
def test_repeated_calls_without_daemon()
def test_repeated_calls_with_daemon()
```

**Expected**: Seamless fallback with no user-visible errors

### 10. Integration Tests: Socket Communication (test_socket_communication.py)

**Test Coverage**: Unix socket IPC reliability

```python
# Integration tests for socket communication
def test_socket_connection_establishment()
def test_socket_message_serialization()
def test_socket_message_deserialization()
def test_socket_large_message_handling()
def test_socket_concurrent_connections()
def test_socket_timeout_handling()
def test_socket_cleanup_on_disconnect()
def test_socket_permission_errors()
def test_socket_path_with_special_characters()
def test_socket_recovery_after_daemon_restart()
```

**Expected**: Reliable socket communication with proper error handling

### 11. Integration Tests: Configuration Loading (test_config_loading.py)

**Test Coverage**: Configuration file parsing in context

```python
# Integration tests for configuration
def test_load_config_and_call_configured_server()
def test_config_with_multiple_servers()
def test_config_with_environment_variable_expansion()
def test_config_validation_before_execution()
def test_config_file_not_found_error()
def test_config_malformed_json_error()
def test_config_missing_required_fields()
def test_config_with_inline_json_arguments()
```

**Expected**: Configuration files correctly integrate with command execution

## Acceptance Criteria for ADR-0003

### Functional Requirements

- [ ] `cllm-mcp list-tools` works identically to `mcp-cli list-tools`
- [ ] `cllm-mcp call-tool` works identically to `mcp-cli call-tool`
- [ ] `cllm-mcp interactive` works identically to `mcp-cli interactive`
- [ ] `cllm-mcp daemon start` starts persistent daemon
- [ ] `cllm-mcp daemon status` shows daemon status and servers
- [ ] `cllm-mcp daemon stop` stops daemon cleanly
- [ ] `cllm-mcp daemon restart` restarts daemon
- [ ] `cllm-mcp config list` shows configured servers
- [ ] `cllm-mcp config validate` validates configuration file

### Performance Requirements

- [ ] Daemon mode provides 5-10x speedup for 5+ sequential tool calls
- [ ] Direct mode performance unchanged (<5% overhead from detection)
- [ ] Daemon detection completes in <100ms
- [ ] Fallback to direct mode is transparent (<5% latency increase)

### Compatibility Requirements

- [ ] `mcp-cli` command still works (backward compatible)
- [ ] `mcp-daemon` command still works (backward compatible)
- [ ] Existing scripts using `mcp-cli` continue to function
- [ ] Existing daemon management still works with new command

### Reliability Requirements

- [ ] Daemon fallback works when socket missing
- [ ] Daemon fallback works when daemon unresponsive
- [ ] Graceful handling of daemon crashes
- [ ] Proper cleanup of resources on exit
- [ ] Thread-safe concurrent daemon access
- [ ] No socket file collisions with multiple instances

### Usability Requirements

- [ ] Help text clearly explains daemon vs direct modes
- [ ] `--verbose` flag shows which mode is being used
- [ ] Error messages are clear and actionable
- [ ] Default behavior is sensible (transparent daemon use)
- [ ] Migration guide from `mcp-cli` to `cllm-mcp` available

## Test Execution Strategy

### Unit Tests

```bash
# Run all unit tests
uv run pytest tests/unit/ -v

# Run with coverage
uv run pytest tests/unit/ --cov=cllm_mcp --cov-report=html

# Run single test module
uv run pytest tests/unit/test_main_dispatcher.py -v
```

### Integration Tests

```bash
# Run all integration tests (may be slower)
uv run pytest tests/integration/ -v

# Run with timeout (integration tests may take longer)
uv run pytest tests/integration/ -v --timeout=10
```

### Full Test Suite

```bash
# Run all tests
uv run pytest tests/ -v --cov=cllm_mcp --cov-report=html

# Run with markers
uv run pytest -m "not slow" -v  # Skip slow tests
```

### CI/CD Integration

```yaml
# In .github/workflows/test.yml
- name: Run unit tests
  run: uv run pytest tests/unit/ --cov=cllm_mcp

- name: Run integration tests
  run: uv run pytest tests/integration/ --timeout=10

- name: Generate coverage report
  run: uv run pytest --cov=cllm_mcp --cov-report=xml
```

## Mock and Fixture Strategy

### Mock MCP Server (fixtures/mock_servers.py)

```python
class MockMCPServer:
    """Mock server that simulates MCP protocol behavior"""
    def __init__(self, tools=None, responses=None):
        self.tools = tools or self.default_tools()
        self.responses = responses or {}

    def start(self) -> str:
        """Start mock server, return command to invoke it"""

    def stop(self):
        """Shutdown mock server"""

    def simulate_tool_call(self, tool_name: str, args: dict) -> dict:
        """Simulate a tool call"""

    def simulate_crash(self):
        """Simulate server crash"""
```

### Socket Testing Helpers (fixtures/socket_helpers.py)

```python
class MockSocket:
    """Mock Unix socket for testing without actual socket files"""
    def connect(self, path: str): pass
    def send(self, data: bytes): pass
    def recv(self, size: int) -> bytes: pass
    def close(self): pass

def create_test_socket_server(socket_path: str):
    """Create a test socket server that responds to daemon protocol"""

def cleanup_test_sockets():
    """Clean up any test socket files"""
```

### Pytest Fixtures (conftest.py)

```python
@pytest.fixture
def mock_server():
    """Provides a mock MCP server for testing"""
    server = MockMCPServer()
    yield server
    server.stop()

@pytest.fixture
def temp_socket():
    """Provides a temporary socket path for testing"""
    path = f"/tmp/test-mcp-{os.getpid()}-{uuid.uuid4()}.sock"
    yield path
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def temp_config_file(tmp_path):
    """Provides a temporary config file for testing"""
    config = {
        "mcpServers": {
            "test-server": {
                "command": "python -m test_server",
                "description": "Test server"
            }
        }
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))
    return config_file

@pytest.fixture
def isolated_filesystem(tmp_path):
    """Provides isolated filesystem for testing"""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(old_cwd)
```

## Pytest Configuration

### pyproject.toml

```toml
[tool.pytest.ini_options]
# Test discovery patterns
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# Output options
addopts = "--strict-markers -v --tb=short"
testpaths = ["tests"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow running tests",
    "socket: Tests requiring socket operations",
    "daemon: Tests requiring daemon operations",
]

# Coverage options
[tool.coverage.run]
source = ["cllm_mcp"]
branch = true
omit = ["*/tests/*", "*/test_*.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
skip_covered = false
precision = 2
```

## Test Data and Constants (fixtures/test_data.py)

```python
# Sample tool definitions
SAMPLE_TOOLS = [
    {
        "name": "echo",
        "description": "Echo tool",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            }
        }
    }
]

# Sample tool responses
SAMPLE_TOOL_RESPONSE = {
    "content": [{"type": "text", "text": "Hello, World!"}]
}

# Sample configuration
SAMPLE_CONFIG = {
    "mcpServers": {
        "test-server": {
            "command": "python -m test_server",
            "args": ["--port", "9000"],
            "env": {"DEBUG": "1"},
            "description": "Test server"
        }
    }
}
```

## Coverage Goals

### Target Coverage

| Component                  | Target |
| -------------------------- | ------ |
| mcp_cli.py (existing)      | 85%    |
| mcp_daemon.py (existing)   | 85%    |
| main.py (new dispatcher)   | 90%    |
| config.py (new management) | 85%    |
| Overall project            | 85%    |

### Critical Paths (Must Have Tests)

- Command dispatch logic (100%)
- Daemon detection logic (100%)
- Fallback behavior (100%)
- Socket communication (90%)
- Error handling paths (90%)
- Configuration loading (90%)

## Test Schedule

### Phase 1: Setup (Week 1)

- [ ] Create test directory structure
- [ ] Configure pytest in pyproject.toml
- [ ] Create conftest.py with shared fixtures
- [ ] Create mock server fixtures
- [ ] Add pytest to dev-dependencies

### Phase 2: Unit Tests (Weeks 1-2)

- [ ] Test command dispatcher
- [ ] Test daemon detection logic
- [ ] Test CLI parser
- [ ] Test configuration management
- [ ] Achieve 85% unit test coverage

### Phase 3: Integration Tests (Weeks 2-3)

- [ ] Test daemon mode end-to-end
- [ ] Test direct mode end-to-end
- [ ] Test fallback behavior
- [ ] Test socket communication
- [ ] Achieve 80%+ integration coverage

### Phase 4: CI/CD & Polish (Week 3)

- [ ] Add GitHub Actions workflow for tests
- [ ] Configure coverage reporting
- [ ] Document testing procedures
- [ ] Add performance benchmarks

## Documentation References

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Python testing best practices](https://docs.pytest.org/en/latest/goodpractices.html)

## Approval and Sign-off

- [ ] Test strategy approved by maintainers
- [ ] Test implementation complete
- [ ] All acceptance criteria met
- [ ] Coverage targets achieved
- [ ] CI/CD integration verified
- [ ] Documentation updated
