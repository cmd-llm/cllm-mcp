# Quick Start Guide

Get started with MCP CLI in 5 minutes!

## Installation (Recommended: Using uv)

This project uses [uv](https://docs.astral.sh/uv/) as its Python package manager for faster, deterministic dependency management.

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone the repository
git clone <this-repo>
cd research

# 3. Install the project using uv
uv sync

# 4. Make scripts executable
chmod +x mcp_cli.py mcp-*.sh examples/*.sh

# 5. Verify installation
uv run mcp-cli --help
```

### Alternative: Direct Python Execution

If you prefer not to use uv, you can run the Python script directly (Python 3.7+ required):
```bash
./mcp_cli.py --help
```

> **Note**: This project officially uses `uv` for dependency management. See [ADR-0002](docs/decisions/0002-adopt-uv-package-manager.md) for details.

## Basic Usage

### Test with Filesystem Server

```bash
# List available tools (using uv)
uv run mcp-cli list-tools "npx -y @modelcontextprotocol/server-filesystem /tmp"

# Create a test file
echo "Hello MCP" > /tmp/test.txt

# Read the file using MCP
uv run mcp-cli call-tool "npx -y @modelcontextprotocol/server-filesystem /tmp" \
    read_file '{"path": "/tmp/test.txt"}'
```

**Or use the Python script directly:**
```bash
./mcp_cli.py list-tools "npx -y @modelcontextprotocol/server-filesystem /tmp"
./mcp_cli.py call-tool "npx -y @modelcontextprotocol/server-filesystem /tmp" \
    read_file '{"path": "/tmp/test.txt"}'
```

## Using Configuration (Recommended)

### 1. Create Your Config

```bash
# Copy example config
cp mcp-config.example.json mcp-config.json

# Edit it (optional - works out of box for filesystem)
nano mcp-config.json
```

### 2. Use the Wrapper

```bash
# List tools from configured server
./mcp-wrapper.sh filesystem list-tools

# Call a tool
./mcp-wrapper.sh filesystem call-tool read_file '{"path": "/tmp/test.txt"}'

# Interactive mode (try it!)
./mcp-wrapper.sh filesystem interactive
```

## For LLM Integration

### Minimal System Prompt

Add this to your LLM's system prompt:

```
You can perform file operations using:
  ./mcp-wrapper.sh filesystem call-tool <tool_name> '<json_params>'

Common tools:
- read_file: '{"path": "<path>"}'
- write_file: '{"path": "<path>", "content": "<content>"}'
- list_directory: '{"path": "<path>"}'

Extract results with jq: | jq -r '.content[0].text'
```

### Test It

Ask your LLM: "Read the file /tmp/test.txt"

Expected LLM response:
```bash
./mcp-wrapper.sh filesystem call-tool read_file '{"path": "/tmp/test.txt"}' | jq -r '.content[0].text'
```

## Adding More Servers

### GitHub Example

```bash
# Add to mcp-config.json:
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token_here"
      }
    }
  }
}

# Use it:
./mcp-wrapper.sh github list-tools
```

### Web Search Example (Brave)

```bash
# Add to mcp-config.json:
{
  "mcpServers": {
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your_api_key"
      }
    }
  }
}

# Search the web:
./mcp-wrapper.sh brave-search call-tool search '{"query": "Model Context Protocol"}'
```

## Run the Example

```bash
# Full filesystem operations demo
./examples/file-operations.sh
```

## Troubleshooting

### "Command not found: npx"
Install Node.js: https://nodejs.org/

### "Permission denied"
```bash
chmod +x mcp_cli.py mcp-*.sh
```

### "Server process not started"
Check that the MCP server command is correct:
```bash
# Test manually:
npx -y @modelcontextprotocol/server-filesystem /tmp
```

### "No response from server"
The server might not support the requested tool. List tools first:
```bash
./mcp-wrapper.sh <server-name> list-tools
```

## Next Steps

1. Read the full [README.md](README.md) for detailed documentation
2. Check [examples/llm-integration.md](examples/llm-integration.md) for LLM patterns
3. Explore available MCP servers: https://github.com/modelcontextprotocol/servers
4. Create custom wrappers for your specific workflows

## Common Patterns

### Read → Process → Write

```bash
# Read file
CONTENT=$(./mcp-wrapper.sh filesystem call-tool read_file '{"path": "/tmp/input.txt"}' | jq -r '.content[0].text')

# Process (example: uppercase)
PROCESSED=$(echo "$CONTENT" | tr '[:lower:]' '[:upper:]')

# Write back
./mcp-wrapper.sh filesystem call-tool write_file "{\"path\": \"/tmp/output.txt\", \"content\": \"$PROCESSED\"}"
```

### Multiple Servers in One Script

```bash
#!/bin/bash
# Read local file, search web, create GitHub issue

# 1. Read local notes
NOTES=$(./mcp-wrapper.sh filesystem call-tool read_file '{"path": "/tmp/notes.txt"}' | jq -r '.content[0].text')

# 2. Search for related info
SEARCH=$(./mcp-wrapper.sh brave-search call-tool search "{\"query\": \"$NOTES\"}")

# 3. Create issue with findings
./mcp-wrapper.sh github call-tool create_issue "{
  \"owner\": \"myuser\",
  \"repo\": \"myrepo\",
  \"title\": \"Research: $NOTES\",
  \"body\": \"Search results:\\n$SEARCH\"
}"
```

## Tips for Success

1. **Start simple**: Test with filesystem server first
2. **Use interactive mode**: Great for exploring tool capabilities
3. **Check JSON syntax**: Use `jq` to validate JSON before passing to MCP
4. **Read error messages**: They usually indicate what's wrong
5. **Keep configs organized**: One config file per project/use-case

## Resources

- [MCP Specification](https://spec.modelcontextprotocol.io)
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)
- [This Project's README](README.md)

---

**Happy MCP CLI-ing!** 🚀
