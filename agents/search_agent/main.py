import os

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

mcp_server_url = os.environ.get('MCP_SERVER_URL', 'http://localhost:8000/sse')

server = MCPServerSSE(url=mcp_server_url)
agent = Agent('openai:gpt-4o', toolsets=[server])


async def main():
    async with agent:
        result = await agent.run('What is 2562 plus 6570?')
    print(result.output)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())