FROM python:3.11-slim

# Install system dependencies for AWS CLI and uv
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws

WORKDIR /app

# Copy all source files
COPY . .

# Install dependencies using uv
RUN uv sync --frozen

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_PROFILE=staging

# Expose port for MCP server
EXPOSE 8000

# Use main_no_tunnel.py as default (can be overridden with environment variables)
CMD ["uv", "run", "python", "main_no_tunnel.py"]
