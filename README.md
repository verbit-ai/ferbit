# Ferbit Backend - Multi-Agent System

A multi-agent system for legal case analysis with search validation and orchestration.

## Quick Start with Docker 🐋

### Prerequisites

- Docker and Docker Compose installed
- OpenAI API key

### Setup & Run

1. **Create environment file:**

   ```bash
   # Create .env file with your OpenAI API key:
   echo "OPENAI_API_KEY=sk-your-key-here" > .env
   # Or create manually and add: OPENAI_API_KEY=sk-your-openai-api-key
   ```

2. **Start all services:**

   ```bash
   ./run.sh
   ```

3. **Stop services:**
   ```bash
   ./stop.sh
   ```

## Services

| Service      | Port | Description                       |
| ------------ | ---- | --------------------------------- |
| MCP Service  | 8000 | OpenSearch MCP server             |
| Expert Agent | 8003 | Legal search validation agent     |
| Main Agent   | 9111 | Task manager and orchestrator     |
| Search Agent | -    | Internal client (connects to MCP) |

## Architecture

```
Main Agent (9111)
    ├── Orchestrates tasks
    ├── Communicates with Expert Agent (8003)
    └── Routes to Search Agent
            └── Connects to MCP Service (8000)
```

## Development

For local development without Docker:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run each service in separate terminal:
cd mcp/opensearch_mcp && uv sync && uv run python main.py
cd agents/search_agent && uv sync && uv run python main.py
cd agents/expert_agent && uv sync && uv run python a2a_server.py
cd agents/main_agent && uv sync && uv run python a2a_server.py
```

## Troubleshooting

- **Build errors**: Make sure your `.env` file has `OPENAI_API_KEY`
- **Port conflicts**: Check if ports 8000, 8003, or 9111 are already in use
- **Service communication**: Services use Docker network `ferbit-network` internally
