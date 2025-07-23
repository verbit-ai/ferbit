"""
Test client for the AI Agent Task Manager A2A Agent
"""
import asyncio
import json
import aiohttp
from typing import Dict, Any


class A2AClient:

    def __init__(self, base_url: str = "http://localhost:9111"):
        self.base_url = base_url
    
    async def get_agent_card(self) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/.well-known/agent.json") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to get agent card: {response.status}")
    
    async def test_connection(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/.well-known/agent.json", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except Exception:
            return False

    async def send_message(self, message: str) -> str:
        async with httpx.AsyncClient() as httpx_client:
            # Initialize A2ACardResolver
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=base_url,
                # agent_card_path uses default, extended_agent_card_path also uses default
            )


async def main():
    client = A2AClient()
    
    print("Testing AI Agent Task Manager A2A Agent")
    print("=" * 50)
    
    try:
        print("🔌 Testing server connection...")
        if not await client.test_connection():
            print("Server is not running on http://localhost:9111")
            print("Please start the server first by running: python a2a_server.py")
            return
        print("✅ Server is running")
        print()
        
        print("📋 Fetching Agent Card...")
        agent_card = await client.get_agent_card()
        print(f"✅ Agent Name: {agent_card['name']}")
        print(f"✅ Agent Description: {agent_card['description']}")
        print(f"✅ Available Skills: {len(agent_card['skills'])}")
        for skill in agent_card['skills']:
            print(f"   - {skill['name']}: {skill['description']}")
        print()
        
        print("💬 Testing message/send - asking about capabilities...")
        question = "What agents are available and what can they do?"
        print(f"Request: {question}")
        response = await client.send_message(question)
        print(f"Response: {response}")
        print()
        
        # Test 3: Task assignment question
        print("💬 Testing message/send - task assignment...")
        question = "Which agent can handle LinkedIn profile scraping?"
        print(f"Request: {question}")
        response = await client.send_message(question)
        print(f"Response: {response}")
        print()
        
        # Test 4: GitHub task assignment
        print("💬 Testing message/send - GitHub task...")
        question = "Assign this task to the most suitable agent: I need to analyze GitHub repositories"
        print(f"Request: {question}")
        response = await client.send_message(question)
        print(f"Response: {response}")
        print()
        
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())