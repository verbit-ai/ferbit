#!/usr/bin/env python3

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Environment Variables Test:")
print("-" * 30)

# Check each environment variable
vars_to_check = [
    'OPENAI_API_KEY',
    'MCP_SERVER_URL', 
    'SEARCH_ORCHESTRATOR_URL',
    'PORT'
]

for var in vars_to_check:
    value = os.environ.get(var)
    if var == 'OPENAI_API_KEY' and value:
        # Only show first 10 characters of API key for security
        print(f"{var}: {value[:10]}...{value[-4:]} ✓")
    elif value:
        print(f"{var}: {value} ✓")
    else:
        print(f"{var}: NOT SET ✗")

print("-" * 30)

# Test loading the ExpertAgent and global agent
try:
    from main import ExpertAgent, agent
    expert = ExpertAgent()
    print("✓ ExpertAgent initialized successfully!")
    print(f"✓ Global agent created: {type(agent).__name__}")
except Exception as e:
    print(f"✗ Error initializing ExpertAgent: {e}")