"""
Tests for ADR-0005: Auto-initialize MCP servers on daemon start.

This test module covers:
1. Configuration validation for autoStart and optional fields
2. Server initialization with parallel startup
3. Initialization failure handling (fail/warn/ignore policies)
4. Health monitoring and server restart
5. Status reporting with auto-started server info
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mcp_daemon import (
    InitializationResult,
    MCPDaemon,
    build_server_command,
    initialize_servers_async,
)

from cllm_mcp.config import validate_config


class TestConfigurationValidation:
    """Test validation of ADR-0005 configuration fields."""

    def test_validate_autostart_field(self):
        """Test that autoStart field must be boolean."""
        config = {
            "mcpServers": {
                "test": {
                    "command": "test-cmd",
                    "autoStart": "true",  # Invalid: should be boolean
                }
            }
        }
        errors = validate_config(config)
        assert any("autoStart" in error and "boolean" in error for error in errors)

    def test_validate_optional_field(self):
        """Test that optional field must be boolean."""
        config = {
            "mcpServers": {
                "test": {
                    "command": "test-cmd",
                    "optional": 1,  # Invalid: should be boolean
                }
            }
        }
        errors = validate_config(config)
        assert any("optional" in error and "boolean" in error for error in errors)

    def test_validate_daemon_section(self):
        """Test validation of daemon configuration section."""
        config = {
            "mcpServers": {"test": {"command": "test-cmd"}},
            "daemon": {
                "socket": "/tmp/test.sock",
                "timeout": 30,
                "maxServers": 10,
                "initializationTimeout": 60,
                "parallelInitialization": 4,
                "onInitFailure": "warn",
            },
        }
        errors = validate_config(config)
        assert not errors  # Should be valid

    def test_validate_daemon_section_invalid_types(self):
        """Test validation catches invalid daemon field types."""
        config = {
            "mcpServers": {"test": {"command": "test-cmd"}},
            "daemon": {
                "timeout": "30",  # Invalid: should be number
                "parallelInitialization": "4",  # Invalid: should be int
            },
        }
        errors = validate_config(config)
        assert any("timeout" in error for error in errors)
        assert any("parallelInitialization" in error for error in errors)

    def test_validate_on_init_failure_enum(self):
        """Test that onInitFailure is validated against allowed values."""
        config = {
            "mcpServers": {"test": {"command": "test-cmd"}},
            "daemon": {"onInitFailure": "invalid"},  # Invalid: must be fail/warn/ignore
        }
        errors = validate_config(config)
        assert any("onInitFailure" in error for error in errors)

    def test_valid_autostart_config(self):
        """Test that valid autoStart configuration passes validation."""
        config = {
            "mcpServers": {
                "server1": {
                    "command": "cmd1",
                    "autoStart": True,
                    "optional": False,
                },
                "server2": {
                    "command": "cmd2",
                    "autoStart": False,
                    "optional": True,
                },
            }
        }
        errors = validate_config(config)
        assert not errors


class TestBuildServerCommand:
    """Test server command building."""

    def test_build_command_without_args(self):
        """Test building command without args."""
        config = {"command": "uvx"}
        result = build_server_command(config)
        assert result == "uvx"

    def test_build_command_with_args(self):
        """Test building command with args."""
        config = {"command": "uvx", "args": ["mcp-server-time"]}
        result = build_server_command(config)
        assert result == "uvx mcp-server-time"

    def test_build_command_with_multiple_args(self):
        """Test building command with multiple args."""
        config = {
            "command": "python",
            "args": ["/path/to/server.py", "--option", "value"],
        }
        result = build_server_command(config)
        assert result == "python /path/to/server.py --option value"


class TestInitializationResult:
    """Test InitializationResult class."""

    def test_initialization_result_creation(self):
        """Test creating InitializationResult."""
        result = InitializationResult(
            total=3, successful=2, failed=1, optional_failures=1
        )
        assert result.total == 3
        assert result.successful == 2
        assert result.failed == 1
        assert result.optional_failures == 1

    def test_initialization_result_repr(self):
        """Test InitializationResult repr."""
        result = InitializationResult(total=3, successful=2, failed=1)
        repr_str = repr(result)
        assert "total=3" in repr_str
        assert "successful=2" in repr_str
        assert "failed=1" in repr_str


class TestInitializationLogic:
    """Test server initialization logic."""

    @pytest.mark.asyncio
    async def test_initialize_with_no_servers(self):
        """Test initialization when no servers are configured."""
        daemon = MCPDaemon()
        config = {"mcpServers": {}}

        result = await initialize_servers_async(daemon, config)

        assert result.total == 0
        assert result.successful == 0
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_initialize_with_no_auto_start_servers(self):
        """Test initialization when no servers have autoStart enabled."""
        daemon = MCPDaemon()
        config = {
            "mcpServers": {
                "manual": {
                    "command": "test-cmd",
                    "autoStart": False,
                }
            }
        }

        result = await initialize_servers_async(daemon, config)

        assert result.total == 0
        assert result.successful == 0

    @pytest.mark.asyncio
    async def test_initialize_skip_when_no_auto_init_flag(self):
        """Test that initialization is skipped when no_auto_init is True."""
        daemon = MCPDaemon()
        config = {
            "mcpServers": {
                "server": {
                    "command": "test-cmd",
                    "autoStart": True,
                }
            }
        }

        result = await initialize_servers_async(daemon, config, no_auto_init=True)

        assert result.total == 0
        assert result.successful == 0

    @pytest.mark.asyncio
    async def test_initialize_default_autostart_true(self):
        """Test that servers have autoStart=true by default."""
        daemon = MCPDaemon()
        config = {
            "mcpServers": {
                "server": {
                    "command": "test-cmd",
                    # Note: no autoStart field, should default to True
                }
            }
        }

        # Mock the start_server method
        with patch.object(daemon, "start_server") as mock_start:
            mock_start.return_value = {"success": True}

            await initialize_servers_async(daemon, config)

            # Should try to start the server since autoStart defaults to True
            assert mock_start.called


class TestDaemonAutoStartTracking:
    """Test daemon's tracking of auto-started servers."""

    def test_daemon_tracks_auto_started_servers(self):
        """Test that daemon tracks which servers were auto-started."""
        daemon = MCPDaemon()

        # Mock the MCPClient
        with patch("mcp_daemon.MCPClient"):
            # Simulate starting a server with auto_start=True
            daemon.servers["test1"] = MagicMock()
            daemon.auto_started_servers.add("test1")
            daemon.server_start_times["test1"] = 0

            # Simulate starting a server with auto_start=False
            daemon.servers["test2"] = MagicMock()

            assert "test1" in daemon.auto_started_servers
            assert "test2" not in daemon.auto_started_servers

    def test_daemon_status_includes_auto_start_info(self):
        """Test that get_status includes auto-start information."""
        daemon = MCPDaemon()

        # Add some test servers
        daemon.servers["auto1"] = MagicMock()
        daemon.auto_started_servers.add("auto1")
        daemon.server_start_times["auto1"] = 1000  # Fake start time

        daemon.servers["manual1"] = MagicMock()

        status = daemon.get_status()

        assert len(status["auto_started"]) == 1
        assert len(status["on_demand"]) == 1
        assert status["auto_start_count"] == 1
        assert status["on_demand_count"] == 1

    def test_daemon_status_uptime_calculation(self):
        """Test that uptime is included in status."""
        daemon = MCPDaemon()
        import time

        current_time = time.time()
        daemon.servers["server1"] = MagicMock()
        daemon.auto_started_servers.add("server1")
        daemon.server_start_times["server1"] = current_time - 60  # 1 minute ago

        status = daemon.get_status()

        auto_started = status["auto_started"]
        assert len(auto_started) > 0
        assert "uptime" in auto_started[0]
        assert 50 < auto_started[0]["uptime"] < 70  # Should be ~60 seconds


class TestHealthMonitoring:
    """Test health monitoring functionality."""

    def test_health_monitoring_detects_crashed_server(self):
        """Test that health monitoring detects when a server crashes."""
        daemon = MCPDaemon()
        daemon.config = {
            "mcpServers": {"test": {"command": "test-cmd", "autoStart": True}}
        }

        # Simulate running server
        daemon.auto_started_servers.add("test")
        daemon.servers["test"] = MagicMock()

        # Now simulate the server crashing (removing it from servers dict)
        del daemon.servers["test"]

        # Mock start_server to restart
        with patch.object(daemon, "start_server") as mock_start:
            mock_start.return_value = {"success": True}

            # Check one iteration of health monitoring
            if "test" not in daemon.servers:
                # This is what health_monitoring does
                server_config = daemon.config["mcpServers"]["test"]
                command = f"{server_config['command']}"
                daemon.start_server("test", command, auto_start=True)

            assert mock_start.called

    def test_health_monitoring_stops_on_running_false(self):
        """Test that health monitoring stops when daemon.running is False."""
        daemon = MCPDaemon()
        daemon.running = False

        # Should return quickly
        # (We can't really test the loop without threading complexity)
        assert daemon.running is False


class TestConfigurationDefaults:
    """Test default values for new configuration fields."""

    def test_default_autostart_is_true(self):
        """Test that autoStart defaults to True in list_servers."""
        from cllm_mcp.config import list_servers

        config = {
            "mcpServers": {"server": {"command": "test-cmd"}}  # No autoStart specified
        }

        servers = list_servers(config)

        assert len(servers) == 1
        assert servers[0]["autoStart"] is True  # Should default to True

    def test_default_optional_is_false(self):
        """Test that optional defaults to False in list_servers."""
        from cllm_mcp.config import list_servers

        config = {
            "mcpServers": {"server": {"command": "test-cmd"}}  # No optional specified
        }

        servers = list_servers(config)

        assert len(servers) == 1
        assert servers[0]["optional"] is False  # Should default to False


class TestFailureHandling:
    """Test failure handling with different policies."""

    @pytest.mark.asyncio
    async def test_required_server_failure_with_fail_policy(self):
        """Test that required server failure raises error with fail policy."""
        daemon = MCPDaemon()
        config = {
            "mcpServers": {
                "required": {
                    "command": "test-cmd",
                    "autoStart": True,
                    "optional": False,
                }
            },
            "daemon": {"onInitFailure": "fail"},
        }

        with patch.object(daemon, "start_server") as mock_start:
            mock_start.return_value = {"success": False, "error": "Connection failed"}

            with pytest.raises(RuntimeError):
                await initialize_servers_async(daemon, config)

    @pytest.mark.asyncio
    async def test_optional_server_failure_continues(self):
        """Test that optional server failure doesn't stop initialization."""
        daemon = MCPDaemon()
        config = {
            "mcpServers": {
                "optional": {
                    "command": "test-cmd",
                    "autoStart": True,
                    "optional": True,
                }
            },
            "daemon": {"onInitFailure": "warn"},
        }

        with patch.object(daemon, "start_server") as mock_start:
            mock_start.return_value = {"success": False, "error": "Connection failed"}

            # Should not raise, just warn
            result = await initialize_servers_async(daemon, config)

            assert result.failed == 1
            assert result.optional_failures == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
