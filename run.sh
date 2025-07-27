#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Make sure .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found!${NC}"
    echo "Please create a .env file with your OPENAI_API_KEY"
    echo "Example:"
    echo "OPENAI_API_KEY=sk-your-key-here"
    exit 1
fi

# Check if OPENAI_API_KEY is set in .env
if ! grep -q "OPENAI_API_KEY" .env; then
    echo -e "${RED}❌ Error: OPENAI_API_KEY not found in .env file!${NC}"
    echo "Please add your OpenAI API key to the .env file:"
    echo "OPENAI_API_KEY=sk-your-key-here"
    exit 1
fi

# Load environment variables
source .env

echo -e "${GREEN}🚀 Starting Ferbit services...${NC}"
echo "This will start:"
echo "  - MCP Service (http://localhost:8000)"
echo "  - Expert Agent (http://localhost:8003)"
echo "  - Main Agent (http://localhost:9111)"
echo "  - Search Agent (http://localhost:8001)"
echo ""

# Function to cleanup on exit
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    
    # Stop Docker Compose services
    docker-compose down 2>/dev/null || true
    
    # Stop individual containers
    docker stop $(docker ps -q --filter "ancestor=ferbit-opensearch-mcp:latest") 2>/dev/null || true
    docker stop $(docker ps -q --filter "ancestor=ferbit-search-agent:latest") 2>/dev/null || true
    docker stop $(docker ps -q --filter "ancestor=ferbit-main-agent:latest") 2>/dev/null || true
    docker stop $(docker ps -q --filter "ancestor=ferbit-expert-agent:latest") 2>/dev/null || true
    
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
if ! aws sts get-caller-identity --profile verbit-staging &>/dev/null; then
    echo -e "${RED}❌ AWS credentials not configured for 'verbit-staging' profile${NC}"
    exit 1
fi

# Clean up any existing tunnels and containers first
echo -e "${YELLOW}🧹 Cleaning up any existing services...${NC}"
pkill -f "session-manager-plugin" 2>/dev/null || true

# Stop Docker Compose services first (this includes opensearch-mcp)
docker-compose down 2>/dev/null || true

# Stop and remove any existing individual containers
docker stop mcp-server ferbit-search-agent 2>/dev/null || true
docker rm mcp-server ferbit-search-agent 2>/dev/null || true

# Kill any processes using ports 8000, 8001, 8003, 9111
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:8003 | xargs kill -9 2>/dev/null || true
lsof -ti:9111 | xargs kill -9 2>/dev/null || true

sleep 3

# Step 1: Start SSM tunnel
echo -e "${YELLOW}🔗 Starting AWS SSM tunnel...${NC}"
AWS_PROFILE=verbit-staging aws --region eu-west-1 ssm start-session \
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

# Step 2: Start Docker Compose services (includes MCP server, Expert Agent, Main Agent, and Search Agent)
echo -e "${YELLOW}🐳 Starting Docker Compose services...${NC}"

echo -e "${GREEN}🎉 All services starting successfully!${NC}"
echo -e "${YELLOW}📋 Service endpoints:${NC}"
echo -e "  • OpenSearch (via tunnel): https://localhost:9201"
echo -e "  • MCP Server: http://localhost:8000/sse"
echo -e "  • Search Agent: http://localhost:8001"
echo -e "  • Expert Agent: http://localhost:8003"
echo -e "  • Main Agent: http://localhost:9111"
echo ""
echo -e "${YELLOW}🧪 To test the system, run:${NC}"
echo -e "  cd agents/search_agent && python test_docker_containers.py"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Start services with logs visible (not detached)
docker-compose up --build