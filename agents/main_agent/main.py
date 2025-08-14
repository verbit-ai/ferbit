import json
import os
import logging
from typing import Dict
from uuid import uuid4

from dotenv import load_dotenv
from pydantic_ai import Agent

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams, Message, Role, TextPart, SendMessageRequest, SendStreamingMessageRequest,
)

SEARCH_AGENT_URL = os.getenv("SEARCH_AGENT_URL", "localhost:8001")
EXPERT_AGENT_URL = os.getenv("EXPERT_AGENT_URL", "localhost:8003")

# Timeout configuration for agent communication
AGENT_TIMEOUT_CONNECT = float(os.getenv("AGENT_TIMEOUT_CONNECT", "10.0"))    # 10 seconds
AGENT_TIMEOUT_READ = float(os.getenv("AGENT_TIMEOUT_READ", "120.0"))         # 2 minutes  
AGENT_TIMEOUT_WRITE = float(os.getenv("AGENT_TIMEOUT_WRITE", "10.0"))        # 10 seconds
AGENT_TIMEOUT_POOL = float(os.getenv("AGENT_TIMEOUT_POOL", "10.0"))          # 10 seconds

agent_registry: Dict[str, str] = {
    "expert_agent": f"http://{EXPERT_AGENT_URL}",
    "search_agent": f"http://{SEARCH_AGENT_URL}"
}

load_dotenv()
agent = Agent(
    "openai:gpt-4o",
    system_prompt="""
        Your name is Ferbit
        You are a manager of a team of AI agents that specializes in comprehensive information retrieval and analysis.
        
        CORE WORKFLOW - Follow this iterative process for ALL queries:
        
        1. DECOMPOSE: Break down complex queries into specific, searchable sub-queries
           - Use expert_agent to evaluate if queries are searchable and get suggestions for better queries
           - Create multiple focused queries that together address the original request
           - Prioritize specific, factual questions over general ones
        
        2. SEARCH: Execute searches for each sub-query
           - Use search_agent to find relevant information for each decomposed query
           - Search systematically through all sub-queries
           - Collect all search results before proceeding
        
        3. COMBINE: Synthesize results from all searches
           - Merge information from multiple search results
           - Identify overlaps, contradictions, and gaps
           - Create a comprehensive response addressing the original query
        
        4. VALIDATE: Check completeness using expert evaluation
           - Use expert_agent to validate if the combined results fully answer the original query
           - Identify any missing information or gaps in the response
           - Get specific suggestions for additional searches if needed
        
        5. ITERATE: Repeat if validation shows incompleteness
           - If expert_agent indicates missing information, perform additional targeted searches
           - Continue the cycle until the query is comprehensively answered
           - Maximum 2 iterations to prevent infinite loops
        
        AGENT SPECIALIZATIONS:
        - expert_agent: Query decomposition, search validation, completeness assessment
        - search_agent: Document search, information retrieval from case collections
        
        COMMUNICATION GUIDELINES:
        - Always start with expert_agent to decompose queries
        - Use search_agent for all information retrieval
        - Return to expert_agent to validate completeness
        - Provide clear, comprehensive final responses that correspond to the original query
        - Show your reasoning and methodology transparently
        - IMPRORTANT: Don't return a question to the user, just answer the query to the best of you ability in the flow mentioned.
        
        EXAMPLE WORKFLOW:
        User: "Tell me about the accident case"
        1. Send to expert_agent: "Tell me about the accident case" → Get specific searchable queries
        2. Send each query to search_agent → Collect all results  
        3. Combine results into comprehensive response
        4. Send to expert_agent for validation → Check if complete
        5. If incomplete, search for missing information and repeat
        
        Always follow this structured approach to ensure thorough, accurate responses.
        """,
)

@agent.system_prompt
async def add_available_agents(ctx) -> str:
    """
        Add the available agents to the system prompt.

        Returns:
            str: A message listing the available agents.
        """
    if not agent_registry:
        return "No agents are currently registered."

    agents_list = ", ".join(agent_registry.keys())
    return f"Available agents: {agents_list}"

@agent.tool
async def say_hello(ctx) -> str:
    return "Hello, blablabla! This is a test message from the agent."


# @agent.tool
# async def get_manning_timeline(ctx, query: str) -> str:
#     """
#     Return Manning timeline information when query contains both 'Manning' and 'Timeline'.
#
#     Args:
#         query: The user's query to check for Manning and Timeline keywords
#
#     Returns:
#         Timeline information if both keywords are present, otherwise a message indicating no match
#     """
#     query_lower = query.lower()
#     if 'manning' in query_lower and 'timeline' in query_lower:
#         return """Timeline of Events
# 1. Mr. Manning's Background
#    • For five years before the accident, Mr. Manning lived at 6126 Evergreen Way, Apartment 2, in Huntingtown, Maryland.
#    • He is self-employed as a counselor specializing in mental health and substance abuse.
#
# 2. March 13th, 2020 — Day of the Accident
# a. Pre-accident
#    • Around 5:30 p.m., Mr. Manning left his home to drive to Target in Glen Burnie to help his friend Jennifer Ryan shop.
#    • He drove a 2020 Tesla Model X with no reported mechanical issues.
#
# b. Traffic and Detour
#    • Traffic was unusually heavy due to road construction on Main Avenue.
#    • Mr. Manning took a detour via Fifth Street to avoid the construction.
#
# c. Accident Occurs
#    • On Main Avenue in Baltimore County, Mr. Manning collided with Mr. Frederick, a pedestrian.
#    • Mr. Frederick was wearing dark clothing and was not visible until Manning was about 50 feet away.
#    • Manning attempted to brake and steer right but could not avoid the collision.
#
# d. Immediate Aftermath
#    • Bystanders stopped to help.
#    • Mr. Manning briefly contacted Jennifer Ryan to reschedule their meeting.
#    • He also reported the accident to his insurance company and gave a statement to his adjuster.
#
# 3. Post-Accident Activities
#    • Manning's attorney contacted the city to obtain traffic camera footage.
#    • Legal proceedings began: the Frederick family filed a lawsuit, and Manning was questioned about the incident.
#
# ⸻
#
# This timeline reflects the actual chronological flow of background, event, and post-event details."""
#     else:
#         return "Manning timeline tool activated but query does not contain both 'Manning' and 'Timeline' keywords."

async def communicate_with_agent(agent_url: str, message: str) -> str:
    """
        Communicate with another agent using the A2A protocol.

        Args:
            agent_url: The URL of the agent to communicate with
            message: The message to send to the agent

        Returns:
            The response from the agent
    """
    # Use configurable timeout for agent communication (default 5s is too short for search operations)
    timeout = httpx.Timeout(
        connect=AGENT_TIMEOUT_CONNECT,  # Time to establish connection
        read=AGENT_TIMEOUT_READ,        # Time to read response (search operations can be slow)
        write=AGENT_TIMEOUT_WRITE,      # Time to send request
        pool=AGENT_TIMEOUT_POOL         # Time to get connection from pool
    )
    
    logger.info(f"Using timeout configuration: connect={AGENT_TIMEOUT_CONNECT}s, read={AGENT_TIMEOUT_READ}s, write={AGENT_TIMEOUT_WRITE}s, pool={AGENT_TIMEOUT_POOL}s")
    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        try:
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=agent_url,
            )
            # Fetch agent card
            logger.info("📋 Fetching Agent Card...")
            agent_card = await resolver.get_agent_card()
            logger.info(f"✅ Connected to: {agent_card.name}")
            logger.info(f"📝 Description: {agent_card.description}")
            logger.info(f"🔧 Skills: {len(agent_card.skills)}")
            logger.info(f"🔧 url: {agent_card.url}")
            for skill in agent_card.skills:
                logger.info(f"   - {skill.name}")
            client = A2AClient(
                httpx_client=httpx_client,
                agent_card=agent_card
            )

            logger.info(f"Communicating with agent at {agent_url} with message: {message}")
            user_message = Message(
                message_id=str(uuid4()),
                role=Role.user,
                parts=[TextPart(text=message)]
            )

            # Use streaming for better responsiveness with search operations
            if "search" in agent_url.lower():
                logger.info("🔄 Using streaming communication for search agent")
                
                # Create SendStreamingMessageRequest
                streaming_request = SendStreamingMessageRequest(
                    id=str(uuid4()),
                    jsonrpc="2.0",
                    method="message/stream",  
                    params=MessageSendParams(message=user_message)
                )

                # Collect streaming response
                response_parts = []
                async for chunk in client.send_message_streaming(streaming_request):
                    chunk_data = chunk.model_dump(mode='json', exclude_none=True)
                    logger.debug(f"📦 Received streaming chunk: {str(chunk_data)[:100]}...")
                    
                    # Extract text from streaming chunks
                    if 'result' in chunk_data and chunk_data['result']:
                        result = chunk_data['result']
                        if 'status' in result and 'message' in result['status']:
                            message_parts = result['status']['message'].get('parts', [])
                            for part in message_parts:
                                if part.get('kind') == 'text' and part.get('text'):
                                    response_parts.append(part['text'])
                
                # Combine all response parts
                final_response = ''.join(response_parts) if response_parts else "No streaming response received"
                logger.info(f"✅ Streaming communication completed, response length: {len(final_response)}")
                return final_response
                
            else:
                # Use regular communication for non-search agents
                logger.info("📤 Using regular communication for non-search agent")
                request = SendMessageRequest(
                    id=str(uuid4()),
                    jsonrpc="2.0",
                    method="message/send",
                    params=MessageSendParams(message=user_message)
                )
                response = await client.send_message(request)
                return str(response)

        except httpx.TimeoutException as e:
            logger.error(f"⏰ Timeout communicating with agent at {agent_url}: {e}")
            return f"Timeout communicating with agent at {agent_url}. The search operation may have taken longer than {AGENT_TIMEOUT_READ} seconds. Consider increasing AGENT_TIMEOUT_READ environment variable."
        except httpx.ConnectError as e:
            logger.error(f"🔌 Connection error communicating with agent at {agent_url}: {e}")
            return f"Could not connect to agent at {agent_url}. Please ensure the agent is running and accessible."
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"❌ Unexpected error communicating with agent at {agent_url}: {e}")
            return f"Error communicating with agent: {e}\n\nFull traceback:\n{error_details}"



@agent.tool
async def send_message_to_agent(ctx, agent_name: str, message: str) -> str:
    """
        Send a message to another agent using the A2A protocol.

        Args:
            agent_name: The registered name of the agent
            message: The message to send to the agent

        Returns:
            The response from the agent
    """
    if agent_name not in agent_registry:
        available_agents = ", ".join(agent_registry.keys()) if agent_registry else "none"
        return f"Agent '{agent_name}' not found in registry. Available agents: {available_agents}"

    agent_url = agent_registry[agent_name]
    return await communicate_with_agent(agent_url, message)




# Main entry point
async def main():
    result = await agent.run("Which agent can you trigger")
    logger.info(result.output)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

