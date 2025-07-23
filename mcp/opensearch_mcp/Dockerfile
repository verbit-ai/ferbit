FROM python:3.11-slim
WORKDIR /app
COPY main.py pyproject.toml uv.lock ./
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["python", "main.py"]