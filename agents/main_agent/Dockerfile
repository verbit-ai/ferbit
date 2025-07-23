FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv pip install --no-cache-dir .
COPY . .
CMD ["python", "a2a_server.py"]