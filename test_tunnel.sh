#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 Testing SSM Tunnel Setup${NC}"

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

# Wait for tunnel to establish
echo -e "${YELLOW}⏳ Waiting for tunnel to establish...${NC}"
sleep 20

# Check if tunnel is working by testing the connection
max_attempts=10
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -k https://localhost:9201 --max-time 5 >/dev/null 2>&1; then
        echo -e "${GREEN}✅ SSM tunnel established and OpenSearch is reachable${NC}"
        curl -k https://localhost:9201 --max-time 5 | jq '.version.number' 2>/dev/null || echo "OpenSearch connected but jq not available"
        break
    fi
    
    attempt=$((attempt + 1))
    echo -e "${YELLOW}⏳ Tunnel test attempt $attempt/$max_attempts...${NC}"
    sleep 3
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ SSM tunnel failed to establish or OpenSearch is not reachable${NC}"
    exit 1
else
    echo -e "${GREEN}🎉 Tunnel test successful!${NC}"
fi