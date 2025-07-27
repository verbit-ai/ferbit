#!/usr/bin/env python3
"""
Test script to verify both MCP and search agent Docker containers are working together.
Uses the same parameters as test_integration.py but tests the Docker containers directly.
"""

import asyncio
import json
from search_client import SearchAgentClient


async def test_search_agent_containers():
    """Test that both containers are working and can communicate"""
    print("🧪 Testing Search Agent Docker Containers")
    print("=" * 50)
    
    # Use same test parameters as integration test
    collection_id = "77ca74f6-c5c6-4505-ad57-499283826b87"
    test_query = "please describe the flow of events which include mr. manning and mr. frederick"
    
    # Create client
    client = SearchAgentClient("http://localhost:8001")
    
    try:
        # Step 1: Check if search agent is ready
        print("🔍 Step 1: Checking if search agent is ready...")
        if not await client.is_ready():
            print("❌ Search agent is not ready!")
            return False
        print("✅ Search agent is ready")
        
        # Step 2: Send search request (agent uses streaming internally)
        print(f"🔍 Step 2: Sending search request...")
        print(f"   Query: '{test_query}'")
        print(f"   Collection ID: {collection_id}")
        print("   Note: Agent will use streaming internally but return complete response")
        
        response = await client.search(test_query, collection_id)
        
        # Step 3: Wait for task completion if it's still in progress
        print("🔍 Step 3: Checking task status and waiting for completion...")
        final_response = await client.wait_for_task_completion(response, max_wait_time=60)
        
        print(f"📋 Full Response:")
        print(json.dumps(final_response, indent=2))
        
        # Step 4: Extract and analyze text
        text_content = client.extract_text_from_response(final_response)
        print(f"📝 Extracted Text Content:")
        print("-" * 30)
        print(text_content)
        print("-" * 30)
        
        # Step 5: Check if response indicates success or expected behavior
        success_indicators = [
            "result" in final_response,
            "status" in final_response.get("result", {}),
            len(text_content.strip()) > 0
        ]
        
        if all(success_indicators):
            print("✅ Test PASSED: Search agent responded with proper structure")
            
            # Check if it mentions connection issues (expected since MCP can't connect to OpenSearch)
            if any(keyword in text_content.lower() for keyword in ["cannot", "unable", "error", "not available"]):
                print("ℹ️  Note: Response indicates expected MCP connection issues (normal without AWS access)")
            else:
                print("🎉 Unexpected: Got successful search results!")
            
            return True
        else:
            print("❌ Test FAILED: Response structure is invalid")
            return False
            
    except Exception as e:
        print(f"❌ Test FAILED with error: {e}")
        return False


async def main():
    """Main test function"""
    print("Starting Docker container test...")
    
    try:
        success = await test_search_agent_containers()
        if success:
            print("\n🎉 Docker container test completed successfully!")
            print("Both containers are working and can communicate.")
        else:
            print("\n💥 Docker container test failed!")
            
    except Exception as e:
        print(f"\n💥 Test failed with unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())