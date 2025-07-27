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
    """Comprehensive test client for Legal Expert Agent - Tests both Query Decomposition and Search Validation skills"""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    base_url = 'http://localhost:8003'  # Legal expert agent server port
    
    print("🧪 Testing Legal Expert Agent - Complete Test Suite")
    print("=" * 80)
    
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
            
            # Test cases for both tools
            test_cases = [
                # ========== QUERY DECOMPOSITION TESTS ==========
                # Good queries (specific, searchable) - should be valid
                {
                    "category": "Query Decomposition",
                    "description": "Specific testimony query - GOOD",
                    "expected_outcome": "positive",
                    "message": {
                        "input_query": "What did John Smith say about the contract signing during his March 15th deposition?"
                    }
                },
                {
                    "category": "Query Decomposition", 
                    "description": "Specific communication query - GOOD",
                    "expected_outcome": "positive",
                    "message": {
                        "input_query": "Show me all emails between ABC Corp and the plaintiff regarding payment delays from January to March 2023"
                    }
                },
                {
                    "category": "Query Decomposition",
                    "description": "Specific evidence query - GOOD",
                    "expected_outcome": "positive", 
                    "message": {
                        "input_query": "What evidence exists in the documents about the defendant's knowledge of safety violations before the incident?"
                    }
                },
                {
                    "category": "Query Decomposition",
                    "description": "Specific document search - GOOD",
                    "expected_outcome": "positive",
                    "message": {
                        "input_query": "Find all invoices and payment records related to the consulting contract between Jane Doe and ABC Corp"
                    }
                },
                # Bad queries (too vague, not searchable) - should be invalid
                {
                    "category": "Query Decomposition",
                    "description": "Vague deposition question - BAD",
                    "expected_outcome": "negative",
                    "message": {
                        "input_query": "What should I ask the defendant in deposition?"
                    }
                },
                {
                    "category": "Query Decomposition",
                    "description": "Legal strategy question - BAD",
                    "expected_outcome": "negative",
                    "message": {
                        "input_query": "What is my best legal strategy for winning this case?"
                    }
                },
                {
                    "category": "Query Decomposition",
                    "description": "Case outcome prediction - BAD",
                    "expected_outcome": "negative",
                    "message": {
                        "input_query": "What are my chances of winning this lawsuit?"
                    }
                },
                {
                    "category": "Query Decomposition",
                    "description": "Case outcome prediction - BAD",
                    "expected_outcome": "negative",
                    "message": {"input_query": "I want to have a deposition in Johnny Depp and Amber Heard case, based on the context of the case - what should I ask the defendant?"}
                },
                
                # ========== SEARCH VALIDATION TESTS ==========
                # Good results (answered_in_full = true) - complete responses
                {
                    "category": "Search Validation",
                    "description": "Complete testimony response - GOOD",
                    "expected_outcome": "positive",
                    "message": {
                        "search_agent_response": "John Smith testified during his March 15th deposition that he reviewed the contract terms on March 10th and found them acceptable. He stated: 'I read through the entire agreement and discussed the payment schedule with our legal team. We agreed to the $50,000 fee and the June 30th payment deadline. I personally signed the contract on March 1st.'",
                        "lawyer_question": "What did John Smith say about the contract signing during his March 15th deposition?"
                    }
                },
                {
                    "category": "Search Validation",
                    "description": "Complete communication records - GOOD",
                    "expected_outcome": "positive", 
                    "message": {
                        "search_agent_response": "Found 8 emails between ABC Corp and Jane Doe regarding payment delays from January-March 2023: 1) Jan 15: Jane requests payment status, 2) Jan 22: ABC Corp says processing delayed, 3) Feb 1: Jane follows up, payment promised by Feb 15, 4) Feb 20: ABC Corp requests extension to March 1, 5) March 5: Jane threatens legal action, 6) March 10: ABC Corp promises payment by March 15, 7) March 16: Jane demands immediate payment, 8) March 20: ABC Corp stops responding.",
                        "lawyer_question": "Show me all emails between ABC Corp and the plaintiff regarding payment delays from January to March 2023"
                    }
                },
                {
                    "category": "Search Validation",
                    "description": "Complete evidence documentation - GOOD",
                    "expected_outcome": "positive",
                    "message": {
                        "search_agent_response": "Safety violation evidence: 1) Internal ABC Corp memo from Dec 2022 noting 'equipment maintenance overdue by 6 months', 2) Email from safety inspector to John Smith on Jan 10, 2023 warning of 'critical safety risks', 3) Maintenance logs showing repairs were scheduled but never completed, 4) Testimony from maintenance supervisor stating 'management knew about the risks but delayed repairs to save costs'.",
                        "lawyer_question": "What evidence exists in the documents about the defendant's knowledge of safety violations before the incident?"
                    }
                },
                # Bad results (answered_in_full = false) - incomplete responses
                {
                    "category": "Search Validation",
                    "description": "Incomplete testimony response - BAD",
                    "expected_outcome": "negative",
                    "message": {
                        "search_agent_response": "John Smith was deposed on March 15th, 2023. The deposition lasted 3 hours and covered the contract negotiations.",
                        "lawyer_question": "What did John Smith say about the contract signing during his March 15th deposition?"
                    }
                },
                {
                    "category": "Search Validation", 
                    "description": "Vague communication summary - BAD",
                    "expected_outcome": "negative",
                    "message": {
                        "search_agent_response": "There were several emails exchanged between the parties regarding payment issues during the first quarter of 2023.",
                        "lawyer_question": "Show me all emails between ABC Corp and the plaintiff regarding payment delays from January to March 2023"
                    }
                },
                {
                    "category": "Search Validation",
                    "description": "Insufficient evidence details - BAD",
                    "expected_outcome": "negative",
                    "message": {
                        "search_agent_response": "There were some safety concerns mentioned in company documents before the incident occurred.",
                        "lawyer_question": "What evidence exists in the documents about the defendant's knowledge of safety violations before the incident?"
                    }
                },
                {
                    "category": "Search Validation",
                    "description": "Missing specific document content - BAD",
                    "expected_outcome": "negative",
                    "message": {
                        "search_agent_response": "Found invoices and payment records related to the consulting contract. The documents exist in the case files.",
                        "lawyer_question": "Find all invoices and payment records related to the consulting contract between Jane Doe and ABC Corp"
                    }
                }
            ]
            
            # Group tests by category
            query_decomp_tests = [tc for tc in test_cases if tc["category"] == "Query Decomposition"]
            search_val_tests = [tc for tc in test_cases if tc["category"] == "Search Validation"]
            
            # Run Query Decomposition Tests
            print("🔍 QUERY DECOMPOSITION TESTS")
            print("=" * 50)
            for i, test_case in enumerate(query_decomp_tests, 1):
                await run_test(client, logger, i, test_case, "Query Decomposition")
            
            print("\n" + "="*80 + "\n")
            
            # Run Search Validation Tests  
            print("✅ SEARCH VALIDATION TESTS")
            print("=" * 50)
            for i, test_case in enumerate(search_val_tests, 1):
                await run_test(client, logger, i, test_case, "Search Validation")
                    
        except Exception as e:
            logger.error(f"Connection failed: {e}", exc_info=True)
            print(f"❌ Failed to connect to legal expert agent at {base_url}")
            print("Make sure the server is running with: python a2a_server.py")
            return
    
    print("✅ All tests completed!")


def evaluate_test_result(test_case, response_text):
    """Evaluate if a test passed based on expected outcome and response content"""
    expected_outcome = test_case.get("expected_outcome", "positive")
    
    # Check for timeout or error responses
    if "TIMEOUT" in response_text or "Processing error:" in response_text:
        return False
    
    # Check if response has meaningful content
    if len(response_text.strip()) < 20:
        return False
    
    response_lower = response_text.lower()
    
    # For Query Decomposition tests
    if "input_query" in test_case["message"] and "search_agent_response" not in test_case["message"]:
        if expected_outcome == "positive":
            # Good queries should be marked as valid
            return ("is_query_valid" in response_lower and "true" in response_lower) or "valid" in response_lower
        else:
            # Bad queries should be marked as invalid or have suggestions
            return (("is_query_valid" in response_lower and "false" in response_lower) or 
                   "invalid" in response_lower or "suggested_queries" in response_lower or
                   "alternative" in response_lower or "specific" in response_lower)
    
    # For Search Validation tests
    elif "search_agent_response" in test_case["message"] and "lawyer_question" in test_case["message"]:        
        if expected_outcome == "positive":
            # Complete responses should be marked as answered_in_full
            return (("answered_in_full" in response_lower and "true" in response_lower) or
                   "complete" in response_lower or "sufficient" in response_lower or
                   "adequate" in response_lower)
        else:
            # Incomplete responses should be marked as not answered_in_full or have missing info
            return (("answered_in_full" in response_lower and "false" in response_lower) or
                   "missing" in response_lower or "insufficient" in response_lower or 
                   "incomplete" in response_lower or "additional_queries" in response_lower or
                   "gap" in response_lower or "need" in response_lower)
    
    return False


async def run_test(client, logger, test_num, test_case, category):
    """Run an individual test case"""
    outcome_emoji = "✨" if test_case["expected_outcome"] == "positive" else "🔍"
    
    print(f"{outcome_emoji} Test {test_num}: {test_case['description']}")
    print(f"   Expected: {test_case['expected_outcome']} outcome")
    
    if 'search_agent_response' in test_case['message']:
        print(f"   📤 Search Response: {test_case['message']['search_agent_response'][:100]}...")
    print(f"   📤 Input Query: {test_case['message'].get('input_query', test_case['message'].get('lawyer_question', ''))}")
    print(f"   📥 Agent Response: ", end="", flush=True)
    
    # Format message as JSON for the agent
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
        import asyncio
        
        stream_response = client.send_message_streaming(streaming_request)
        response_text = ""
        
        # Add timeout to prevent getting stuck
        timeout_seconds = 60
        try:
            async def process_stream():
                nonlocal response_text
                async for chunk_stream in stream_response:
                    chunk = chunk_stream.model_dump(mode='json', exclude_none=True)
                    if 'result' in chunk and chunk['result']:
                        result = chunk['result']
                        if 'parts' in result and result['parts']:
                            for part in result['parts']:
                                if 'kind' in part and part['kind'] == 'text' and 'text' in part:
                                    print(part['text'], end="", flush=True)
                                    response_text += part['text']
            
            await asyncio.wait_for(process_stream(), timeout=timeout_seconds)
            
        except asyncio.TimeoutError:
            print(f"\n⏰ TIMEOUT after {timeout_seconds} seconds - test may be stuck")
            response_text = f"TIMEOUT after {timeout_seconds} seconds"
        
        if not response_text:
            print("(No text response received)")
            logger.debug(f"Raw chunk data available")
        
        # Evaluate test result
        test_passed = evaluate_test_result(test_case, response_text)
        if test_passed:
            print(f"\n✅ TEST PASSED - {test_case['description']}")
        else:
            print(f"\n❌ TEST FAILED - {test_case['description']}")
        
        print("\n" + "-" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Stream error: {e}")
        logger.error(f"Streaming failed for test case {test_num}: {e}", exc_info=True)
        print("-" * 60 + "\n")


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())