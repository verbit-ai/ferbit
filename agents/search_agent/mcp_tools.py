"""
MCP tools integration for the search agent.
This module provides LangChain-compatible tools that connect to the MCP server using the official LangChain MCP adapters.
"""

import os
import asyncio
from typing import List
from langchain_mcp_adapters.client import MultiServerMCPClient


class MCPClient:
    """MCP client wrapper for the search agent using LangChain MCP adapters"""
    
    def __init__(self, mcp_server_url: str = None):
        self.mcp_server_url = mcp_server_url or os.environ.get('MCP_SERVER_URL', 'http://127.0.0.1:8000/sse/')
        self._client = None
        self._tools = None
    
    async def get_tools(self) -> List:
        """Get MCP tools from the server using MultiServerMCPClient"""
        if self._tools is None:
            try:
                print(f"🔗 Connecting to MCP server at: {self.mcp_server_url}")
                
                # Create MCP client with SSE transport for our search server
                self._client = MultiServerMCPClient({
                    "search": {
                        "url": self.mcp_server_url,
                        "transport": "sse"
                    }
                })
                
                print("📡 Getting tools from MCP server...")
                # Get tools from the MCP server
                self._tools = await self._client.get_tools()
                print(f"🔧 Retrieved {len(self._tools)} tools from MCP server")
                
                # Log available tools
                for tool in self._tools:
                    print(f"  - {tool.name}: {tool.description}")
                
            except Exception as e:
                import traceback
                print(f"❌ Failed to connect to MCP server: {e}")
                print(f"📋 Full traceback:")
                traceback.print_exc()
                # Return empty list if connection fails
                self._tools = []
                
        return self._tools
    
    async def close(self):
        """Close the MCP client connection"""
        if self._client:
            try:
                # MultiServerMCPClient doesn't have close method, so we'll clean up manually
                if hasattr(self._client, 'close'):
                    await self._client.close()
                else:
                    # Clear the reference
                    self._client = None
            except Exception as e:
                print(f"Warning: Error closing MCP client: {e}")
            finally:
                self._client = None


# Global MCP client instance
_mcp_client = MCPClient()


async def get_search_tools() -> List:
    """Get the list of MCP-based tools for use with LangGraph"""
    return await _mcp_client.get_tools()


async def test_mcp_connection(mcp_server_url: str = None) -> bool:
    """Test if the MCP server is available and responsive"""
    try:
        test_client = MCPClient(mcp_server_url)
        tools = await test_client.get_tools()
        await test_client.close()
        
        # If we get tools back, the connection works
        return len(tools) > 0
        
    except Exception as e:
        print(f"MCP connection test failed: {e}")
        return False


async def close_mcp_client():
    """Close the global MCP client"""
    await _mcp_client.close()


if __name__ == "__main__":
    # Test the MCP tools
    async def main():
        print("🧪 Testing MCP Tools")
        print("=" * 30)
        
        # Test connection
        is_connected = await test_mcp_connection()
        print(f"MCP Connection: {'✅ Connected' if is_connected else '❌ Failed'}")
        
        if is_connected:
            # Get and display tools
            tools = await get_search_tools()
            print(f"Available tools: {[tool.name for tool in tools]}")
            
            # Test a search tool if available
            search_tools = [tool for tool in tools if 'search' in tool.name.lower()]
            if search_tools:
                search_tool = search_tools[0]
                print(f"Testing tool: {search_tool.name}")
                try:
                    # Test the tool with some sample arguments
                    result = await search_tool.ainvoke({
                        "query": "test query",
                        "index": "test_index", 
                        "size": 3
                    })
                    print(f"Search result: {result}")
                except Exception as e:
                    print(f"Tool test failed: {e}")
        
        # Cleanup
        await close_mcp_client()
    
    asyncio.run(main())