#!/usr/bin/env python3
"""
Integration test for the Search Agent with MCP server.
Tests the full flow from search agent through MCP to OpenSearch.
"""

import asyncio
import subprocess
import time
import os
import signal
import httpx
import json
from uuid import UUID
from typing import Optional, Dict, Any


class TestRunner:
    def __init__(self):
        self.mcp_process: Optional[subprocess.Popen] = None
        self.agent_process: Optional[subprocess.Popen] = None
        self.test_collection_id = "77ca74f6-c5c6-4505-ad57-499283826b87"
        self.test_query = "please describe the flow of events which include mr. manning and mr. frederick"

    async def start_mcp_server(self):
        """Start the MCP server in the background"""
        print("Starting MCP server...")
        
        # Change to MCP directory and start server
        mcp_dir = "../../mcp/opensearch_mcp"
        
        env = os.environ.copy()
        env['AWS_PROFILE'] = 'staging'
        
        self.mcp_process = subprocess.Popen(
            ["python", "main.py"],
            cwd=mcp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Wait for MCP server to start
        print("Waiting for MCP server to initialize...")
        await asyncio.sleep(10)  # Give time for tunnel and server to start
        
        # Check if process is still running
        if self.mcp_process.poll() is not None:
            stdout, stderr = self.mcp_process.communicate()
            print(f"MCP server failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            raise RuntimeError("MCP server failed to start")
        
        print("MCP server started successfully")
    
    async def start_search_agent(self):
        """Start the search agent server in the background"""
        print("Starting Search Agent server...")
        
        # Change to search agent directory and start server
        agent_dir = "."
        
        env = os.environ.copy()
        env['MCP_SERVER_URL'] = 'http://localhost:8000/sse'
        
        # Ensure OPENAI_API_KEY is set
        if 'OPENAI_API_KEY' not in env:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable is required for the search agent.\n"
                "Please set it by running: export OPENAI_API_KEY='your-api-key-here'"
            )
        
        self.agent_process = subprocess.Popen(
            ["python", "main.py"],
            cwd=agent_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Wait for search agent to start
        print("Waiting for Search Agent server to start...")
        await asyncio.sleep(5)
        
        # Check if process is still running
        if self.agent_process.poll() is not None:
            stdout, stderr = self.agent_process.communicate()
            print(f"Search Agent server failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            raise RuntimeError("Search Agent server failed to start")
        
        print("Search Agent server started successfully")
    
    async def wait_for_agent_ready(self, max_attempts: int = 10):
        """Wait for the search agent to be ready to accept requests"""
        print("Waiting for Search Agent to be ready...")
        
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:8001/.well-known/agent.json")
                    if response.status_code == 200:
                        print("Search Agent is ready!")
                        return True
            except Exception as e:
                print(f"Attempt {attempt + 1}: Agent not ready yet ({e})")
                await asyncio.sleep(2)
        
        return False
    
    async def send_search_request(self) -> Dict[str, Any]:
        """Send a search request to the search agent"""
        print(f"Sending search request: '{self.test_query}' for collection '{self.test_collection_id}'")
        
        # Create A2A request payload
        request_payload = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "message/send",
            "params": {
                "message": {
                    "message_id": "msg-1",
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": self.test_query
                        }
                    ],
                    "kind": "message"
                }
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8001/",
                json=request_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Context-Id": self.test_collection_id
                }
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"Response data: {json.dumps(response_data, indent=2)}")
                return response_data
            else:
                print(f"Request failed with status {response.status_code}")
                print(f"Response text: {response.text}")
                return {}
    
    def check_opensearch_results(self, response_data: Dict[str, Any]) -> bool:
        """Check if the response contains results from OpenSearch"""
        try:
            # Check if we got a valid A2A response
            if "result" not in response_data:
                print("❌ No 'result' field in response")
                return False
            
            result = response_data["result"]
            
            # Check if there's a status and message in the result
            if "status" not in result:
                print("❌ No 'status' field in result")
                return False
            
            status = result["status"]
            
            # Check if the task failed
            if status.get("state") == "failed":
                print("❌ Task failed - likely due to MCP connection or other error")
                return False
            
            if "message" not in status:
                print("❌ No 'message' field in status")
                return False
            
            message = status["message"]
            
            # Extract text content from message parts
            text_content = ""
            if "parts" in message:
                for part in message["parts"]:
                    if part.get("kind") == "text":
                        text_content += part.get("text", "")
            
            print(f"Response text: {text_content}")
            
            # Check for indicators that OpenSearch was queried successfully
            successful_search_indicators = [
                "found",
                "results",
                "documents",
                "hits",
                "manning"  # Should mention the query term
            ]
            
            # Check for indicators that agent tried to search but couldn't connect
            connection_error_indicators = [
                "unable to perform searches",
                "do not have the capability",
                "cannot access",
                "databases",
                "external databases"
            ]
            
            text_lower = text_content.lower()
            found_success = [indicator for indicator in successful_search_indicators if indicator in text_lower]
            found_error = [indicator for indicator in connection_error_indicators if indicator in text_lower]
            
            if found_success:
                print(f"✅ Found successful OpenSearch indicators: {found_success}")
                return True
            elif found_error:
                print(f"⚠️  Agent responded but couldn't connect to OpenSearch: {found_error}")
                print("This indicates the agent is working but MCP connection failed")
                return False
            else:
                print("❌ No OpenSearch indicators found in response")
                return False
                
        except Exception as e:
            print(f"❌ Error checking results: {e}")
            return False
    
    def cleanup(self):
        """Clean up running processes"""
        print("Cleaning up processes...")
        
        if self.agent_process:
            print("Terminating Search Agent server...")
            self.agent_process.terminate()
            try:
                self.agent_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.agent_process.kill()
        
        if self.mcp_process:
            print("Terminating MCP server...")
            self.mcp_process.terminate()
            try:
                self.mcp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.mcp_process.kill()
        
        print("Cleanup completed")
    
    async def run_test(self):
        """Run the complete integration test"""
        print("🚀 Starting Search Agent Integration Test")
        print("=" * 50)
        
        try:
            # Start MCP server
            await self.start_mcp_server()
            
            # Start search agent
            await self.start_search_agent()
            
            # Wait for agent to be ready
            if not await self.wait_for_agent_ready():
                raise RuntimeError("Search Agent failed to become ready")
            
            # Send search request
            response_data = await self.send_search_request()
            
            # Check results
            success = self.check_opensearch_results(response_data)
            
            print("=" * 50)
            if success:
                print("✅ Integration test PASSED!")
                print("The Search Agent successfully:")
                print("  - Received the query")
                print("  - Connected to MCP server") 
                print("  - Queried OpenSearch")
                print("  - Returned relevant results")
            else:
                print("❌ Integration test FAILED!")
                print("The test did not find evidence of successful OpenSearch integration")
            
            return success
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return False
        
        finally:
            self.cleanup()


async def main():
    """Main test function"""
    test_runner = TestRunner()
    
    try:
        success = await test_runner.run_test()
        exit_code = 0 if success else 1
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        exit_code = 1
    except Exception as e:
        print(f"❌ Test failed with unexpected error: {e}")
        exit_code = 1
    finally:
        test_runner.cleanup()
    
    exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())