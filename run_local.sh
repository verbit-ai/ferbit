#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Ferbit services (Local Mode)...${NC}"
echo "This will start:"
echo "  - MCP Service (http://localhost:8000) -> Local OpenSearch"
echo "  - Search Agent (http://localhost:8001)"
echo "  - Expert Agent (http://localhost:8003)"
echo "  - Main Agent (http://localhost:9111)"
echo ""

# Check if OpenAI API key is provided
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}❌ Error: OPENAI_API_KEY environment variable is required!${NC}"
    echo "Please set it by running:"
    echo "export OPENAI_API_KEY=add_api_key"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    
    # Kill background processes
    if [ -n "$MCP_PID" ]; then
        kill $MCP_PID 2>/dev/null || true
    fi
    if [ -n "$SEARCH_AGENT_PID" ]; then
        kill $SEARCH_AGENT_PID 2>/dev/null || true
    fi
    if [ -n "$EXPERT_AGENT_PID" ]; then
        kill $EXPERT_AGENT_PID 2>/dev/null || true
    fi
    if [ -n "$MAIN_AGENT_PID" ]; then
        kill $MAIN_AGENT_PID 2>/dev/null || true
    fi
    
    # Kill any processes using ports 8000, 8001, 8003, 9111
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:8001 | xargs kill -9 2>/dev/null || true
    lsof -ti:8003 | xargs kill -9 2>/dev/null || true
    lsof -ti:9111 | xargs kill -9 2>/dev/null || true
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Clean up any existing services first
echo -e "${YELLOW}🧹 Cleaning up any existing services...${NC}"
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:8003 | xargs kill -9 2>/dev/null || true
lsof -ti:9111 | xargs kill -9 2>/dev/null || true

sleep 2

# Check if local OpenSearch is running
echo -e "${YELLOW}🔍 Checking local OpenSearch...${NC}"
if ! curl -s http://localhost:9200 >/dev/null 2>&1; then
    echo -e "${RED}❌ Local OpenSearch not found on port 9200!${NC}"
    echo "Please make sure OpenSearch is running locally."
    echo "You should see OpenSearch containers running with: docker ps"
    exit 1
fi

echo -e "${GREEN}✅ Local OpenSearch found on port 9200${NC}"

# Step 1: Start MCP server (no tunnel version)
echo -e "${YELLOW}🔧 Starting MCP server (local mode)...${NC}"
cd mcp/opensearch_mcp

# Activate virtual environment and start MCP server
source ../../venv/bin/activate
USE_SSL=false OPENSEARCH_PORT=9200 python main_no_tunnel.py > ../../mcp_server.log 2>&1 &
MCP_PID=$!

cd ../../

# Wait for MCP server to start
echo -e "${YELLOW}⏳ Waiting for MCP server to initialize...${NC}"
sleep 5

# Check if MCP server is working
max_attempts=10
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8000/sse >/dev/null 2>&1; then
        echo -e "${GREEN}✅ MCP server started successfully${NC}"
        break
    fi
    
    attempt=$((attempt + 1))
    echo -e "${YELLOW}⏳ MCP server startup attempt $attempt/$max_attempts...${NC}"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ MCP server failed to start${NC}"
    echo "Check mcp_server.log for details"
    exit 1
fi

# Step 2: Start Search Agent
echo -e "${YELLOW}🤖 Starting Search Agent...${NC}"
cd agents/search_agent

# Activate virtual environment and start search agent
source ../../venv/bin/activate
OPENAI_API_KEY=$OPENAI_API_KEY MCP_SERVER_URL=http://localhost:8000/sse python main.py > ../../search_agent.log 2>&1 &
SEARCH_AGENT_PID=$!

cd ../../

# Wait for Search Agent to start
echo -e "${YELLOW}⏳ Waiting for Search Agent to initialize...${NC}"
sleep 5

# Check if Search Agent is working
max_attempts=10
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8001/.well-known/agent.json >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Search Agent started successfully${NC}"
        break
    fi
    
    attempt=$((attempt + 1))
    echo -e "${YELLOW}⏳ Search Agent startup attempt $attempt/$max_attempts...${NC}"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ Search Agent failed to start${NC}"
    echo "Check search_agent.log for details"
    exit 1
fi

# Step 3: Start Expert Agent
echo -e "${YELLOW}🎓 Starting Expert Agent...${NC}"
cd agents/expert_agent

# Activate virtual environment and start expert agent
source ../../venv/bin/activate
OPENAI_API_KEY=$OPENAI_API_KEY python a2a_server.py > ../../expert_agent.log 2>&1 &
EXPERT_AGENT_PID=$!

cd ../../

# Wait for Expert Agent to start
echo -e "${YELLOW}⏳ Waiting for Expert Agent to initialize...${NC}"
sleep 5

# Check if Expert Agent is working
max_attempts=10
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8003/.well-known/agent.json >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Expert Agent started successfully${NC}"
        break
    fi
    
    attempt=$((attempt + 1))
    echo -e "${YELLOW}⏳ Expert Agent startup attempt $attempt/$max_attempts...${NC}"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ Expert Agent failed to start${NC}"
    echo "Check expert_agent.log for details"
    exit 1
fi

# Step 4: Start Main Agent
echo -e "${YELLOW}🎯 Starting Main Agent...${NC}"
cd agents/main_agent

# Activate virtual environment and start main agent
source ../../venv/bin/activate
OPENAI_API_KEY=$OPENAI_API_KEY SEARCH_AGENT_URL=127.0.0.1:8001 EXPERT_AGENT_URL=127.0.0.1:8003 python a2a_server.py > ../../main_agent.log 2>&1 &
MAIN_AGENT_PID=$!

cd ../../

# Wait for Main Agent to start
echo -e "${YELLOW}⏳ Waiting for Main Agent to initialize...${NC}"
sleep 5

# Check if Main Agent is working
max_attempts=10
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:9111/.well-known/agent.json >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Main Agent started successfully${NC}"
        break
    fi
    
    attempt=$((attempt + 1))
    echo -e "${YELLOW}⏳ Main Agent startup attempt $attempt/$max_attempts...${NC}"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ Main Agent failed to start${NC}"
    echo "Check main_agent.log for details"
    exit 1
fi

echo -e "${GREEN}🎉 All services started successfully!${NC}"
echo -e "${YELLOW}📋 Service endpoints:${NC}"
echo -e "  • Local OpenSearch: http://localhost:9200"
echo -e "  • MCP Server: http://localhost:8000/sse"
echo -e "  • Search Agent: http://localhost:8001"
echo -e "  • Expert Agent: http://localhost:8003"
echo -e "  • Main Agent: http://localhost:9111"
echo ""
echo -e "${YELLOW}🧪 To test the system, run:${NC}"
echo -e "  cd agents/search_agent && python interactive_search_client.py"
echo -e "  cd agents/main_agent && python interactive_client.py"
echo ""
echo -e "${YELLOW}📋 Logs:${NC}"
echo -e "  • MCP Server: tail -f mcp_server.log"
echo -e "  • Search Agent: tail -f search_agent.log"
echo -e "  • Expert Agent: tail -f expert_agent.log"
echo -e "  • Main Agent: tail -f main_agent.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Keep the script running and show logs
echo -e "${YELLOW}📄 Showing live logs (Ctrl+C to stop):${NC}"
echo ""

# Show logs from all services
tail -f mcp_server.log search_agent.log expert_agent.log main_agent.log 2>/dev/null || {
    echo "Waiting for logs to be available..."
    sleep 5
    tail -f mcp_server.log search_agent.log expert_agent.log main_agent.log 2>/dev/null || {
        echo "Services are running in background"
        echo "Use individual log commands to view logs"
        
        # Just keep script running and monitor all services
        while true; do
            sleep 5
            # Check if services are still running
            if ! kill -0 $MCP_PID 2>/dev/null; then
                echo -e "${RED}❌ MCP server has stopped${NC}"
                break
            fi
            if ! kill -0 $SEARCH_AGENT_PID 2>/dev/null; then
                echo -e "${RED}❌ Search agent has stopped${NC}"
                break
            fi
            if ! kill -0 $EXPERT_AGENT_PID 2>/dev/null; then
                echo -e "${RED}❌ Expert agent has stopped${NC}"
                break
            fi
            if ! kill -0 $MAIN_AGENT_PID 2>/dev/null; then
                echo -e "${RED}❌ Main agent has stopped${NC}"
                break
            fi
        done
    }
}