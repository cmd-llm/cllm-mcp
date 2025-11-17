"""Environment variable expansion and resolution for MCP servers.

This module implements the environment variable support specified in ADR-0008,
providing variable expansion, merging, and validation for MCP server initialization.
"""

import re
from typing import Dict, List, Optional


class EnvironmentVariableError(Exception):
    """Raised when environment variable resolution fails."""

    def __init__(self, server: str, var: str, reason: str):
        self.server = server
        self.variable = var
        self.reason = reason
        super().__init__(
            f"Environment variable error in '{server}': ${{{var}}} - {reason}"
        )


def expand_env_variable(
    value: str, parent_env: Dict[str, str], strict: bool = False
) -> str:
    """Expand environment variable references in a value string.

    Patterns:
    - "${VAR}" - Direct reference (raises if not found, strict=True)
    - "${VAR:default}" - Reference with fallback default
    - "literal" - Literal string (unchanged)

    Args:
        value: String potentially containing ${VAR} references
        parent_env: Parent environment dict to pull variables from
        strict: If True, raise on undefined variables without defaults

    Returns:
        Expanded string with variables resolved

    Raises:
        EnvironmentVariableError: If strict=True and var undefined without default
        ValueError: If expansion syntax is malformed
    """
    if not isinstance(value, str):
        return str(value)

    # Pattern to match ${VAR} or ${VAR:default}
    # Negative lookbehind prevents matching escaped \${
    pattern = r"(?<!\\)\$\{([^}:]+)(?::([^}]*))?\}"

    def replace_var(match: re.Match) -> str:
        var_name = match.group(1)
        var_default = match.group(2)

        # Check for nested expansion (not supported)
        if "${" in var_name or (var_default and "${" in var_default):
            raise ValueError(f"Nested expansion not supported: {match.group(0)}")

        # Look up variable in parent environment
        if var_name in parent_env:
            return parent_env[var_name]

        # Variable not found
        if var_default is not None:
            # Default was provided, use it
            return var_default
        elif strict:
            # No default and strict mode - raise error
            raise EnvironmentVariableError(
                server="<unknown>",
                var=var_name,
                reason="variable not found and no default provided",
            )
        else:
            # No default and non-strict mode - return original pattern
            return match.group(0)

    # Replace all ${VAR} patterns
    result = re.sub(pattern, replace_var, value)

    # Handle escaped braces: \${ becomes ${
    result = result.replace(r"\${", "${")

    return result


def validate_env_config(
    env_dict: Optional[Dict], server_name: str = "<unknown>"
) -> List[str]:
    """Validate environment variable configuration.

    Checks:
    - env field is dict or None
    - All keys are strings
    - All values are strings
    - No malformed expansion syntax

    Args:
        env_dict: Environment dictionary from server config (can be None)
        server_name: Name of server for error messages

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: List[str] = []

    if env_dict is None:
        return errors

    if not isinstance(env_dict, dict):
        errors.append(
            f"Server '{server_name}': 'env' must be a dict, "
            f"got {type(env_dict).__name__}"
        )
        return errors

    for key, value in env_dict.items():
        if not isinstance(key, str):
            errors.append(
                f"Server '{server_name}': env key must be string, "
                f"got {type(key).__name__}"
            )
            continue

        if not isinstance(value, str):
            errors.append(
                f"Server '{server_name}': env['{key}'] must be string, "
                f"got {type(value).__name__}"
            )
            continue

        # Validate expansion syntax
        if "${" in value:
            # Check for malformed patterns
            if not re.search(r"\$\{[^}]+\}", value):
                # Pattern contains ${ but no valid }
                errors.append(
                    f"Server '{server_name}': env['{key}'] has malformed "
                    f"variable expansion: {value}"
                )
            # Check for nested expansion
            elif "${" in value.replace("${", "", 1):
                # More than one ${ suggests nested expansion
                try:
                    # Try to detect nested patterns
                    for match in re.finditer(r"\$\{([^}]*)\}", value):
                        var_content = match.group(1)
                        if "${" in var_content:
                            errors.append(
                                f"Server '{server_name}': env['{key}'] has "
                                f"nested variable expansion: {value}"
                            )
                            break
                except Exception:  # noqa: B014,B110
                    # Ignore errors in variable expansion validation
                    pass

    return errors


def build_server_env(
    server_name: str,
    config_env: Optional[Dict[str, str]],
    parent_env: Dict[str, str],
    cli_overrides: Optional[Dict[str, str]] = None,
    strict: bool = False,
) -> Dict[str, str]:
    """Merge environment from multiple sources with proper precedence.

    Precedence (low to high):
    1. Parent environment (inherited)
    2. Server-specific environment (from config)
    3. CLI overrides (if present)

    Args:
        server_name: Name of server (for error messages)
        config_env: Server-specific env from configuration
        parent_env: Parent process environment
        cli_overrides: CLI-provided environment variables
        strict: If True, raise on undefined variables without defaults

    Returns:
        Merged environment dict ready for subprocess

    Raises:
        EnvironmentVariableError: If strict=True and required var missing
    """
    # Start with parent environment (allows inheritance)
    merged_env = parent_env.copy()

    # Apply server-specific environment from config
    if config_env:
        for key, value in config_env.items():
            try:
                # Expand the value using parent_env as reference
                expanded_value = expand_env_variable(value, parent_env, strict=strict)
                merged_env[key] = expanded_value
            except EnvironmentVariableError as e:
                # Re-raise with server context
                raise EnvironmentVariableError(
                    server=server_name, var=e.variable, reason=e.reason
                ) from e

    # Apply CLI overrides (highest priority)
    if cli_overrides:
        merged_env.update(cli_overrides)

    return merged_env


def resolve_server_env_overrides(
    server_name: str, parent_env: Dict[str, str]
) -> Dict[str, str]:
    """Extract CLLM_MCP_SERVER_ENV_* overrides from environment.

    Looks for environment variables matching the pattern:
    CLLM_MCP_SERVER_ENV_{SERVER}_{VAR}=value

    Args:
        server_name: Name of server to look up overrides for
        parent_env: Environment dict to search

    Returns:
        Dictionary of overrides for this server
    """
    overrides = {}
    prefix = f"CLLM_MCP_SERVER_ENV_{server_name.upper()}_"

    for key, value in parent_env.items():
        if key.startswith(prefix):
            var_name = key[len(prefix) :]
            overrides[var_name] = value

    return overrides


def mask_sensitive_variables(
    env_dict: Dict[str, str], sensitive_patterns: Optional[List[str]] = None
) -> Dict[str, str]:
    """Mask sensitive variables for logging purposes.

    Creates a copy of the environment with sensitive values replaced
    with placeholder text.

    Args:
        env_dict: Environment dictionary to mask
        sensitive_patterns: List of variable name patterns to mask
                          (e.g., ["*API*", "*SECRET*", "PASSWORD"])

    Returns:
        Copy of environment with sensitive values masked
    """
    if sensitive_patterns is None:
        # Default sensitive patterns
        sensitive_patterns = [
            "*API*",
            "*SECRET*",
            "*PASSWORD*",
            "*TOKEN*",
            "*KEY*",
            "*CREDENTIAL*",
        ]

    masked = env_dict.copy()

    for key in masked:
        # Check if key matches any sensitive pattern
        for pattern in sensitive_patterns:
            if _matches_pattern(key, pattern):
                masked[key] = "***MASKED***"
                break

    return masked


def _matches_pattern(name: str, pattern: str) -> bool:
    """Check if a name matches a glob pattern.

    Args:
        name: String to check
        pattern: Glob pattern (supports * wildcards)

    Returns:
        True if name matches pattern
    """
    # Convert glob pattern to regex
    regex_pattern = pattern.replace("*", ".*").replace("?", ".")
    regex_pattern = f"^{regex_pattern}$"
    return bool(re.match(regex_pattern, name, re.IGNORECASE))
