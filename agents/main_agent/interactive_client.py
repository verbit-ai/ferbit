import logging
import asyncio
import sys
import re
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendStreamingMessageRequest,
)


def extract_suggestions(response_text: str) -> list:
    """Extract numbered suggestions or questions from the agent's response"""
    suggestions = []
    
    # Look for numbered lists (1., 2., etc.)
    numbered_pattern = r'^\s*\d+\.\s*(.+?)(?=\n|$)'
    numbered_matches = re.findall(numbered_pattern, response_text, re.MULTILINE)
    
    # Look for bullet points (- or •)
    bullet_pattern = r'^\s*[-•]\s*(.+?)(?=\n|$)'
    bullet_matches = re.findall(bullet_pattern, response_text, re.MULTILINE)
    
    # Look for questions ending with ?
    question_pattern = r'([^.!?]*\?)'
    question_matches = re.findall(question_pattern, response_text)
    
    # Prioritize numbered suggestions, then bullets, then questions
    if numbered_matches:
        suggestions = [s.strip() for s in numbered_matches if len(s.strip()) > 10]
    elif bullet_matches:
        suggestions = [s.strip() for s in bullet_matches if len(s.strip()) > 10]
    elif question_matches:
        suggestions = [s.strip() for s in question_matches if len(s.strip()) > 10 and '?' in s]
    
    # Clean up and limit to reasonable suggestions
    cleaned_suggestions = []
    for suggestion in suggestions[:5]:  # Max 5 suggestions
        cleaned = suggestion.strip()
        if cleaned and len(cleaned) > 20:  # Must be substantial
            cleaned_suggestions.append(cleaned)
    
    return cleaned_suggestions


def is_number_input(user_input: str, max_num: int) -> tuple:
    """Check if user input is a valid number selection"""
    try:
        num = int(user_input.strip())
        if 1 <= num <= max_num:
            return True, num
    except ValueError:
        pass
    return False, 0


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
            last_suggestions = []  # Store suggestions from previous response
            
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
                    
                    # Check if user selected a numbered suggestion
                    is_number, selected_num = is_number_input(user_input, len(last_suggestions))
                    if is_number and last_suggestions:
                        user_input = last_suggestions[selected_num - 1]
                        print(f"🎯 Using suggestion #{selected_num}: {user_input}")
                    elif user_input.lower() == 'more':
                        user_input = "Please provide more specific suggestions or alternatives for the previous query."
                        print(f"🔄 Requesting more suggestions...")
                    
                    # Handle special commands
                    if user_input.lower() in ['help', 'h']:
                        print("\n📚 Help:")
                        print("   • Type your question and press Enter")
                        print("   • Use numbers (1,2,3...) to select from suggestions")
                        print("   • Type 'more' for additional suggestions")
                        print("   • Type 'quit' or 'exit' to end session")
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
                    
                    # Enhanced interactivity: detect suggestions and offer quick follow-ups
                    suggestions = extract_suggestions(response_text)
                    last_suggestions = suggestions  # Store for next iteration
                    
                    if suggestions:
                        print("\n💡 The agent provided these specific suggestions:")
                        for i, suggestion in enumerate(suggestions, 1):
                            print(f"   {i}. {suggestion}")
                        
                        print("\n🚀 Quick options:")
                        print("   • Type a number (1-{}) to use that suggestion".format(len(suggestions)))
                        print("   • Ask your own follow-up question")
                        print("   • Type 'more' for additional suggestions")
                        print("   • Type 'help' for commands")
                        print("   • Type 'quit' to exit")
                    else:
                        # Even if no structured suggestions, encourage follow-up
                        print("\n💬 Feel free to ask follow-up questions or request more specific information!")
                    
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