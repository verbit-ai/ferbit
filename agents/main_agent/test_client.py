import logging

from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendStreamingMessageRequest,
)


async def main() -> None:
    """Test client for AI Agent Task Manager - Stream only implementation"""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    base_url = 'http://localhost:9111'  # Task manager server port
    
    print("🧪 Testing AI Agent Task Manager A2A Client (Stream Only)")
    print("=" * 60)
    
    async with httpx.AsyncClient() as httpx_client:
        try:
            # Initialize A2ACardResolver
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=base_url,
            )
            
            # Fetch agent card
            print("📋 Fetching Agent Card...")
            agent_card = await resolver.get_agent_card()
            print(f"✅ Connected to: {agent_card.name}")
            print(f"📝 Description: {agent_card.description}")
            print(f"🔧 Skills: {len(agent_card.skills)}")
            for skill in agent_card.skills:
                print(f"   - {skill.name}")
            print()
            
            client = A2AClient(
                httpx_client=httpx_client, 
                agent_card=agent_card
            )
            logger.info('A2AClient initialized for streaming.')
            
            test_messages = [
                "What agents are available and what can they do?",
                "Which agent can handle LinkedIn profile scraping?", 
                "Assign this task to the most suitable agent: I need to analyze GitHub repositories",
                "Route this request to the github_agent: Please analyze the repository structure",
                "Break down this complex task: I need to scrape LinkedIn profiles and analyze them with AI"
            ]
            
            for i, message_text in enumerate(test_messages, 1):
                print(f"🌊 Test {i}: Streaming Message")
                print(f"📤 Request: {message_text}")
                print(f"📥 Response: ", end="", flush=True)
                
                message_payload = {
                    'message': {
                        'role': 'user',
                        'parts': [
                            {'kind': 'text', 'text': message_text}
                        ],
                        'messageId': uuid4().hex,
                    },
                }
                
                streaming_request = SendStreamingMessageRequest(
                    id=str(uuid4()), 
                    params=MessageSendParams(**message_payload)
                )
                
                try:
                    stream_response = client.send_message_streaming(streaming_request)
                    response_text = ""
                    
                    async for chunk_stream in stream_response:
                        chunk = chunk_stream.model_dump(mode='json', exclude_none=True)
                        if 'result' in chunk and chunk['result']:
                            result = chunk['result']
                            if 'parts' in result and result['parts']:
                                for part in result['parts']:
                                    if 'kind' in part and part['kind'] == 'text' and 'text' in part:
                                        print(part['text'], end="", flush=True)
                                        response_text += part['text']
                    
                    if not response_text:
                        print("(No text response received)")
                        logger.debug(f"Raw chunk data: {chunk}")
                    
                    print("\n" + "-" * 50 + "\n")
                    
                except Exception as e:
                    print(f"\n❌ Stream error: {e}")
                    logger.error(f"Streaming failed for message {i}: {e}", exc_info=True)
                    print("-" * 50 + "\n")
                    
        except Exception as e:
            logger.error(f"Connection failed: {e}", exc_info=True)
            print(f"❌ Failed to connect to task manager at {base_url}")
            print("Make sure the server is running with: python a2a_server.py")
            return
    
    print("✅ All streaming tests completed!")


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())