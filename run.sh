#!/bin/bash

# Make sure .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your OPENAI_API_KEY"
    echo "Example:"
    echo "OPENAI_API_KEY=sk-your-key-here"
    exit 1
fi

# Check if OPENAI_API_KEY is set in .env
if ! grep -q "OPENAI_API_KEY" .env; then
    echo "❌ Error: OPENAI_API_KEY not found in .env file!"
    echo "Please add your OpenAI API key to the .env file:"
    echo "OPENAI_API_KEY=sk-your-key-here"
    exit 1
fi

echo "🚀 Starting Ferbit services..."
echo "This will start:"
echo "  - MCP Service (http://localhost:8000)"
echo "  - Expert Agent (http://localhost:8003)"
echo "  - Main Agent (http://localhost:9111)"
echo "  - Search Agent (internal)"
echo ""

# Build and run all services
docker-compose up --build

echo "✅ All services stopped."