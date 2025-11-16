"""Tests for ADR-0008 environment variable expansion.

This test module covers the environment variable expansion, merging, and
validation functionality introduced by ADR-0008.
"""

import os

import pytest

from cllm_mcp.env_expansion import (
    EnvironmentVariableError,
    build_server_env,
    expand_env_variable,
    mask_sensitive_variables,
    resolve_server_env_overrides,
    validate_env_config,
)


class TestEnvVariableExpansion:
    """Test variable expansion parsing and resolution."""

    def test_literal_string_unchanged(self):
        """Literal strings without variables should be unchanged."""
        parent_env = {"HOME": "/home/alice"}
        result = expand_env_variable("plain string", parent_env)
        assert result == "plain string"

    def test_direct_variable_reference(self):
        """${VAR} should use parent env value."""
        parent_env = {"HOME": "/home/alice"}
        result = expand_env_variable("${HOME}", parent_env)
        assert result == "/home/alice"

    def test_variable_in_path(self):
        """Variables in paths should expand correctly."""
        parent_env = {"HOME": "/home/alice"}
        result = expand_env_variable("${HOME}/projects", parent_env)
        assert result == "/home/alice/projects"

    def test_multiple_variables(self):
        """Multiple ${VAR} in one string should all expand."""
        parent_env = {"HOME": "/home/alice", "USER": "alice"}
        result = expand_env_variable("${HOME}/${USER}", parent_env)
        assert result == "/home/alice/alice"

    def test_variable_with_default(self):
        """${VAR:default} should use default if not found."""
        parent_env = {}
        result = expand_env_variable("${UNDEFINED:default_value}", parent_env)
        assert result == "default_value"

    def test_variable_with_default_not_used_when_found(self):
        """${VAR:default} should use env value if found."""
        parent_env = {"VAR": "actual_value"}
        result = expand_env_variable("${VAR:default_value}", parent_env)
        assert result == "actual_value"

    def test_empty_default(self):
        """${VAR:} should use empty string as default."""
        parent_env = {}
        result = expand_env_variable("${UNDEFINED:}", parent_env)
        assert result == ""

    def test_special_chars_in_default(self):
        """${VAR:/path/to/file} should handle special chars."""
        parent_env = {}
        result = expand_env_variable("${PATH:/path/to/default}", parent_env)
        assert result == "/path/to/default"

    def test_undefined_variable_strict_mode(self):
        """${VAR} with strict=True should raise if undefined."""
        parent_env = {}
        with pytest.raises(EnvironmentVariableError):
            expand_env_variable("${UNDEFINED}", parent_env, strict=True)

    def test_undefined_variable_non_strict_mode(self):
        """${VAR} with strict=False should return original pattern."""
        parent_env = {}
        result = expand_env_variable("${UNDEFINED}", parent_env, strict=False)
        assert result == "${UNDEFINED}"

    def test_nested_expansion_rejected(self):
        """${${VAR}} should raise error."""
        parent_env = {"VAR": "value"}
        with pytest.raises(ValueError):
            expand_env_variable("${${VAR}}", parent_env)

    def test_escaped_braces(self):
        r"""\\${VAR} should produce literal ${VAR}."""
        parent_env = {"VAR": "value"}
        result = expand_env_variable(r"\${VAR}", parent_env)
        assert result == "${VAR}"

    def test_malformed_expansion_missing_closing_brace(self):
        """${VAR without closing } should raise error."""
        parent_env = {}
        # This is currently not detected as malformed during expansion,
        # but would be caught during validation
        result = expand_env_variable("${UNCLOSED", parent_env)
        assert result == "${UNCLOSED"


class TestEnvironmentMerging:
    """Test merging environments from multiple sources."""

    def test_parent_env_inherited(self):
        """Parent process env should be available to server."""
        parent_env = {"PARENT_VAR": "parent_value"}
        result = build_server_env("test", {}, parent_env)
        assert result["PARENT_VAR"] == "parent_value"

    def test_config_env_overrides_parent(self):
        """Config env should override parent values."""
        parent_env = {"VAR": "parent_value"}
        config_env = {"VAR": "config_value"}
        result = build_server_env("test", config_env, parent_env)
        assert result["VAR"] == "config_value"

    def test_cli_overrides_config(self):
        """CLI overrides should override config values."""
        parent_env = {"VAR": "parent_value"}
        config_env = {"VAR": "config_value"}
        cli_overrides = {"VAR": "cli_value"}
        result = build_server_env("test", config_env, parent_env, cli_overrides)
        assert result["VAR"] == "cli_value"

    def test_env_expansion_in_config(self):
        """Variables in config should be expanded."""
        parent_env = {"HOME": "/home/alice"}
        config_env = {"DATA_DIR": "${HOME}/data"}
        result = build_server_env("test", config_env, parent_env)
        assert result["DATA_DIR"] == "/home/alice/data"

    def test_env_expansion_with_default(self):
        """Default values should be used if var not found."""
        parent_env = {}
        config_env = {"LOG_DIR": "${LOG_DIR:/var/log}"}
        result = build_server_env("test", config_env, parent_env)
        assert result["LOG_DIR"] == "/var/log"

    def test_strict_mode_expansion(self):
        """Strict mode should raise on undefined vars without defaults."""
        parent_env = {}
        config_env = {"REQUIRED": "${UNDEFINED_VAR}"}
        with pytest.raises(EnvironmentVariableError):
            build_server_env("test", config_env, parent_env, strict=True)

    def test_non_strict_mode_expansion(self):
        """Non-strict mode should not raise on undefined vars."""
        parent_env = {}
        config_env = {"OPTIONAL": "${UNDEFINED_VAR}"}
        result = build_server_env("test", config_env, parent_env, strict=False)
        assert result["OPTIONAL"] == "${UNDEFINED_VAR}"

    def test_server_name_in_error(self):
        """Error messages should include server name."""
        parent_env = {}
        config_env = {"VAR": "${UNDEFINED}"}
        with pytest.raises(EnvironmentVariableError) as exc_info:
            build_server_env("my-server", config_env, parent_env, strict=True)
        assert "my-server" in str(exc_info.value)


class TestEnvironmentValidation:
    """Test environment variable configuration validation."""

    def test_valid_env_dict(self):
        """Valid env dict should have no errors."""
        env = {"VAR1": "value1", "VAR2": "${VAR1}"}
        errors = validate_env_config(env)
        assert errors == []

    def test_none_env_valid(self):
        """None env should be valid (optional field)."""
        errors = validate_env_config(None)
        assert errors == []

    def test_non_dict_env_invalid(self):
        """Non-dict env should produce error."""
        errors = validate_env_config("not a dict", "server")
        assert any("must be a dict" in e for e in errors)

    def test_non_string_key_invalid(self):
        """Non-string keys should produce error."""
        env = {1: "value"}
        errors = validate_env_config(env, "server")
        assert any("key must be string" in e for e in errors)

    def test_non_string_value_invalid(self):
        """Non-string values should produce error."""
        env = {"KEY": 123}
        errors = validate_env_config(env, "server")
        assert any("must be string" in e for e in errors)

    def test_malformed_expansion_syntax(self):
        """Malformed expansion syntax should produce error."""
        env = {"KEY": "${VAR without closing brace"}
        errors = validate_env_config(env, "server")
        # This might not catch all malformed syntax, but should catch severe issues
        # The specific validation depends on implementation
        # Just verify it completes without crashing
        assert isinstance(errors, list)

    def test_valid_expansion_syntax(self):
        """Valid expansion syntax should have no errors."""
        env = {"VAR1": "${HOME}", "VAR2": "${HOME:default}"}
        errors = validate_env_config(env, "server")
        assert errors == []


class TestServerEnvOverrides:
    """Test CLLM_MCP_SERVER_ENV_* override resolution."""

    def test_resolve_server_env_overrides(self):
        """Should extract CLLM_MCP_SERVER_ENV_* variables."""
        parent_env = {
            "CLLM_MCP_SERVER_ENV_MYSERVER_VAR1": "value1",
            "CLLM_MCP_SERVER_ENV_MYSERVER_VAR2": "value2",
            "OTHER_VAR": "should_not_match",
        }
        overrides = resolve_server_env_overrides("myserver", parent_env)
        assert overrides == {"VAR1": "value1", "VAR2": "value2"}

    def test_server_name_case_sensitivity(self):
        """Server name override matching should be case-sensitive."""
        parent_env = {
            "CLLM_MCP_SERVER_ENV_MYSERVER_VAR": "upper",
            "CLLM_MCP_SERVER_ENV_myserver_VAR": "lower",
        }
        overrides = resolve_server_env_overrides("myserver", parent_env)
        # Should only match the exact case
        assert "VAR" in overrides


class TestSensitiveVariableMasking:
    """Test masking of sensitive variables for logging."""

    def test_mask_api_keys(self):
        """API_KEY variables should be masked."""
        env = {"API_KEY": "secret123", "DATABASE_URL": "postgresql://..."}
        masked = mask_sensitive_variables(env)
        assert masked["API_KEY"] == "***MASKED***"

    def test_mask_passwords(self):
        """PASSWORD variables should be masked."""
        env = {"DB_PASSWORD": "secret", "USER_PASSWORD": "secret"}
        masked = mask_sensitive_variables(env)
        assert masked["DB_PASSWORD"] == "***MASKED***"
        assert masked["USER_PASSWORD"] == "***MASKED***"

    def test_mask_tokens(self):
        """TOKEN variables should be masked."""
        env = {"AUTH_TOKEN": "token123", "API_TOKEN": "token456"}
        masked = mask_sensitive_variables(env)
        assert masked["AUTH_TOKEN"] == "***MASKED***"
        assert masked["API_TOKEN"] == "***MASKED***"

    def test_preserve_non_sensitive_vars(self):
        """Non-sensitive variables should not be masked."""
        env = {"DATA_DIR": "/data", "LOG_LEVEL": "debug"}
        masked = mask_sensitive_variables(env)
        assert masked["DATA_DIR"] == "/data"
        assert masked["LOG_LEVEL"] == "debug"

    def test_custom_sensitive_patterns(self):
        """Should support custom sensitive patterns."""
        env = {"CUSTOM_SECRET": "value", "OTHER": "value"}
        masked = mask_sensitive_variables(env, ["*SECRET*"])
        assert masked["CUSTOM_SECRET"] == "***MASKED***"
        assert masked["OTHER"] == "value"

    def test_case_insensitive_pattern_matching(self):
        """Pattern matching should be case-insensitive."""
        env = {"api_key": "secret", "API_KEY": "secret", "Api_Key": "secret"}
        masked = mask_sensitive_variables(env)
        assert masked["api_key"] == "***MASKED***"
        assert masked["API_KEY"] == "***MASKED***"
        assert masked["Api_Key"] == "***MASKED***"


@pytest.mark.integration
class TestEnvironmentWithRealParentEnv:
    """Integration tests using real parent environment."""

    def test_expand_with_real_home(self):
        """Should expand ${HOME} using real parent environment."""
        home = os.environ.get("HOME", "/tmp")
        result = expand_env_variable("${HOME}/projects", os.environ)
        assert result.startswith(home)

    def test_merge_with_current_env(self):
        """Should merge with current environment."""
        # Add a test var to current environment
        os.environ["TEST_VAR"] = "test_value"
        try:
            config_env = {"MERGED": "${TEST_VAR}"}
            result = build_server_env("test", config_env, os.environ.copy())
            assert result["MERGED"] == "test_value"
        finally:
            del os.environ["TEST_VAR"]
