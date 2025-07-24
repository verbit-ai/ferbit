#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Search Agent Services${NC}"

# Function to cleanup on exit
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    
    # Stop containers
    docker stop $(docker ps -q --filter "ancestor=opensearch-mcp-host:latest") 2>/dev/null || true
    docker stop $(docker ps -q --filter "ancestor=search-agent:latest") 2>/dev/null || true
    
    # Kill SSM tunnel
    pkill -f "aws.*ssm.*start-session" || true
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install AWS CLI first.${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity --profile staging &>/dev/null; then
    echo -e "${RED}❌ AWS credentials not configured for 'staging' profile${NC}"
    exit 1
fi

# Clean up any existing tunnels first
echo -e "${YELLOW}🧹 Cleaning up any existing tunnels...${NC}"
pkill -f "session-manager-plugin" 2>/dev/null || true
sleep 2

# Step 1: Start SSM tunnel
echo -e "${YELLOW}🔗 Starting AWS SSM tunnel...${NC}"
AWS_PROFILE=staging aws --region eu-west-1 ssm start-session \
    --target i-041af79ea7c7d1f02 \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters '{"host":["vpc-opensearch-ferret-stagging-4fp5wiub5owfti2shyjkdfrday.eu-west-1.es.amazonaws.com"],"portNumber":["443"], "localPortNumber":["9201"]}' &

# Store the SSM process PID for cleanup
SSM_PID=$!

# Wait for tunnel to establish
echo -e "${YELLOW}⏳ Waiting for tunnel to establish...${NC}"
sleep 20

# Check if tunnel is working by testing the connection
max_attempts=10
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -k https://localhost:9201 --max-time 5 >/dev/null 2>&1; then
        echo -e "${GREEN}✅ SSM tunnel established and OpenSearch is reachable${NC}"
        break
    fi
    
    attempt=$((attempt + 1))
    echo -e "${YELLOW}⏳ Tunnel test attempt $attempt/$max_attempts...${NC}"
    sleep 3
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ SSM tunnel failed to establish or OpenSearch is not reachable${NC}"
    exit 1
fi

echo -e "${GREEN}✅ SSM tunnel established on port 9201${NC}"

# Step 2: Start MCP server (use host.docker.internal to access host tunnel)
echo -e "${YELLOW}🔧 Starting MCP server...${NC}"
docker run --rm --name mcp-server -p 8000:8000 \
    -e NO_TUNNEL=true \
    -e OPENSEARCH_HOST=host.docker.internal \
    -e OPENSEARCH_PORT=9201 \
    opensearch-mcp-host:latest &

# Wait for MCP server to start
echo -e "${YELLOW}⏳ Waiting for MCP server to initialize...${NC}"
sleep 15

# Check if MCP server is running with retry logic
max_attempts=15
attempt=0
while [ $attempt -lt $max_attempts ]; do
    # Check if port 8000 is listening instead of trying SSE endpoint
    if lsof -ti:8000 >/dev/null 2>&1 || nc -z localhost 8000 2>/dev/null; then
        echo -e "${GREEN}✅ MCP server is responding${NC}"
        break
    fi
    
    attempt=$((attempt + 1))
    echo -e "${YELLOW}⏳ MCP server startup check $attempt/$max_attempts...${NC}"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ MCP server failed to start${NC}"
    echo -e "${YELLOW}📋 Checking MCP server logs...${NC}"
    docker logs mcp-server 2>/dev/null || echo "No logs available"
    exit 1
fi

echo -e "${GREEN}✅ MCP server started on port 8000${NC}"

# Step 3: Start search agent
echo -e "${YELLOW}🤖 Starting search agent...${NC}"
docker run --rm --name search-agent -p 8001:8001 \
    -e MCP_SERVER_URL=http://host.docker.internal:8000/sse \
    -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
    search-agent:latest &

# Wait for search agent to start
sleep 5

# Check if search agent is ready
if ! curl -s http://localhost:8001/.well-known/agent.json >/dev/null; then
    echo -e "${RED}❌ Search agent failed to start${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Search agent started on port 8001${NC}"

echo -e "${GREEN}🎉 All services are running successfully!${NC}"
echo -e "${YELLOW}📋 Service endpoints:${NC}"
echo -e "  • OpenSearch (via tunnel): https://localhost:9201"
echo -e "  • MCP Server: http://localhost:8000/sse"
echo -e "  • Search Agent: http://localhost:8001"
echo ""
echo -e "${YELLOW}🧪 To test the system, run:${NC}"
echo -e "  cd agents/search_agent && python test_docker_containers.py"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Keep script running
wait