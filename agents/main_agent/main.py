import os
from typing import Dict

from dotenv import load_dotenv
from pydantic_ai import Agent

SEARCH_AGENT_URL = os.getenv("SEARCH_AGENT_URL", "localhost:8001")
EXPERT_AGENT_URL = os.getenv("EXPERT_AGENT_URL", "localhost:8002")

agent_registry: Dict[str, str] = {
    "linkedin_scraper": f"http://{SEARCH_AGENT_URL}",
    "github_agent": f"http://{EXPERT_AGENT_URL}"
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

# Example tool the agent can use
@agent.tool
async def say_hello(ctx) -> str:
    return "Hello, blablabla! This is a test message from the agent."

# Main entry point
async def main():
    result = await agent.run("Which agent can you trigger")
    print(result.output)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

