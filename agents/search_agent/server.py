from typing import Dict, Any
import uuid

from a2a.types import (
    AgentCard, 
    AgentSkill, 
    AgentCapabilities, 
    AgentProvider
)
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue

from search_agent import SearchAgent


def get_agent_card(host: str = "localhost", port: int = 8001) -> AgentCard:
    """Create A2A agent card for the Search Agent"""
    capabilities = AgentCapabilities(streaming=True, pushNotifications=False)
    
    search_skill = AgentSkill(
        id='search_collection',
        name='Document Search',
        description='Search through document collections and provide relevant information',
        tags=['search', 'documents', 'retrieval', 'mcp'],
        examples=[
            'Search for documents about machine learning',
            'Find papers related to natural language processing',
            'What documents mention neural networks?'
        ]
    )
    
    return AgentCard(
        name='Search Agent',
        description='An intelligent search agent that can query collections and provide relevant information using MCP integration.',
        url=f'http://{host}:{port}',
        version='1.0.0',
        provider=AgentProvider(
            organization='Ferbit Research',
            url='https://ferbit.example.com'
        ),
        capabilities=capabilities,
        skills=[search_skill],
        default_input_modes=['text/plain'],
        default_output_modes=['text/plain']
    )


class SearchAgentExecutor(AgentExecutor):
    """A2A Agent Executor for Search Agent"""
    
    def __init__(self):
        self.agent = SearchAgent()
    
    def _get_user_query(self, params: Dict[str, Any]) -> str:
        """Extract user query from A2A message params"""
        message = params.get('message', {})
        parts = message.get('parts', [])
        
        query = ""
        for part in parts:
            if part.get('kind') == 'text':
                query += part.get('text', '')
        
        return query.strip()
    
    async def on_message_send(self, request, event_queue, task):
        """Handle synchronous message sending"""
        params = request.params
        query = self._get_user_query(params)
        
        try:
            # Use the agent to process the query
            response = await self.agent.ainvoke(query, task.contextId)
            
            # Update task with agent response
            task.response = {
                "message": {
                    "message_id": str(uuid.uuid4()),
                    "role": "assistant",
                    "parts": [
                        {
                            "kind": "text",
                            "text": response
                        }
                    ],
                    "kind": "message"
                }
            }
            
            # Enqueue the response
            event_queue.enqueue_event(task)
            
        except Exception as e:
            # Handle errors
            task.error = {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            }
            event_queue.enqueue_event(task)
    
    async def on_message_stream(self, request, event_queue, task):
        """Handle streaming message requests"""
        params = request.params
        query = self._get_user_query(params)
        
        try:
            # Stream responses from the agent
            async for chunk in self.agent.stream(query, task.contextId):
                if 'messages' in chunk and chunk['messages']:
                    last_message = chunk['messages'][-1]
                    if hasattr(last_message, 'content') and last_message.content:
                        # Send streaming response
                        stream_task = task.copy()
                        stream_task.response = {
                            "message": {
                                "message_id": str(uuid.uuid4()),
                                "role": "assistant",
                                "parts": [
                                    {
                                        "kind": "text",
                                        "text": last_message.content
                                    }
                                ],
                                "kind": "message"
                            }
                        }
                        event_queue.enqueue_event(stream_task)
                        
        except Exception as e:
            # Handle streaming errors
            task.error = {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            }
            event_queue.enqueue_event(task)
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent's logic for a given request context."""
        try:
            print(f"🎯 SearchAgentExecutor.execute called")
            
            # Extract request details from context
            task_id = getattr(context, 'task_id', None)
            context_id = getattr(context, 'context_id', None)
            message = getattr(context, 'message', None)
            
            # Always check for X-Context-Id header first (this is the collection_id we want)
            header_context_id = None
            if hasattr(context, 'call_context') and context.call_context:
                headers = context.call_context.state.get('headers', {})
                header_context_id = headers.get('x-context-id') or headers.get('X-Context-Id')
                print(f"🔗 Found X-Context-Id header: {header_context_id}")
                print(f"📋 All headers: {headers}")
            
            # Use header context_id if available, otherwise use context.context_id
            final_context_id = header_context_id if header_context_id else context_id
            
            print(f"📁 Task ID: {task_id}")
            print(f"🔗 Context ID: {context_id}")
            print(f"💬 Message: {message}")
            print(f"🔍 Full context attributes: {dir(context)}")
            
            if message and hasattr(message, 'parts'):
                # Extract query from message parts
                query = ""
                for part in message.parts:
                    print(f"🔍 Processing part: {part}")
                    if hasattr(part, 'root') and hasattr(part.root, 'text'):
                        query += part.root.text
                    elif hasattr(part, 'text'):
                        query += part.text
                
                query = query.strip()
                print(f"🔍 Extracted query: '{query}'")
                
                # Use final_context_id as collection_id, fallback to task_id if not available
                collection_id = final_context_id if final_context_id else task_id
                print(f"🗂️ Using collection_id: {collection_id}")
                print(f"🔗 Header context_id: {header_context_id}")
                print(f"🔗 Message context_id: {context_id}")
                print(f"🎯 Final collection_id: {collection_id}")
                
                # Use the agent to process the query
                response = await self.agent.ainvoke(query, collection_id)
                
                print(f"🤖 Agent response: {response}")
                
                # Create the task response with proper schema
                from a2a.types import Task, TaskStatus, TaskState, Message, Part, TextPart
                
                # Create message parts - use TextPart wrapped in Part
                text_part = TextPart(kind="text", text=response)
                message_parts = [Part(root=text_part)]
                
                # Create response message
                response_message = Message(
                    message_id=str(uuid.uuid4()),
                    role="agent",
                    parts=message_parts,
                    kind="message"
                )
                
                # Create task status
                task_status = TaskStatus(
                    state=TaskState.completed,
                    message=response_message
                )
                
                # Create completed task
                task = Task(
                    id=task_id,
                    contextId=task_id,
                    status=task_status
                )
                
                print(f"📤 Enqueueing task: {task}")
                await event_queue.enqueue_event(task)
                
            else:
                print("❌ Invalid context structure - no message found")
                raise ValueError("No message found in request context")
                
        except Exception as e:
            print(f"❌ Error in execute: {e}")
            import traceback
            traceback.print_exc()
            
            # Create error task with proper schema
            from a2a.types import Task, TaskStatus, TaskState
            
            error_status = TaskStatus(
                state=TaskState.failed
            )
            
            error_task = Task(
                id=getattr(context, 'task_id', str(uuid.uuid4())),
                contextId=getattr(context, 'task_id', str(uuid.uuid4())),
                status=error_status
            )
            
            await event_queue.enqueue_event(error_task)
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Request the agent to cancel an ongoing task."""
        # This method would handle task cancellation
        pass

