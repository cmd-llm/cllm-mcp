"""Unit tests for configuration management (cllm_mcp/config.py)."""

import json
import os
import pytest
from pathlib import Path


class TestCLLMConfigPrecedence:
    """Tests for CLLM-style configuration precedence (ADR-0004)."""

    @pytest.mark.unit
    def test_find_config_returns_tuple(self, config_file):
        """Test that find_config_file returns tuple of (path, trace)."""
        from cllm_mcp.config import find_config_file

        path, trace = find_config_file(config_file)
        assert path is not None
        assert isinstance(trace, list)

    @pytest.mark.unit
    def test_precedence_explicit_path_highest(self, temp_config_dir):
        """Test that explicit path has highest precedence."""
        from cllm_mcp.config import find_config_file

        # Create test config
        explicit_config = Path(temp_config_dir) / "explicit.json"
        explicit_config.write_text('{"mcpServers": {}}')

        # Find should return explicit path
        path, _ = find_config_file(str(explicit_config))
        assert path == explicit_config

    @pytest.mark.unit
    def test_precedence_current_directory(self, temp_config_dir, monkeypatch):
        """Test that ./mcp-config.json is found."""
        from cllm_mcp.config import find_config_file

        # Create config in current directory
        cwd_config = Path(temp_config_dir) / "mcp-config.json"
        cwd_config.write_text('{"mcpServers": {}}')

        # Change to temp directory
        monkeypatch.chdir(temp_config_dir)

        path, _ = find_config_file()
        # Use resolve() for consistent path comparison across platforms
        assert path.resolve() == cwd_config.resolve()

    @pytest.mark.unit
    def test_verbose_tracing_enabled(self, config_file):
        """Test that verbose tracing returns trace messages."""
        from cllm_mcp.config import find_config_file

        path, trace = find_config_file(config_file, verbose=True)
        assert len(trace) > 0
        assert any("[CONFIG]" in msg for msg in trace)

    @pytest.mark.unit
    def test_verbose_tracing_disabled_by_default(self, config_file):
        """Test that verbose tracing is empty by default."""
        from cllm_mcp.config import find_config_file

        path, trace = find_config_file(config_file, verbose=False)
        assert len(trace) == 0

    @pytest.mark.unit
    def test_environment_variable_override(self, config_file, monkeypatch):
        """Test that CLLM_MCP_CONFIG environment variable is used."""
        from cllm_mcp.config import find_config_file

        monkeypatch.setenv("CLLM_MCP_CONFIG", config_file)
        path, _ = find_config_file(verbose=True)
        assert path == Path(config_file)

    @pytest.mark.unit
    def test_backward_compatibility_deprecation_warning(self, config_file):
        """Test that deprecation warnings are shown in verbose trace."""
        from cllm_mcp.config import find_config_file

        # Use a path that doesn't exist to trigger deprecated paths check
        path, trace = find_config_file(verbose=True)

        # Even if not found, trace should show that deprecated paths were checked
        trace_str = "\n".join(trace).lower()
        if "deprecated" in trace_str:
            # If deprecated path found, should have warning
            assert any("warn" in msg.lower() for msg in trace)


class TestConfigLoading:
    """Tests for loading configuration files."""

    @pytest.mark.unit
    def test_load_config_from_explicit_path(self, config_file):
        """Test loading config from explicitly specified path."""
        from cllm_mcp.config import load_config
        config = load_config(config_file)
        assert "mcpServers" in config
        assert "time" in config["mcpServers"]

    @pytest.mark.unit
    def test_load_config_from_home_directory(self, temp_config_dir):
        """Test loading config from ~/.config/cllm-mcp/config.json."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_load_config_from_xdg_config_home(self, temp_config_dir):
        """Test loading config from $XDG_CONFIG_HOME/cllm-mcp/config.json."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_load_config_from_etc(self, temp_config_dir):
        """Test loading config from /etc/cllm-mcp/config.json."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_load_config_from_current_directory(self, temp_config_dir):
        """Test loading config from current working directory."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_config_file_not_found_raises_error(self):
        """Test that missing config file raises FileNotFoundError."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_config_file_search_order(self):
        """Test that config files are searched in correct order."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_first_found_config_is_used(self):
        """Test that first found config file is used."""
        # TODO: Implement test
        pass


class TestConfigValidation:
    """Tests for configuration validation."""

    @pytest.mark.unit
    def test_validate_valid_config(self, config_file):
        """Test that valid config passes validation."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_validate_requires_mcpServers_key(self):
        """Test that mcpServers key is required."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_validate_server_requires_command(self):
        """Test that each server requires a command."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_validate_server_command_must_be_string(self):
        """Test that server command must be a string."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_validate_server_args_must_be_list(self):
        """Test that server args (if present) must be a list."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_validate_detects_invalid_json(self):
        """Test that invalid JSON is detected."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_validate_detects_missing_required_fields(self):
        """Test that missing required fields are detected."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_validate_detects_extra_unknown_fields(self):
        """Test that extra unknown fields are detected (warning)."""
        # TODO: Implement test
        pass


class TestServerDiscovery:
    """Tests for discovering servers from configuration."""

    @pytest.mark.unit
    def test_list_configured_servers(self, config_file):
        """Test listing all configured servers."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_get_server_by_name(self, config_file):
        """Test retrieving specific server by name."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_get_server_returns_none_for_missing_server(self, config_file):
        """Test that getting missing server returns None."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_server_name_resolution(self, config_file):
        """Test resolving server name to full command."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_build_server_command(self, config_file):
        """Test building full command for server."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_server_with_args_builds_correctly(self, config_file):
        """Test that server with args builds complete command."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_server_without_args_builds_correctly(self, config_file):
        """Test that server without args builds correct command."""
        # TODO: Implement test
        pass


class TestConfigMerging:
    """Tests for merging environment variables and config."""

    @pytest.mark.unit
    def test_environment_variable_overrides_config(self):
        """Test that environment variables override config values."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_command_line_overrides_config(self):
        """Test that command-line args override config values."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_command_line_overrides_environment(self):
        """Test that command-line args override environment variables."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_config_priority_order(self):
        """Test priority order: CLI > ENV > FILE."""
        # TODO: Implement test
        pass


class TestConfigEdgeCases:
    """Tests for edge cases in configuration."""

    @pytest.mark.unit
    def test_empty_config_file(self, temp_config_dir):
        """Test handling of empty config file."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_config_with_empty_mcpServers(self, temp_config_dir):
        """Test config with empty mcpServers dict."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_server_name_case_sensitivity(self, config_file):
        """Test that server names are case-sensitive."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_special_characters_in_server_names(self, temp_config_dir):
        """Test handling of special characters in server names."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_very_long_server_names(self, temp_config_dir):
        """Test handling of very long server names."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_unicode_in_config(self, temp_config_dir):
        """Test handling of unicode characters in config."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_config_with_comments(self):
        """Test that comments in config are handled properly."""
        # TODO: Implement test
        pass


class TestConfigCommands:
    """Tests for config subcommands."""

    @pytest.mark.unit
    def test_config_list_command(self, config_file):
        """Test config list command output."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_config_list_shows_all_servers(self, config_file):
        """Test that config list shows all configured servers."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_config_validate_command_success(self, config_file):
        """Test config validate command with valid config."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_config_validate_command_failure(self, temp_config_dir):
        """Test config validate command with invalid config."""
        # TODO: Implement test
        pass

    @pytest.mark.unit
    def test_config_validate_shows_all_errors(self):
        """Test that config validate shows all validation errors."""
        # TODO: Implement test
        pass
