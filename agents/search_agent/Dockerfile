FROM python:3.11-slim

# Install uv
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy all source files
COPY . .

# Install dependencies using uv
RUN uv sync --frozen

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV OPENAI_API_KEY=""
ENV MCP_SERVER_URL="http://localhost:8000/sse"

# Expose port for the search agent
EXPOSE 8001
CMD ["uv", "run", "python", "main.py"]