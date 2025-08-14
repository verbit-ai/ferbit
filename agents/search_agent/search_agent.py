import os
import uuid
import logging
from uuid import UUID
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from mcp_tools import get_search_tools
from keyword_generator import generate_legal_keywords
from rate_limiter import openai_rate_limiter


if "OPENAI_API_KEY" not in os.environ:
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Configure logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'search_agent.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize these globally
response_model = init_chat_model("openai:gpt-4o-mini", temperature=0)
memory = MemorySaver()


class SearchAgent:
    def __init__(self):
        self.response_model = response_model
        self.graph = None
        self._initialized = False

    async def _initialize_if_needed(self):
        """Initialize the agent with MCP tools if not already done"""
        if not self._initialized:
            # Get MCP-based search tools asynchronously
            search_tools = await get_search_tools()
            print(f"🔧 SearchAgent initialized with {len(search_tools)} tools")
            for tool in search_tools:
                print(f"  - {tool.name}: {tool.description}")

            # Create LangGraph agent with MCP tools
            self.graph = create_react_agent(
                self.response_model,
                tools=search_tools,
                checkpointer=memory
            )
            self._initialized = True

    async def ainvoke(self, query: str, collection_id: UUID = "5d3bcf72-d167-482d-bd1b-156ac5026c20") -> Any:
        """Invoke the agent asynchronously using streaming internally"""
        logger.info(f"[AINVOKE] Starting search with query: '{query}', collection_id: {collection_id}")

        await self._initialize_if_needed()

        collection_id = "5d3bcf72-d167-482d-bd1b-156ac5026c20"
        if collection_id is None:
            error_msg = "Error: collection_id is required for search operations. Please provide a valid collection_id."
            logger.error(f"[AINVOKE] {error_msg}")
            return error_msg

        config = {"configurable": {"thread_id": str(collection_id)}}

        # Generate extensive legal keywords for the search
        legal_keywords = await generate_legal_keywords(query)
        logger.info(f"[AINVOKE] Generated legal keywords: {legal_keywords}")
        print(f"Generated legal keywords: {legal_keywords}")

        # Enhanced prompt to instruct the agent to use the search tool with generated keywords
        search_prompt = f"""
You are a search agent with access to an OpenSearch database through the 'search' tool.
You must use the search tool to find relevant documents for the user's query.

Original user query: {query}
Generated legal keywords: {legal_keywords}
Collection/Index to search: {collection_id}

IMPORTANT: Use the search tool with index="{collection_id}" and incorporate the generated legal keywords to find relevant documents in legal depositions and case documents.
Use both the original query and the expanded keywords for comprehensive search results.
Provide only a direct answer to the user's query based on the search results without elaboration or explanation.
"""

        logger.info(f"[AINVOKE] LLM Input - Search prompt: {search_prompt[:200]}...")

        messages = [HumanMessage(content=search_prompt)]
        
        # Use streaming internally but collect all chunks for final result with rate limiting
        logger.info(f"[AINVOKE] Using internal streaming to process request")
        all_chunks = []
        
        async def run_graph_stream():
            async for chunk in self.graph.astream({"messages": messages}, config):
                yield chunk
        
        async for chunk in openai_rate_limiter.stream_with_backoff(run_graph_stream):
            logger.debug(f"[AINVOKE] Received streaming chunk: {str(chunk)[:100]}...")
            all_chunks.append(chunk)
        
        # Extract final result from the last chunk
        if all_chunks:
            final_chunk = all_chunks[-1]
            
            # Check for messages in standard format first
            if "messages" in final_chunk and final_chunk["messages"]:
                final_result = final_chunk["messages"][-1].content
            # Check for messages in agent format (LangGraph structure)
            elif "agent" in final_chunk and "messages" in final_chunk["agent"] and final_chunk["agent"]["messages"]:
                final_result = final_chunk["agent"]["messages"][-1].content
            else:
                # Check all chunks for any messages
                for chunk in all_chunks:
                    if isinstance(chunk, dict) and "messages" in chunk and chunk["messages"]:
                        final_result = chunk["messages"][-1].content
                        break
                    elif isinstance(chunk, dict) and "agent" in chunk and "messages" in chunk["agent"] and chunk["agent"]["messages"]:
                        final_result = chunk["agent"]["messages"][-1].content
                        break
                else:
                    final_result = "No response received from agent."
        else:
            final_result = "No chunks received from streaming."

        logger.info(f"[AINVOKE] LLM Output - Final result: {final_result[:200]}...")
        logger.info(f"[AINVOKE] Completed search operation for query: '{query}' using {len(all_chunks)} streaming chunks")

        return final_result

    async def stream(self, query: str, collection_id: UUID = "5d3bcf72-d167-482d-bd1b-156ac5026c20", context_id: str = None):
        """Stream agent responses"""
        logger.info(f"[STREAM] Starting stream with query: '{query}', collection_id: {collection_id}, context_id: {context_id}")

        await self._initialize_if_needed()

        collection_id = "5d3bcf72-d167-482d-bd1b-156ac5026c20"
        if collection_id is None:
            error_msg = "Error: collection_id is required for search operations. Please provide a valid collection_id."
            logger.error(f"[STREAM] {error_msg}")
            yield {"error": error_msg}
            return

        config = {"configurable": {"thread_id": context_id or str(collection_id)}}

        # Generate extensive legal keywords for the search
        legal_keywords = await generate_legal_keywords(query)
        logger.info(f"[STREAM] Generated legal keywords: {legal_keywords}")
        print(f"Generated legal keywords: {legal_keywords}")

        # Enhanced prompt to instruct the agent to use the search tool with generated keywords
        search_prompt = f"""
You are a search agent with access to an OpenSearch database through the 'search' tool.
You must use the search tool to find relevant documents for the user's query.

Original user query: {query}
Generated legal keywords: {legal_keywords}
Collection/Index to search: {collection_id}

IMPORTANT: Use the search tool with index="{collection_id}" and incorporate the generated legal keywords to find relevant documents in legal depositions and case documents.
Use both the original query and the expanded keywords for comprehensive search results.
Provide only a direct answer to the user's query based on the search results without elaboration or explanation.
"""

        logger.info(f"[STREAM] LLM Input - Search prompt: {search_prompt[:200]}...")

        messages = [HumanMessage(content=search_prompt)]

        async def run_graph_stream():
            async for chunk in self.graph.astream({"messages": messages}, config):
                yield chunk

        async for chunk in openai_rate_limiter.stream_with_backoff(run_graph_stream):
            logger.debug(f"[STREAM] Chunk received: {str(chunk)[:100]}...")
            yield chunk

        logger.info(f"[STREAM] Completed streaming for query: '{query}'")


    async def run(self, collection_id: UUID, query: str):
        """Legacy method for backward compatibility"""
        logger.info(f"[RUN] Legacy run method called with collection_id: {collection_id}, query: '{query}'")
        result = await self.ainvoke(query, collection_id)
        logger.info(f"[RUN] Legacy run method completed")
        return result