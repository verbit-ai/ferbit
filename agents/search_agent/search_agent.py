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
response_model = init_chat_model("openai:gpt-4o", temperature=0)
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

    async def ainvoke(self, query: str, collection_id: UUID = "77ca74f6-c5c6-4505-ad57-499283826b87") -> Any:
        """Invoke the agent asynchronously"""
        logger.info(f"[AINVOKE] Starting search with query: '{query}', collection_id: {collection_id}")

        await self._initialize_if_needed()

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
Provide a comprehensive answer based on the search results.
"""

        logger.info(f"[AINVOKE] LLM Input - Search prompt: {search_prompt[:200]}...")

        messages = [HumanMessage(content=search_prompt)]
        result = await self.graph.ainvoke({"messages": messages}, config)

        final_result = result["messages"][-1].content
        logger.info(f"[AINVOKE] LLM Output - Final result: {final_result[:200]}...")
        logger.info(f"[AINVOKE] Completed search operation for query: '{query}'")

        return final_result

    async def stream(self, query: str, context_id: str = None):
        """Stream agent responses"""
        logger.info(f"[STREAM] Starting stream with query: '{query}', context_id: {context_id}")

        await self._initialize_if_needed()

        config = {"configurable": {"thread_id": context_id or str(uuid.uuid4())}}
        messages = [HumanMessage(content=query)]

        logger.info(f"[STREAM] LLM Input - Query: {query}")

        async for chunk in self.graph.astream({"messages": messages}, config):
            logger.debug(f"[STREAM] Chunk received: {str(chunk)[:100]}...")
            yield chunk

        logger.info(f"[STREAM] Completed streaming for query: '{query}'")


    async def run(self, collection_id: UUID, query: str):
        """Legacy method for backward compatibility"""
        logger.info(f"[RUN] Legacy run method called with collection_id: {collection_id}, query: '{query}'")
        result = await self.ainvoke(query, collection_id)
        logger.info(f"[RUN] Legacy run method completed")
        return result