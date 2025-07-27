import subprocess
import time
import os
import atexit
import logging
from typing import List, Dict, Any, Optional
from fastmcp import FastMCP
from opensearchpy import OpenSearch
from pydantic import BaseModel, Field

# Configure logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'opensearch_mcp.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SearchQuery(BaseModel):
    query: str = Field(description="The search query string")
    index: str = Field(default="_all", description="The index to search in")
    size: int = Field(default=10, description="Number of results to return")
    from_: int = Field(default=0, alias="from", description="Starting position for results")

class SearchResult(BaseModel):
    total_hits: int = Field(description="Total number of matching documents")
    max_score: Optional[float] = Field(description="Maximum relevance score")
    hits: List[Dict[str, Any]] = Field(description="Search result documents")
    took: int = Field(description="Time taken for search in milliseconds")

class SearchMCPServer:
    def __init__(self):
        logger.info("[INIT] Initializing SearchMCPServer")
        self.app = FastMCP("Search MCP Server")
        self.tunnel_process = None
        self.opensearch_client = None
        self.setup_tunnel()
        self.setup_opensearch_client()
        self.register_tools()
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
        logger.info("[INIT] SearchMCPServer initialization completed")
    
    def setup_tunnel(self):
        """Setup AWS SSM tunnel to OpenSearch"""
        logger.info("[TUNNEL] Setting up AWS SSM tunnel to OpenSearch...")
        print("Setting up AWS SSM tunnel to OpenSearch...")
        
        # Set AWS profile
        os.environ['AWS_PROFILE'] = 'staging'
        logger.info("[TUNNEL] AWS_PROFILE set to 'staging'")
        
        # Start SSM port forwarding session
        cmd = [
            'aws', '--region', 'eu-west-1', 'ssm', 'start-session',
            '--target', 'i-041af79ea7c7d1f02',
            '--document-name', 'AWS-StartPortForwardingSessionToRemoteHost',
            '--parameters', '{"host":["vpc-opensearch-ferret-stagging-4fp5wiub5owfti2shyjkdfrday.eu-west-1.es.amazonaws.com"],"portNumber":["443"], "localPortNumber":["9201"]}'
        ]
        
        logger.info(f"[TUNNEL] Executing SSM command: {' '.join(cmd[:4])}...")
        
        try:
            self.tunnel_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            logger.info("[TUNNEL] SSM process started, waiting 5 seconds for tunnel establishment...")
            # Wait a bit for tunnel to establish
            time.sleep(5)
            logger.info("[TUNNEL] AWS SSM tunnel established on port 9201")
            print("AWS SSM tunnel established on port 9201")
            
        except Exception as e:
            logger.error(f"[TUNNEL] Failed to setup AWS SSM tunnel: {e}")
            print(f"Failed to setup AWS SSM tunnel: {e}")
            raise
    
    def setup_opensearch_client(self):
        """Setup OpenSearch client"""
        logger.info("[OPENSEARCH] Setting up OpenSearch client...")
        
        try:
            client_config = {
                'hosts': [{'host': 'localhost', 'port': 9201}],
                'http_compress': True,
                'http_auth': None,
                'use_ssl': True,
                'verify_certs': False,
                'ssl_assert_hostname': False,
                'ssl_show_warn': False,
                'timeout': 30,
            }
            
            logger.info(f"[OPENSEARCH] Client config: {client_config}")
            
            self.opensearch_client = OpenSearch(**client_config)
            
            # Test connection
            logger.info("[OPENSEARCH] Testing connection...")
            info = self.opensearch_client.info()
            version = info['version']['number']
            logger.info(f"[OPENSEARCH] Successfully connected to OpenSearch version: {version}")
            print(f"Connected to OpenSearch: {version}")
            
        except Exception as e:
            logger.error(f"[OPENSEARCH] Failed to setup OpenSearch client: {e}")
            print(f"Failed to setup OpenSearch client: {e}")
            raise
    
    def register_tools(self):
        """Register MCP tools"""
        @self.app.tool()
        def search(query: str, index: str, size: int = 10, from_: int = 0) -> SearchResult:
            """Search OpenSearch for documents matching the query"""
            logger.info(f"[SEARCH_TOOL] Called with params - query: '{query}', index: '{index}', size: {size}, from: {from_}")
            print(f"MCP TOOL CALLED: search(query='{query}', index='{index}', size={size}, from={from_})")
            
            real_index = index + "_text"
            logger.info(f"[SEARCH_TOOL] Using real index: '{real_index}'")
            
            try:
                search_body = {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["_all", "*"]
                        }
                    },
                    "size": size,
                    "from": from_
                }
                
                logger.info(f"[SEARCH_TOOL] Search body: {search_body}")
                
                response = self.opensearch_client.search(
                    index=real_index,
                    body=search_body
                )
                
                logger.debug(f"[SEARCH_TOOL] Raw OpenSearch response: {response}")
                
                result = SearchResult(
                    total_hits=response['hits']['total']['value'] if isinstance(response['hits']['total'], dict) else response['hits']['total'],
                    max_score=response['hits']['max_score'],
                    hits=[hit for hit in response['hits']['hits']],
                    took=response['took']
                )
                
                logger.info(f"[SEARCH_TOOL] Search completed - Found {result.total_hits} hits in {result.took}ms, max_score: {result.max_score}")
                print(f"SEARCH RESULT: Found {result.total_hits} hits in {result.took}ms")
                
                # Log hit details (truncated for readability)
                for i, hit in enumerate(result.hits[:3]):  # Log first 3 hits
                    logger.info(f"[SEARCH_TOOL] Hit {i+1}: score={hit.get('_score')}, source_preview={str(hit.get('_source', {}))[:100]}...")
                
                return result
                
            except Exception as e:
                logger.error(f"[SEARCH_TOOL] Search error for query '{query}' on index '{real_index}': {e}")
                print(f"Search error: {e}")
                # Return empty result on error
                empty_result = SearchResult(
                    total_hits=0,
                    max_score=None,
                    hits=[],
                    took=0
                )
                logger.info(f"[SEARCH_TOOL] Returning empty result due to error")
                return empty_result
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("[CLEANUP] Starting cleanup process...")
        
        if self.tunnel_process:
            logger.info("[CLEANUP] Terminating AWS SSM tunnel...")
            print("Terminating AWS SSM tunnel...")
            try:
                self.tunnel_process.terminate()
                self.tunnel_process.wait(timeout=10)
                logger.info("[CLEANUP] AWS SSM tunnel terminated successfully")
            except subprocess.TimeoutExpired:
                logger.warning("[CLEANUP] Tunnel process did not terminate gracefully, forcing kill")
                self.tunnel_process.kill()
                self.tunnel_process.wait()
            except Exception as e:
                logger.error(f"[CLEANUP] Error during tunnel cleanup: {e}")
        else:
            logger.info("[CLEANUP] No tunnel process to clean up")
        
        logger.info("[CLEANUP] Cleanup completed")
    
    def run(self):
        """Run the MCP server"""
        logger.info("[SERVER] Starting MCP server on port 8000 with SSE transport...")
        
        try:
            self.app.run(transport="sse", host="0.0.0.0", port=8000)
        except KeyboardInterrupt:
            logger.info("[SERVER] Received keyboard interrupt, shutting down...")
            print("\nShutting down...")
        except Exception as e:
            logger.error(f"[SERVER] Server error: {e}")
            raise
        finally:
            logger.info("[SERVER] Server stopped, performing cleanup...")
            self.cleanup()

if __name__ == '__main__':
    logger.info("[MAIN] Starting SearchMCPServer application...")
    try:
        server = SearchMCPServer()
        server.run()
    except Exception as e:
        logger.error(f"[MAIN] Fatal error: {e}")
        raise
    finally:
        logger.info("[MAIN] Application terminated")