FROM python:3.11-slim

WORKDIR /app

COPY main.py .
COPY pyproject.toml .
COPY README.md .
COPY uv.lock .

RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1
ENV OPENAI_API_KEY=""
ENV MCP_SERVER_URL="http://localhost:8000/sse"

CMD ["python", "main.py"]