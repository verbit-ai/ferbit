import json
import logging
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendStreamingMessageRequest,
)


async def main() -> None:
    """Test client for Legal Search Validation A2A Agent - Stream only implementation"""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    base_url = 'http://localhost:8003'  # Legal validation agent server port
    
    print("🧪 Testing Legal Search Validation A2A Client (Stream Only)")
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
            
            # Test cases specific to legal validation agent with JSON format
            test_cases = [
                {
                    "description": "Basic search validation - deposition prep",
                    "message": {
                        "search_agent_response": "The defendant is John Smith, CEO of ABC Corp. He was involved in the contract negotiations in March 2023.",
                        "lawyer_question": "I want to have a deposition in this case, based on the context of the case - what should I ask the defendant?"
                    }
                },
                {
                    "description": "Case overview validation",
                    "message": {
                        "search_agent_response": "This is a breach of contract case filed on June 15, 2023. The plaintiff claims non-payment of $50,000 for services rendered.",
                        "lawyer_question": "What is this case about?"
                    }
                },
                {
                    "description": "Timeline and people validation",
                    "message": {
                        "search_agent_response": "Plaintiff: Jane Doe (consultant). Defendant: ABC Corp. Contract signed March 1, 2023. Services completed May 30, 2023.",
                        "lawyer_question": "Who are the main people, places, roles and main timelines in the case?"
                    }
                },
                {
                    "description": "Incomplete information test",
                    "message": {
                        "search_agent_response": "The case involves a contract dispute.",
                        "lawyer_question": "What are the key legal issues and what additional information do I need?"
                    }
                },
                {
                    "description": "Missing witness information",
                    "message": {
                        "search_agent_response": "Contract between Jane Doe and ABC Corp for consulting services. Payment was due but not received.",
                        "lawyer_question": "Who should I interview for this case and what documents do I need?"
                    }
                }
            ]
            
            for i, test_case in enumerate(test_cases, 1):
                print(f"🌊 Test {i}: {test_case['description']}")
                print(f"📤 Search Response: {test_case['message']['search_agent_response']}")
                print(f"📤 Lawyer Question: {test_case['message']['lawyer_question']}")
                print(f"📥 Validation Response: ", end="", flush=True)
                
                # Format message as JSON for the legal validation agent
                json_message = json.dumps(test_case['message'])
                
                message_payload = {
                    'message': {
                        'role': 'user',
                        'parts': [
                            {'kind': 'text', 'text': json_message}
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
                    logger.error(f"Streaming failed for test case {i}: {e}", exc_info=True)
                    print("-" * 50 + "\n")
                    
        except Exception as e:
            logger.error(f"Connection failed: {e}", exc_info=True)
            print(f"❌ Failed to connect to legal validation agent at {base_url}")
            print("Make sure the server is running with: python a2a_server.py")
            return
    
    print("✅ All streaming tests completed!")


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())