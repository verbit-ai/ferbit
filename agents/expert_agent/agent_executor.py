from dotenv import load_dotenv
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

load_dotenv()


class LegalExpertAgentExecutor(AgentExecutor):
    """Single executor that uses the agent's automatic tool selection based on input format"""
    
    def __init__(self):
        # Agent is already created globally, no need to recreate
        pass
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        try:
            user_message = ""
            if context.message and context.message.parts:
                for part in context.message.parts:
                    if hasattr(part, 'text') and part.text:
                        user_message = part.text
                        break
                    elif hasattr(part, 'root') and hasattr(part.root, 'text') and part.root.text:
                        user_message = part.root.text
                        break

            print(f"🔍 Legal Expert Agent - Processing message: {user_message[:100]}...")
            
            # Use pydantic-ai agent for tool selection
            from main import agent
            result = await agent.run(user_message)
            
            # Get the response text
            response_text = result.output if hasattr(result, 'output') else str(result)
            
            print(f"   📤 Response: {response_text[:200]}...")
            
            # Return the response as text
            message = new_agent_text_message(text=response_text)
            await event_queue.enqueue_event(message)
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            error_message = new_agent_text_message(text=f"Processing error: {str(e)}")
            await event_queue.enqueue_event(error_message)
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle cancellation requests"""
        raise NotImplementedError("Cancellation is not supported for this agent")