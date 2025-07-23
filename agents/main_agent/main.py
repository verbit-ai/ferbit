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
    "expert_agent": f"http://{SEARCH_AGENT_URL}",
    "search_agent": f"http://{EXPERT_AGENT_URL}"
}

load_dotenv()
agent = Agent(
    "openai:gpt-4o",
    system_prompt="""
        You are a manager of a team of AI agents.
        Your task is to assign tasks to the agents based on their capabilities.
        You will receive a task description and a list of agents with their capabilities.

        You will analyze the task and assign it to the most suitable agent.
        If no agent is suitable, you will respond with "No suitable agent found".
        Always provide a clear and concise response.
        If you need to ask for more information, do so in a clear and concise manner.
        Always provide the date and time of the request.
        The date and time should be in the format: YYYY-MM-DD HH:MM:SS

        You talk to the agents using the A2A protocol.
        The agents will respond with their results.

        The idea is to use the agents to solve complex tasks by breaking them down into smaller tasks and assigning them to the agents.

        """,
)

@agent.system_prompt
async def add_available_agents(ctx) -> str:
    if not agent_registry:
        return "No agents are currently registered."

    agents_list = ", ".join(agent_registry.keys())
    return f"Available agents: {agents_list}"

@agent.tool
async def say_hello(ctx) -> str:
    return "Hello, blablabla! This is a test message from the agent."


async def communicate_with_agent(agent_url: str, message: str) -> str:
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

                user_message = Message(
                    message_id=str(uuid4()),
                    role=Role.user,
                    parts=[TextPart(text=message)]
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

                # message_payload = {
                #     'message': {
                #         'role': 'user',
                #         'parts': [
                #             {'kind': 'text', 'text': message}
                #         ],
                #         'messageId': uuid4().hex,
                #     },
                # }
                #
                # streaming_request = SendStreamingMessageRequest(
                #     id=str(uuid4()),
                #     params=MessageSendParams(**message_payload)
                # )
                #
                # stream_response = client.send_message_streaming(streaming_request)
                # return str(stream_response)

            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                return f"Error communicating with agent: {e}\n\nFull traceback:\n{error_details}"



@agent.tool
async def send_message_to_agent(ctx, agent_name: str, message: str) -> str:
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

