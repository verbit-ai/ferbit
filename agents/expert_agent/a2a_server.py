import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

from agent_executor import LegalExpertAgentExecutor


def create_agent_card() -> AgentCard:
    query_decomposition_skill = AgentSkill(
        id="query_decomposition",
        name="Legal Query Decomposition",
        description="Breaks down complex input queries into smaller, searchable components optimized for OpenSearch retrieval including sub-questions, key entities, and search keywords",
        tags=["query-analysis", "search-optimization", "legal-research", "question-breakdown"],
        examples=[
            '{"input_query": "I want to have a deposition in this case, based on the context of the case - what should I ask the defendant?"}',
            '{"input_query": "What is this case about and what are the key legal issues I should focus on?"}',
            '{"input_query": "Who are the main people, places, roles and main timelines in the case?"}'
        ]
    )

    search_validation_skill = AgentSkill(
        id="search_validation",
        name="Legal Search Response Validation",
        description="Validates search agent responses against lawyer case questions, identifies missing information, and determines what additional searches are needed",
        tags=["legal-validation", "search-completeness", "case-analysis", "gap-identification"],
        examples=[
            '{"search_agent_response": "The defendant is John Smith, CEO of ABC Corp.", "lawyer_question": "What should I ask the defendant in deposition?"}',
            '{"search_agent_response": "This is a breach of contract case filed June 15, 2023.", "lawyer_question": "What is this case about?"}',
            '{"search_agent_response": "Plaintiff: Jane Doe. Defendant: ABC Corp.", "lawyer_question": "Who are the main people and timeline in this case?"}'
        ]
    )

    capabilities = AgentCapabilities(
        streaming=True,
    )

    agent_card = AgentCard(
        name="Legal Expert Agent",
        description="Expert agent that provides query decomposition and search validation for legal case research. Breaks down complex lawyer questions into searchable components and validates search responses for completeness.",
        version="1.0.0",
        url="http://localhost:8003/",
        capabilities=capabilities,
        skills=[query_decomposition_skill, search_validation_skill],
        default_input_modes=["application/json"],
        default_output_modes=["application/json"]
    )

    return agent_card


def main():
    agent_card = create_agent_card()
    agent_executor = LegalExpertAgentExecutor()
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

    print("Starting Legal Expert Agent A2A Server...")
    print("Agent Card will be available at: http://localhost:8003/.well-known/agent.json")
    print("Legal expert agent ready with 2 skills (automatic tool selection):")
    print("1. Query Decomposition - Send: {\"input_query\": \"...\"}")
    print("2. Search Validation - Send: {\"search_agent_response\": \"...\", \"lawyer_question\": \"...\"}")
    print("Press CTRL+C to stop the server")

    uvicorn.run(
        app,
        timeout_keep_alive=60,
        host="0.0.0.0",
        port=8003,
        log_level="debug"
    )


if __name__ == "__main__":
    main()