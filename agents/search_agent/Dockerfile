FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
COPY uv.lock ./
RUN uv sync --frozen
COPY . .

ENV PYTHONUNBUFFERED=1
ENV OPENAI_API_KEY=""
ENV MCP_SERVER_URL="http://localhost:8000/sse"

CMD ["uv", "run", "python", "main.py"]