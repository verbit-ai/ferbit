#!/usr/bin/env python3
"""
Entry point for the Search Agent A2A server.
"""

import asyncio
import uvicorn

from server import get_agent_card, SearchAgentExecutor
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.events.in_memory_queue_manager import InMemoryQueueManager


async def main():
    """Main function - runs A2A server"""
    print("Starting A2A Search Agent server on port 8001...")
    
    # Create agent card
    agent_card = get_agent_card("localhost", 8001)
    
    # Create A2A components
    executor = SearchAgentExecutor()
    task_store = InMemoryTaskStore()
    queue_manager = InMemoryQueueManager()
    
    # Create request handler
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        queue_manager=queue_manager
    )
    
    # Create A2A FastAPI application
    app_builder = A2AFastAPIApplication(agent_card, request_handler)
    app = app_builder.build()
    
    # Run the server
    config = uvicorn.Config(app, host="0.0.0.0", port=8001)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")