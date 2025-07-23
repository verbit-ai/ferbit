import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

from agent_executor import LegalExpertValidationAgentExecutor


def create_agent_card() -> AgentCard:
    search_validation_skill = AgentSkill(
        id="search_response_validation",
        name="Legal Search Response Validation",
        description="Validates search agent responses to lawyer case questions, identifies missing information, and requests additional searches through the orchestrator",
        tags=["legal-validation", "search-completeness", "case-analysis", "gap-identification", "orchestration"],
        examples=[
            '{"search_agent_response": "The defendant is John Smith, CEO of ABC Corp.", "lawyer_question": "What should I ask the defendant in deposition?"}',
            '{"search_agent_response": "This is a breach of contract case filed June 15, 2023.", "lawyer_question": "What is this case about?"}',
            '{"search_agent_response": "Plaintiff: Jane Doe. Defendant: ABC Corp.", "lawyer_question": "Who are the main people and timeline in this case?"}'
        ]
    )

    missing_info_skill = AgentSkill(
        id="missing_information_identification",
        name="Missing Case Information Analysis",
        description="Identifies specific gaps in search results and determines what case information is missing for complete legal answers",
        tags=["information-gaps", "case-documents", "missing-data", "legal-completeness"],
        examples=[
            "Identify missing witness statements for deposition preparation",
            "Find gaps in case timeline from search results", 
            "Determine missing party information for case overview"
        ]
    )

    orchestration_skill = AgentSkill(
        id="additional_search_orchestration",
        name="Search Orchestration Requests",
        description="Generates specific additional search requests to be sent to the orchestrator for improving search completeness",
        tags=["search-orchestration", "iterative-search", "targeted-queries", "legal-research"],
        examples=[
            "Request search for specific document types from date range",
            "Ask for additional information about particular case parties",
            "Request targeted search for missing procedural history"
        ]
    )

    capabilities = AgentCapabilities(
        streaming=True,
    )

    agent_card = AgentCard(
        name="Legal Search Validation Agent",
        description="Expert agent that validates search agent responses to lawyer case questions, identifies missing case information, and coordinates additional searches through the orchestrator to ensure comprehensive legal answers.",
        version="1.0.0",
        url="http://localhost:8003/",
        capabilities=capabilities,
        skills=[search_validation_skill, missing_info_skill, orchestration_skill],
        default_input_modes=["application/json"],
        default_output_modes=["application/json"]
    )

    return agent_card


def main():
    agent_card = create_agent_card()
    agent_executor = LegalExpertValidationAgentExecutor()
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

    print("Starting Legal Search Validation Agent A2A Server...")
    print("Agent Card will be available at: http://localhost:8002/.well-known/agent.json")
    print("Legal search validation ready for your requests!")
    print("Send JSON format: {\"search_agent_response\": \"...\", \"lawyer_question\": \"...\"}")
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