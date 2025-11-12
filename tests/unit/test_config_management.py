"""
Unit tests for configuration management (ADR-0003).

Tests the new config subcommand functionality for loading, validating,
and discovering configured MCP servers.
"""

import json
import os
from pathlib import Path

import pytest


@pytest.mark.unit
class TestConfigLoading:
    """Tests for loading configuration files."""

    def test_load_valid_json_config(self, temp_config_file):
        """Test loading a valid JSON configuration file."""
        # Once config.py is implemented:
        # config = load_config(str(temp_config_file))
        # assert "mcpServers" in config
        pass

    def test_load_config_with_multiple_servers(self, tmp_path):
        """Test loading config with multiple server definitions."""
        config = {
            "mcpServers": {
                "server1": {"command": "cmd1"},
                "server2": {"command": "cmd2"},
                "server3": {"command": "cmd3"},
            }
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Once implemented:
        # loaded = load_config(str(config_file))
        # assert len(loaded["mcpServers"]) == 3
        pass

    def test_load_config_invalid_json_returns_error(self, tmp_path):
        """Test loading invalid JSON returns proper error."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid json }")

        # Once implemented:
        # with pytest.raises(ConfigError):
        #     load_config(str(config_file))
        pass

    def test_load_config_missing_file_returns_error(self):
        """Test loading missing config file returns error."""
        # Once implemented:
        # with pytest.raises(FileNotFoundError):
        #     load_config("/nonexistent/config.json")
        pass

    def test_load_config_with_trailing_comma_json(self, tmp_path):
        """Test that invalid JSON with trailing commas fails."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"servers": {},}')

        # Should fail to parse
        pass

    def test_config_file_permissions_error(self, tmp_path):
        """Test error when config file has wrong permissions."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")
        os.chmod(config_file, 0o000)

        # Once implemented should catch permission error
        try:
            pass
        finally:
            os.chmod(config_file, 0o644)

    def test_load_config_empty_servers(self, tmp_path):
        """Test loading config with no servers defined."""
        config = {"mcpServers": {}}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Should load successfully with empty servers
        pass


@pytest.mark.unit
class TestConfigValidation:
    """Tests for validating configuration."""

    def test_validate_required_command_field(self, tmp_path):
        """Test validation catches missing 'command' field."""
        config = {
            "mcpServers": {
                "bad-server": {
                    "description": "Missing command field"
                }
            }
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Once implemented:
        # errors = validate_config(str(config_file))
        # assert len(errors) > 0
        pass

    def test_validate_command_executable(self, tmp_path):
        """Test validation checks if command is executable."""
        config = {
            "mcpServers": {
                "test": {
                    "command": "/nonexistent/command"
                }
            }
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Should report command not found
        pass

    def test_validate_correct_format(self, temp_config_file):
        """Test validation passes for correct format."""
        # Once implemented:
        # errors = validate_config(str(temp_config_file))
        # assert len(errors) == 0
        pass

    def test_validate_detects_invalid_json_type(self, tmp_path):
        """Test validation detects invalid field types."""
        config = {
            "mcpServers": {
                "test": {
                    "command": "python",
                    "args": "not-a-list"  # Should be list
                }
            }
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Should report type error
        pass

    def test_validate_environment_variables(self, tmp_path):
        """Test validation of environment variables in config."""
        config = {
            "mcpServers": {
                "test": {
                    "command": "python",
                    "env": {"KEY": "value"}
                }
            }
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Should validate env field
        pass

    def test_validate_detects_circular_references(self, tmp_path):
        """Test validation detects circular references in config."""
        # If config supports references, should detect cycles
        pass

    def test_validate_returns_detailed_errors(self, tmp_path):
        """Test validation errors include line numbers and details."""
        config = {
            "mcpServers": {
                "bad": {}  # Missing required fields
            }
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Errors should be detailed
        pass


@pytest.mark.unit
class TestConfigList:
    """Tests for listing configured servers."""

    def test_list_shows_all_servers(self, temp_config_file):
        """Test list command shows all servers."""
        # Once implemented:
        # servers = list_servers(str(temp_config_file))
        # assert "test-server" in servers
        # assert "echo-server" in servers
        pass

    def test_list_includes_descriptions(self, temp_config_file):
        """Test list includes server descriptions."""
        # Server descriptions should be shown
        pass

    def test_list_includes_command_info(self, temp_config_file):
        """Test list includes command information."""
        # Should show command and args for each server
        pass

    def test_list_includes_environment_vars(self, temp_config_file):
        """Test list shows environment variables."""
        pass

    def test_list_empty_config(self, tmp_path):
        """Test list with empty server list."""
        config = {"mcpServers": {}}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Should indicate no servers configured
        pass

    def test_list_output_format(self, temp_config_file):
        """Test list output is formatted nicely."""
        # Should be readable (possibly table format)
        pass

    def test_list_with_json_output(self, temp_config_file):
        """Test list with --json flag outputs JSON."""
        # --json flag should output machine-readable JSON
        pass

    def test_list_sorted_alphabetically(self, tmp_path):
        """Test servers are listed in alphabetical order."""
        config = {
            "mcpServers": {
                "zebra": {"command": "z"},
                "apple": {"command": "a"},
                "middle": {"command": "m"},
            }
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Should be sorted: apple, middle, zebra
        pass


@pytest.mark.unit
class TestConfigWithEnvironment:
    """Tests for environment variable handling in config."""

    def test_config_expands_env_variables(self, tmp_path):
        """Test config expands environment variables."""
        os.environ["TEST_COMMAND"] = "/test/cmd"

        config = {
            "mcpServers": {
                "test": {
                    "command": "${TEST_COMMAND}"
                }
            }
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Should expand ${TEST_COMMAND}
        pass

    def test_config_env_variable_with_default(self, tmp_path):
        """Test config environment variable with default value."""
        # Syntax like ${VAR:-default}
        pass

    def test_config_missing_env_variable(self, tmp_path):
        """Test error when required environment variable missing."""
        config = {
            "mcpServers": {
                "test": {
                    "command": "${MISSING_VAR}"
                }
            }
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Should error or use default
        pass


@pytest.mark.unit
class TestConfigSearch:
    """Tests for finding config files."""

    def test_find_config_in_current_directory(self, isolated_temp_dir, tmp_path):
        """Test finding config in current directory."""
        # Look for mcp-config.json or .mcp-config.json in cwd
        pass

    def test_find_config_in_home_directory(self):
        """Test finding config in home directory."""
        # Look in ~/.config/cllm-mcp/config.json
        pass

    def test_find_config_in_etc(self):
        """Test finding config in /etc."""
        # Look in /etc/cllm-mcp/config.json on Linux
        pass

    def test_config_search_order(self):
        """Test config search order is correct."""
        # Order: --config > cwd > ~/.config > /etc
        pass

    def test_explicit_config_overrides_search(self):
        """Test explicit --config path overrides search."""
        pass


@pytest.mark.unit
class TestConfigEdgeCases:
    """Tests for edge cases in configuration."""

    def test_server_name_with_spaces(self, tmp_path):
        """Test server name with spaces."""
        config = {
            "mcpServers": {
                "my server": {
                    "command": "python"
                }
            }
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Should handle or reject clearly
        pass

    def test_server_name_with_special_characters(self, tmp_path):
        """Test server name with special characters."""
        config = {
            "mcpServers": {
                "server-with-dashes": {"command": "python"},
                "server_with_underscores": {"command": "python"},
                "server.with.dots": {"command": "python"},
            }
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Should handle these properly
        pass

    def test_command_with_quoted_args(self, tmp_path):
        """Test command arguments with quotes."""
        config = {
            "mcpServers": {
                "test": {
                    "command": "python",
                    "args": ['-c', 'print("hello")']
                }
            }
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Should handle quoted arguments
        pass

    def test_config_with_comments(self, tmp_path):
        """Test config file with comments."""
        # Standard JSON doesn't support comments
        # Should either reject or support JSON5/JSONC
        pass

    def test_very_large_config_file(self, tmp_path):
        """Test handling of very large config file."""
        servers = {str(i): {"command": f"cmd-{i}"} for i in range(1000)}
        config = {"mcpServers": servers}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        # Should handle large configs efficiently
        pass
