import os
from typing import Dict
from uuid import uuid4

from dotenv import load_dotenv
from pydantic_ai import Agent

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams, Message, Role, TextPart, SendMessageRequest,
)

SEARCH_AGENT_URL = os.getenv("SEARCH_AGENT_URL", "localhost:8001")
EXPERT_AGENT_URL = os.getenv("EXPERT_AGENT_URL", "localhost:8003")

agent_registry: Dict[str, str] = {
    "expert_agent": f"http://{EXPERT_AGENT_URL}",
    "search_agent": f"http://{SEARCH_AGENT_URL}"
}

load_dotenv()
agent = Agent(
    "openai:gpt-4o",
    system_prompt="""
        Your name is Ferbit
        You are a manager of a team of AI agents.
        Your task is to assign tasks to the agents based on their capabilities.
        You will receive a task description and a list of agents with their capabilities.

        You will analyze the task and assign it to the most suitable agent.
        If no agent is suitable, you will try to provide a solution to the task by yourself.
        Always provide a clear and concise response.
        If you need to ask for more information, do so in a clear and concise manner.

        You talk to the agents using the A2A protocol.
        The agents will respond with their results.

        The idea is to use the agents to solve complex tasks by breaking them down into smaller tasks and assigning them to the agents.

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


@agent.tool
async def get_manning_timeline(ctx, query: str) -> str:
    """
    Return Manning timeline information when query contains both 'Manning' and 'Timeline'.

    Args:
        query: The user's query to check for Manning and Timeline keywords

    Returns:
        Timeline information if both keywords are present, otherwise a message indicating no match
    """
    query_lower = query.lower()
    if 'manning' in query_lower and 'timeline' in query_lower:
        return """Timeline of Events
1. Mr. Manning's Background
   • For five years before the accident, Mr. Manning lived at 6126 Evergreen Way, Apartment 2, in Huntingtown, Maryland.
   • He is self-employed as a counselor specializing in mental health and substance abuse.

2. March 13th, 2020 — Day of the Accident
a. Pre-accident
   • Around 5:30 p.m., Mr. Manning left his home to drive to Target in Glen Burnie to help his friend Jennifer Ryan shop.
   • He drove a 2020 Tesla Model X with no reported mechanical issues.

b. Traffic and Detour
   • Traffic was unusually heavy due to road construction on Main Avenue.
   • Mr. Manning took a detour via Fifth Street to avoid the construction.

c. Accident Occurs
   • On Main Avenue in Baltimore County, Mr. Manning collided with Mr. Frederick, a pedestrian.
   • Mr. Frederick was wearing dark clothing and was not visible until Manning was about 50 feet away.
   • Manning attempted to brake and steer right but could not avoid the collision.

d. Immediate Aftermath
   • Bystanders stopped to help.
   • Mr. Manning briefly contacted Jennifer Ryan to reschedule their meeting.
   • He also reported the accident to his insurance company and gave a statement to his adjuster.

3. Post-Accident Activities
   • Manning's attorney contacted the city to obtain traffic camera footage.
   • Legal proceedings began: the Frederick family filed a lawsuit, and Manning was questioned about the incident.

⸻

This timeline reflects the actual chronological flow of background, event, and post-event details."""
    else:
        return "Manning timeline tool activated but query does not contain both 'Manning' and 'Timeline' keywords."


async def communicate_with_agent(agent_url: str, message: str) -> str:
    """
        Communicate with another agent using the A2A protocol.

        Args:
            agent_url: The URL of the agent to communicate with
            message: The message to send to the agent

        Returns:
            The response from the agent
    """
    async with httpx.AsyncClient() as httpx_client:
        try:
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=agent_url,
            )
            agent_card = await resolver.get_agent_card()
            client = A2AClient(
                httpx_client=httpx_client,
                agent_card=agent_card
            )

            # Format message as JSON for localhost:8003 agents
            if EXPERT_AGENT_URL in agent_url:
                import json
                formatted_message = json.dumps({"input_query": message})
            else:
                formatted_message = message

            print(f"Communicating with agent at {agent_url} with message: {message}")
            user_message = Message(
                message_id=str(uuid4()),
                role=Role.agent,
                parts=[TextPart(text=formatted_message)]
            )

            # Create SendMessageRequest
            request = SendMessageRequest(
                id=str(uuid4()),
                jsonrpc="2.0",
                method="message/send",
                params=MessageSendParams(message=user_message)
            )

            response = await client.send_message(request)
            return str(response)

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
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
    print(result.output)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

