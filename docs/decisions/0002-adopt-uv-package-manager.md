# ADR-0002: Adopt uv as the Python Package Manager

## Status

Accepted

## Context

The cllm-mcp project currently uses standard Python package management tools. However, package management in Python has several pain points:

- **Speed**: Traditional pip can be slow, especially for large dependency trees
- **Lock file reliability**: Dependency resolution can be inconsistent across environments
- **Complexity**: Managing different tools (pip, pip-tools, virtualenv) adds cognitive overhead
- **Installation time**: Initial and incremental installs can be time-consuming

The project has `uv.lock` already present, indicating prior consideration. [uv](https://github.com/astral-sh/uv) is a modern Python package installer and resolver written in Rust that addresses these concerns with:

- **Exceptional speed**: 10-100x faster than pip for most operations
- **Deterministic resolution**: All environments use the same lock file
- **Single tool approach**: Replaces pip, pip-tools, and virtualenv
- **Drop-in replacement**: Compatible with pip's CLI and PyPI
- **Active development**: Backed by Astral and the broader Python community

## Decision

We adopt uv as the primary Python package manager for the cllm-mcp project. This includes:

1. Using `uv` for all dependency management operations
2. Committing `uv.lock` to version control for deterministic builds
3. Documenting uv usage in project README and contributor guidelines
4. Using `pyproject.toml` as the single source of truth for dependencies

## Consequences

### Positive

- **Faster development**: Installation and dependency resolution are significantly faster
- **More reliable builds**: Lock file ensures consistent dependency versions across all environments
- **Simplified tooling**: Single tool replaces multiple Python package management tools
- **Better reproducibility**: Deterministic dependency resolution prevents "works on my machine" issues
- **Reduced friction**: Faster feedback loop during development and CI/CD
- **Community adoption**: Growing ecosystem and strong backing in the Python community

### Negative

- **New tool learning curve**: Team members unfamiliar with uv will need to learn its CLI
- **Ecosystem maturity**: Newer tool compared to pip (though rapidly maturing)
- **Documentation**: Fewer Stack Overflow answers and tutorials compared to pip
- **Integration assumptions**: Some tools may assume pip/virtualenv and need verification

## Alternatives Considered

- **Continue with pip + pip-tools**: Traditional approach but slower and requires multiple tools
- **Poetry**: Full dependency management with lock files, but larger ecosystem and more opinionated
- **PDM**: Python Development Master with lock file support, good but less mature than uv
- **Conda**: Works well but adds complexity for a pure Python project and different ecosystem

## Implementation Notes

1. Remove any pip-based workflows and scripts
2. Update CI/CD pipelines to use `uv pip install` or `uv sync`
3. Document in README:
   - Installation instructions for uv
   - How to add/update dependencies: `uv add package-name`
   - How to sync environment: `uv sync`
4. Update contributor documentation to reference uv instead of pip
5. Keep `uv.lock` in version control to ensure reproducible installs
6. For users without uv installed, provide fallback instructions

## More Information

- [uv GitHub Repository](https://github.com/astral-sh/uv)
- [uv Documentation](https://docs.astral.sh/uv/)
- [uv Benchmarks](https://astral.sh/blog/uv-benchmarks)
- Related: ADR-0001 (Adopt Vibe ADR)
