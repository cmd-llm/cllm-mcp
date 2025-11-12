# Contributing to MCP CLI

We're excited that you want to contribute to the MCP CLI project! This guide will help you get set up and explain our development practices.

## Development Setup

### Prerequisites

- Python 3.7 or higher
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager (required)
- Node.js and npm (for testing with MCP servers)
- Git

### Installing Dependencies

We use **uv** for all Python dependency management. This ensures fast, deterministic builds across all environments.

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository-url>
cd cllm-mcp

# Sync dependencies using uv
uv sync
```

### Working with Dependencies

**Adding a new dependency:**
```bash
uv add package-name
```

This will:
- Update `pyproject.toml` with the dependency
- Update `uv.lock` with the resolved dependency tree
- Ensure all environments use the same versions

**Updating dependencies:**
```bash
uv sync
```

This reads from `uv.lock` to ensure everyone has the same versions.

**Do NOT use pip directly** - Always use `uv` for dependency management to maintain `uv.lock` consistency.

## Development Workflow

### Running the Code

```bash
# Using uv run (recommended)
uv run mcp-cli --help

# Or activate the virtual environment
source .venv/bin/activate
mcp_cli.py --help
```

### Testing

```bash
# Run tests (when tests are added)
uv run pytest

# Or with virtual environment activated
pytest
```

### Making Changes

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Ensure `uv.lock` is committed if you modified dependencies
4. Write clear commit messages
5. Submit a pull request

## Code Style and Standards

- Follow PEP 8 for Python code style
- Include docstrings for public functions
- Add comments for complex logic
- Keep functions focused and testable

## Architecture Decisions

This project uses the Vibe ADR (Architecture Decision Record) framework for documenting important decisions. Key ADRs:

- [ADR-0001: Adopt Vibe ADR](docs/decisions/0001-adopt-vibe-adr.md)
- [ADR-0002: Adopt uv as the Python Package Manager](docs/decisions/0002-adopt-uv-package-manager.md)

Before making significant architectural changes, consider creating a new ADR to document the decision.

## Submitting a Pull Request

1. **Ensure your branch is up to date:**
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Test your changes:**
   ```bash
   uv run mcp-cli list-tools "npx -y @modelcontextprotocol/server-filesystem /tmp"
   ```

3. **Verify `uv.lock` is committed:**
   ```bash
   git status
   ```
   If you modified dependencies, ensure `uv.lock` is staged and committed.

4. **Push your branch and open a PR:**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Provide a clear PR description:**
   - What problem does this solve?
   - How does it solve it?
   - Any breaking changes?

## Reporting Issues

If you find a bug or have a feature request:

1. Check existing issues to avoid duplicates
2. Provide a clear, concise title
3. Include:
   - Steps to reproduce (for bugs)
   - Expected behavior
   - Actual behavior
   - Your environment (OS, Python version, etc.)

## Questions?

If you have questions about contributing, feel free to:
- Open an issue with your question
- Check existing discussions
- Review the [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md)

## License

By contributing to this project, you agree that your contributions will be licensed under its MIT License.

---

Thank you for contributing! 🚀
