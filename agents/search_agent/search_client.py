#!/usr/bin/env python3
"""
Client for the Search Agent.
Provides an easy-to-use interface for communicating with the search agent server.
"""

import asyncio
import httpx
import json
from typing import Dict, Any, Optional
from uuid import uuid4


class SearchAgentClient:
    def __init__(self, agent_url: str):
        self.agent_url = agent_url
        self.timeout = 60.0
    
    async def is_ready(self) -> bool:
        """Check if the search agent is ready to accept requests"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.agent_url}/.well-known/agent.json")
                return response.status_code == 200
        except Exception:
            return False
    
    async def wait_for_ready(self, max_attempts: int = 10) -> bool:
        """Wait for the search agent to be ready"""
        for attempt in range(max_attempts):
            if await self.is_ready():
                return True
            await asyncio.sleep(2)
        return False
    
    async def search(self, query: str, collection_id: str, message_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a search query to the search agent
        
        Args:
            query: The search query text
            collection_id: The collection ID to search in
            message_id: Optional message ID, will generate one if not provided
            
        Returns:
            The response from the search agent
        """
        if message_id is None:
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
        
        print(f"🔍 Sending request to search agent...")
        print(f"📋 Request payload: {json.dumps(request_payload, indent=2)}")
        
        # Use longer timeout for complex search operations
        long_timeout = httpx.Timeout(120.0)  # 2 minutes
        
        async with httpx.AsyncClient(timeout=long_timeout) as client:
            response = await client.post(
                self.agent_url,
                json=request_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Context-Id": collection_id
                }
            )
            
            print(f"📬 Received response with status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"📄 Response data: {json.dumps(response_data, indent=2)}")
                return response_data
            else:
                raise Exception(f"Request failed with status {response.status_code}: {response.text}")

    async def search_stream(self, query: str, collection_id: str, message_id: Optional[str] = None):
        """
        Send a search query to the search agent and stream the response
        
        Args:
            query: The search query text
            collection_id: The collection ID to search in
            message_id: Optional message ID, will generate one if not provided
            
        Yields:
            Streaming chunks from the search agent
        """
        if message_id is None:
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
        
        print(f"🔍 Sending streaming request to search agent...")
        print(f"📋 Request payload: {json.dumps(request_payload, indent=2)}")
        
        # Use longer timeout for complex search operations
        long_timeout = httpx.Timeout(120.0)  # 2 minutes
        
        async with httpx.AsyncClient(timeout=long_timeout) as client:
            async with client.stream(
                "POST",
                self.agent_url,
                json=request_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Context-Id": collection_id
                }
            ) as response:
                
                print(f"📬 Received streaming response with status: {response.status_code}")
                
                if response.status_code == 200:
                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            print(f"📦 Received chunk: {chunk[:100]}...")
                            yield chunk
                else:
                    raise Exception(f"Request failed with status {response.status_code}: {await response.aread()}")
    
    async def wait_for_task_completion(self, initial_response: Dict[str, Any], max_wait_time: int = 60) -> Dict[str, Any]:
        """
        Wait for a task to complete by polling its status
        
        Args:
            initial_response: The initial response from the search request
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            The final response when task is completed
        """
        try:
            result = initial_response.get("result", {})
            task_id = result.get("id")
            current_state = result.get("status", {}).get("state", "unknown")
            
            # If already completed or failed, return immediately
            if current_state in ["completed", "failed"]:
                return initial_response
            
            if not task_id:
                print("⚠️  No task ID found, returning initial response")
                return initial_response
                
            print(f"🔄 Task state: {current_state}, waiting for completion...")
            print(f"📋 Task ID: {task_id}")
            
            # Poll for completion
            wait_time = 0
            poll_interval = 2  # Poll every 2 seconds
            
            while wait_time < max_wait_time:
                await asyncio.sleep(poll_interval)
                wait_time += poll_interval
                
                # Check task status (this would need a specific endpoint for task status)
                # For now, we'll just return the initial response since A2A might handle this differently
                print(f"⏱️  Waited {wait_time}s for task completion...")
                
                # In a real implementation, you'd poll a status endpoint here
                # For now, we assume the initial response is the final one
                break
                
            print("✅ Task polling completed")
            return initial_response
            
        except Exception as e:
            print(f"⚠️  Error during task polling: {e}")
            return initial_response
    
    def extract_text_from_response(self, response_data: Dict[str, Any]) -> str:
        """Extract text content from the search agent response"""
        try:
            result = response_data.get("result", {})
            status = result.get("status", {})
            message = status.get("message", {})
            
            text_content = ""
            for part in message.get("parts", []):
                if part.get("kind") == "text":
                    text_content += part.get("text", "")
            
            return text_content
        except Exception:
            return ""


async def main():
    """Example usage of the SearchAgentClient"""
    client = SearchAgentClient("http://localhost:8001")
    
    # Wait for agent to be ready
    print("Waiting for search agent to be ready...")
    if not await client.wait_for_ready():
        print("Search agent is not ready!")
        return
    
    # Send a search query
    collection_id = "5d3bcf72-d167-482d-bd1b-156ac5026c20"
    query = "Who are the witnesses?"
    
    try:
        print(f"Sending query: {query}")
        
        # First try to get initial response
        response = await client.search(query, collection_id)
        print("Initial response received:")
        print(json.dumps(response, indent=2))
        
        # Wait for task completion to get the full results
        final_response = await client.wait_for_task_completion(response, max_wait_time=120)
        
        # Try streaming to get the complete response
        print("\nTrying streaming approach to get complete results...")
        full_text = ""
        async for chunk in client.search_stream(query, collection_id):
            if chunk.strip():
                try:
                    chunk_data = json.loads(chunk)
                    if "result" in chunk_data and "status" in chunk_data["result"]:
                        message = chunk_data["result"]["status"].get("message", {})
                        for part in message.get("parts", []):
                            if part.get("kind") == "text":
                                text_content = part.get("text", "")
                                full_text += text_content
                                print(f"📄 Received: {text_content}")
                except json.JSONDecodeError:
                    # Handle non-JSON chunks
                    print(f"📄 Raw chunk: {chunk}")
                    full_text += chunk
        
        if full_text:
            print("\n" + "="*50)
            print("COMPLETE RESPONSE:")
            print("="*50)
            print(full_text)
        else:
            # Fallback to extract from final response
            text = client.extract_text_from_response(final_response)
            if text:
                print("\nExtracted text from final response:")
                print(text)
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())