from dotenv import load_dotenv
from main import ExpertAgent
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message
import json

load_dotenv()


class LegalExpertValidationAgent:

    def __init__(self):
        self.expert_agent = ExpertAgent()
    
    async def invoke(self, user_message: str) -> str:
        try:
            # Parse the validation request from the user message
            # Expected format: JSON with search_agent_response and lawyer_question
            request_data = json.loads(user_message)
            search_agent_response = request_data.get("search_agent_response", "")
            lawyer_question = request_data.get("lawyer_question", "")
            
            if not search_agent_response or not lawyer_question:
                return json.dumps({
                    "error": "Both 'search_agent_response' and 'lawyer_question' are required",
                    "validation": {
                        "is_complete": False,
                        "missing_information": ["Invalid request format"],
                        "additional_searches_needed": []
                    }
                })
            
            # Process the validation
            result = await self.expert_agent.process_search_validation(
                search_agent_response, 
                lawyer_question
            )
            
            return json.dumps(result, indent=2)
            
        except json.JSONDecodeError:
            return json.dumps({
                "error": "Invalid JSON format. Expected: {\"search_agent_response\": \"...\", \"lawyer_question\": \"...\"}",
                "validation": {
                    "is_complete": False,
                    "missing_information": ["Invalid request format"],
                    "additional_searches_needed": []
                }
            })
        except Exception as e:
            return json.dumps({
                "error": f"Validation error: {str(e)}",
                "validation": {
                    "is_complete": False,
                    "missing_information": [f"Processing error: {str(e)}"],
                    "additional_searches_needed": []
                }
            })


class LegalExpertValidationAgentExecutor(AgentExecutor):

    def __init__(self):
        self.agent = LegalExpertValidationAgent()
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        try:
            user_message = ""
            if context.message and context.message.parts:
                for part in context.message.parts:
                    # Try different ways to extract the text content
                    if hasattr(part, 'text') and part.text:
                        user_message = part.text
                        break
                    elif hasattr(part, 'root') and hasattr(part.root, 'text') and part.root.text:
                        user_message = part.root.text
                        break

            print(f"🔍 Extracted user message: {user_message[:100]}...")  # Debug log
            response = await self.agent.invoke(user_message)
            print(f"📤 Agent response length: {len(response)} characters")  # Debug log
            
            message = new_agent_text_message(text=response)
            await event_queue.enqueue_event(message)
            
        except Exception as e:
            error_message = new_agent_text_message(
                f"I apologize, but I encountered an error during legal validation: {str(e)}"
            )
            await event_queue.enqueue_event(error_message)
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle cancellation requests"""
        raise NotImplementedError("Cancellation is not supported for this agent")