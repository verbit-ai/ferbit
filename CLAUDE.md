# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This repository contains a distributed AI agent system with MCP (Model Context Protocol) integration:

- **agents/**: Contains AI agent implementations
  - `expert_agent/`: Basic expert agent (currently minimal implementation)
  - `search_agent/`: Agent that integrates with MCP servers using pydantic-ai
- **mcp/**: MCP server implementations
  - `opensearch_mcp/`: FastMCP server providing mathematical operations

## Technology Stack

- **Python 3.11+**: All components require Python 3.11 or higher
- **pydantic-ai**: Used by search_agent for AI agent functionality and MCP integration
- **FastMCP**: Used by opensearch_mcp for creating MCP servers
- **uv**: Package manager used by search_agent and opensearch_mcp

## Development Commands

### Running Components

Each component is standalone with its own pyproject.toml:

```bash
# Run the expert agent
cd agents/expert_agent && python main.py

# Run the search agent (requires MCP server)
cd agents/search_agent && python main.py

# Run the MCP server
cd mcp/opensearch_mcp && python main.py
```

### MCP Server Integration

The search_agent connects to MCP servers via SSE (Server-Sent Events):
- Default MCP server URL: `http://localhost:8000/sse`
- Override with `MCP_SERVER_URL` environment variable
- The opensearch_mcp server runs on this endpoint when started

### Package Management

Each component uses uv for dependency management where applicable:

```bash
# Install dependencies (in components with uv.lock)
uv sync

# Add new dependencies
uv add <package-name>
```

## Key Integration Points

- The search_agent expects an MCP server to be running at the configured URL
- The opensearch_mcp provides basic arithmetic operations via MCP protocol
- Agents use OpenAI GPT-4o model by default (configurable in search_agent)

## Development Workflow

1. Start the MCP server: `cd mcp/opensearch_mcp && python main.py`
2. Run agents that depend on MCP services
3. Each component has minimal dependencies and can be developed independently