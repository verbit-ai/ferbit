#!/usr/bin/env python3
"""
Interactive client for the Search Agent.
Allows users to ask questions and get streaming responses in a conversational format.
"""

import asyncio
import httpx
import json
import sys
from typing import Dict, Any, Optional
from uuid import uuid4


class InteractiveSearchClient:
    def __init__(self, agent_url: str = "http://localhost:8001", collection_id: str = "5d3bcf72-d167-482d-bd1b-156ac5026c20"):
        self.agent_url = agent_url
        self.collection_id = collection_id
        self.timeout = httpx.Timeout(120.0)  # 2 minutes
    
    async def is_ready(self) -> bool:
        """Check if the search agent is ready to accept requests"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.agent_url}/.well-known/agent.json")
                return response.status_code == 200
        except Exception:
            return False
    
    async def wait_for_ready(self, max_attempts: int = 5) -> bool:
        """Wait for the search agent to be ready"""
        print("🔌 Connecting to search agent...")
        for attempt in range(max_attempts):
            if await self.is_ready():
                return True
            if attempt < max_attempts - 1:  # Don't print on last attempt
                print(f"⏳ Attempt {attempt + 1}/{max_attempts}: Agent not ready yet, retrying...")
                await asyncio.sleep(2)
        return False
    
    async def send_query_streaming(self, query: str):
        """Send a query and process streaming response"""
        message_id = str(uuid4())
        
        request_payload = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "message/stream",
            "params": {
                "message": {
                    "message_id": message_id,
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": query
                        }
                    ],
                    "kind": "message"
                }
            }
        }
        
        response_text = ""
        chunk_count = 0
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    self.agent_url,
                    json=request_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Context-Id": self.collection_id
                    }
                ) as response:
                    
                    if response.status_code != 200:
                        print(f"❌ Error: Request failed with status {response.status_code}")
                        error_text = await response.aread()
                        print(f"Error details: {error_text.decode()}")
                        return ""
                    
                    print("📥 ", end="", flush=True)  # Start response indicator
                    
                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            chunk_count += 1
                            try:
                                chunk_data = json.loads(chunk)
                                if "result" in chunk_data and "status" in chunk_data["result"]:
                                    message = chunk_data["result"]["status"].get("message", {})
                                    for part in message.get("parts", []):
                                        if part.get("kind") == "text":
                                            text_content = part.get("text", "")
                                            if text_content:
                                                print(text_content, end="", flush=True)
                                                response_text += text_content
                            except json.JSONDecodeError:
                                # Handle non-JSON chunks (shouldn't happen but just in case)
                                if chunk.strip():
                                    print(chunk, end="", flush=True)
                                    response_text += chunk
        
        except asyncio.TimeoutError:
            print("\n⏰ Request timed out. The search may be taking longer than expected.")
            return response_text
        except Exception as e:
            print(f"\n❌ Error during request: {e}")
            return response_text
        
        # If no streaming content, try regular request
        if not response_text.strip():
            print("🔄 No streaming content, trying regular request...")
            response_text = await self.send_query_regular(query)
        
        return response_text
    
    async def send_query_regular(self, query: str) -> str:
        """Fallback to regular request if streaming doesn't work"""
        message_id = str(uuid4())
        
        request_payload = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "message_id": message_id,
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": query
                        }
                    ],
                    "kind": "message"
                }
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.agent_url,
                    json=request_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Context-Id": self.collection_id
                    }
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Extract text from response
                    result = response_data.get("result", {})
                    status = result.get("status", {})
                    message = status.get("message", {})
                    
                    text_content = ""
                    for part in message.get("parts", []):
                        if part.get("kind") == "text":
                            text_content += part.get("text", "")
                    
                    if text_content:
                        print(text_content, end="", flush=True)
                    
                    return text_content
                else:
                    print(f"❌ Request failed with status {response.status_code}")
                    return ""
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return ""


async def main():
    """Main interactive loop"""
    print("🔍 Interactive Search Agent Client")
    print("=" * 60)
    print("💬 Ask questions and get search results from OpenSearch")
    print("💡 Commands: 'quit', 'exit', or Ctrl+C to stop")
    print("🔄 The agent will search through legal documents and provide relevant information")
    print("=" * 60)
    print()
    
    # You can change the collection_id here if needed
    client = InteractiveSearchClient(
        agent_url="http://localhost:8001",
        collection_id="77ca74f6-c5c6-4505-ad57-499283826b87"  # Default collection ID
    )
    
    # Check if agent is ready
    if not await client.wait_for_ready():
        print("❌ Search agent is not ready!")
        print("🔧 Make sure the search agent is running with: python main.py")
        return
    
    print("✅ Connected to search agent")
    print(f"📋 Using collection ID: {client.collection_id}")
    print()
    
    conversation_count = 0
    
    try:
        while True:
            try:
                # Get user input
                if conversation_count == 0:
                    prompt = "🔍 Your search question: "
                else:
                    prompt = "🔍 Ask another question (or 'quit'): "
                
                user_input = input(prompt).strip()
                
                # Check for exit commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    print("⚠️  Please enter a question.")
                    continue
                
                conversation_count += 1
                print(f"\n🌊 Search Response #{conversation_count}:")
                
                # Send query and get streaming response
                response_text = await client.send_query_streaming(user_input)
                
                # Finalize response display
                if not response_text.strip():
                    print("(No response received)")
                
                print(f"\n{'─' * 60}")
                print(f"📊 Search completed ({len(response_text)} characters)")
                print()
                
            except KeyboardInterrupt:
                print("\n\n⏹️  Interrupted by user")
                break
            except EOFError:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error processing request: {e}")
                print("🔧 You can try again with a different question.")
                continue
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted during setup")
    
    print("✨ Session ended")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)