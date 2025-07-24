import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill, AgentCapabilities
from starlette.middleware.cors import CORSMiddleware

from agent_executor import TaskManagerAgentExecutor


def create_agent_card() -> AgentCard:
    task_management_skill = AgentSkill(
        id="task_manager",
        name="AI Agent Task Manager",
        description="Manages and assigns tasks to a team of AI agents based on their capabilities. Analyzes task requirements and routes them to the most suitable agent in the registry. Coordinates complex tasks by breaking them down into smaller, manageable subtasks.",
        tags=["task-management", "agent-coordination", "workflow", "delegation", "orchestration", "team-management", "routing", "analysis", "expertise", "search", ""],
        examples=[
            "Find all deposition transcripts where the witness discussed the merger agreement",
            "What is the statute of limitations for breach of contract claims in California?",
            "Search for expert witness testimony about accounting practices in our case files",
            "Can you explain the legal significance of the attorney-client privilege objection?",
            "Find depositions where opposing counsel mentioned the Delaware incorporation documents",
            "What are the key elements required to prove negligent misrepresentation?",
            "Search for any prior testimony by Dr. Smith in similar patent infringement cases",
            "Help me understand the discovery rules for electronically stored information",
            "Find all references to the confidentiality agreement in witness depositions"
        ]
    )

    capabilities = AgentCapabilities(
        streaming=True,
    )

    agent_card = AgentCard(
        name="AI Agent Task Manager",
        description="A manager of a team of AI agents that assigns tasks based on their capabilities. Analyzes task descriptions and routes them to the most suitable agent. Uses the A2A protocol to communicate with agents and coordinates complex tasks by breaking them down into smaller manageable tasks.",
        version="1.0.0",
        url="http://localhost:9111/",
        capabilities=capabilities,
        skills=[task_management_skill],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"]
    )

    return agent_card


def main():
    agent_card = create_agent_card()
    agent_executor = TaskManagerAgentExecutor()
    task_store = InMemoryTaskStore()
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=task_store
    )
    server_app_builder = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )
    app = server_app_builder.build()

    # Add CORS middleware for all clients and methods
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods
        allow_headers=["*"],  # Allow all headers
    )

    print("Starting AI Agent Task Manager A2A Server...")
    print("Agent Card will be available at: http://localhost:9111/.well-known/agent.json")
    print("Task management and agent coordination ready for your requests!")
    print("Press CTRL+C to stop the server")

    uvicorn.run(
        app,
        timeout_keep_alive=60,
        host="0.0.0.0",
        port=9111,
        log_level="debug"
    )


if __name__ == "__main__":
    main()
