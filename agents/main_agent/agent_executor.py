
from dotenv import load_dotenv
from main import agent
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

load_dotenv()


class TaskManagerAgent:

    def __init__(self):
        self.agent = agent
    
    async def invoke(self, user_message: str) -> str:
        try:
            result = await self.agent.run(user_message)
            return result.data
        except Exception as e:
            return f"I apologize, but I encountered an error processing your request: {str(e)}"


class TaskManagerAgentExecutor(AgentExecutor):

    def __init__(self):
        self.agent = TaskManagerAgent()
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        try:
            user_message = ""
            if context.message and context.message.parts:
                for part in context.message.parts:
                    if hasattr(part, 'root') and hasattr(part.root, 'text') and part.root.text:
                        user_message = part.root.text
                        break

            response = await self.agent.invoke(user_message)
            
            message = new_agent_text_message(response)
            await event_queue.enqueue_event(message)
            
        except Exception as e:
            error_message = new_agent_text_message(
                f"I apologize, but I encountered an error: {str(e)}"
            )
            await event_queue.enqueue_event(error_message)
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle cancellation requests"""
        raise NotImplementedError("Cancellation is not supported for this agent")
