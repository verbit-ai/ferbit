import logging
import asyncio
import sys
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendStreamingMessageRequest,
)


async def interactive_main_agent_client():
    """Interactive client for the main agent with streaming responses and conversation loop"""
    
    # Configure logging to be less verbose for interactive use
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    
    base_url = 'http://localhost:9111'  # Main agent server port
    
    print("🤖 Interactive AI Agent Task Manager Client")
    print("=" * 60)
    print("📝 Type your questions and get streaming responses")
    print("💡 Commands: 'quit', 'exit', or Ctrl+C to stop")
    print("🔄 The agent will use its iterative workflow: decompose → search → combine → validate")
    print("=" * 60)
    print()
    
    async with httpx.AsyncClient() as httpx_client:
        try:
            # Initialize A2ACardResolver
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=base_url,
            )
            
            # Fetch agent card
            print("🔌 Connecting to main agent...")
            agent_card = await resolver.get_agent_card()
            print(f"✅ Connected to: {agent_card.name}")
            print(f"📋 {agent_card.description}")
            print()

            client = A2AClient(
                httpx_client=httpx_client, 
                agent_card=agent_card
            )
            
            conversation_count = 0
            
            while True:
                try:
                    # Get user input
                    if conversation_count == 0:
                        prompt = "🗣️  Your question: "
                    else:
                        prompt = "🗣️  Ask another question (or 'quit'): "
                    
                    user_input = input(prompt).strip()
                    
                    # Check for exit commands
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("\n👋 Goodbye!")
                        break
                    
                    if not user_input:
                        print("⚠️  Please enter a question.")
                        continue
                    
                    conversation_count += 1
                    print(f"\n🌊 Response #{conversation_count}:")
                    print("📥 ", end="", flush=True)
                    
                    # Create message payload
                    message_payload = {
                        'message': {
                            'role': 'user',
                            'parts': [
                                {'kind': 'text', 'text': user_input}
                            ],
                            'messageId': uuid4().hex,
                        },
                    }
                    
                    # Create streaming request
                    streaming_request = SendStreamingMessageRequest(
                        id=str(uuid4()), 
                        params=MessageSendParams(**message_payload)
                    )
                    
                    response_text = ""
                    chunk_count = 0
                    
                    # Stream the response
                    async for chunk_stream in client.send_message_streaming(streaming_request):
                        chunk = chunk_stream.model_dump(mode='json', exclude_none=True)
                        chunk_count += 1
                        
                        if 'result' in chunk and chunk['result']:
                            result = chunk['result']
                            if 'parts' in result and result['parts']:
                                for part in result['parts']:
                                    if 'kind' in part and part['kind'] == 'text' and 'text' in part:
                                        text_chunk = part['text']
                                        print(text_chunk, end="", flush=True)
                                        response_text += text_chunk
                    
                    # Finalize response display
                    if not response_text:
                        print("(No response received)")
                    
                    print(f"\n{'─' * 60}")
                    print(f"📊 Response completed ({chunk_count} chunks, {len(response_text)} characters)")
                    print()
                    
                except KeyboardInterrupt:
                    print("\n\n⏹️  Interrupted by user")
                    break
                except EOFError:
                    print("\n\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"\n❌ Error processing request: {e}")
                    print("🔧 You can try again with a different question.")
                    continue
                    
        except KeyboardInterrupt:
            print("\n\n⏹️  Interrupted during setup")
        except Exception as e:
            print(f"❌ Failed to connect to main agent at {base_url}")
            print(f"Error: {e}")
            print("🔧 Make sure the main agent server is running with: python a2a_server.py")
            return
    
    print("✨ Session ended")


if __name__ == '__main__':
    try:
        asyncio.run(interactive_main_agent_client())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)