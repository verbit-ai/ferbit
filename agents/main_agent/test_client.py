import logging

from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendStreamingMessageRequest,
)


async def main() -> None:

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
            agent_card = await resolver.get_agent_card()

            client = A2AClient(
                httpx_client=httpx_client, 
                agent_card=agent_card
            )
            logger.info('A2AClient initialized for streaming.')
            
            test_messages = [
                # "What agents are available and what can they do?",
                # '{"input_query": "I want to have a deposition in Johnny Depp and Amber Heard case, based on the context of the case - what should I ask the defendant?"}',
                # "Please Search about manning case",
                # "can you describe mister Fredrick behaviour in short",
                # "how many people mentioned in this case. And who are they?",
                # "Tell me about the ACC vs Fire case",
                "Describe the timeline of events in the acc vs fire case",
                # "Who are the main key players in ACC vs FIRE case"
                # "What is the allegation described in the ACC vs FIRE case"
                # "How many people are involved in ACC vs Fire case and who are they"
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

# Describe the timeline of events in the acc vs fire case
# answer
# The timeline of the "ACC vs Fire" case has been compiled as follows, using the information retrieved from various documents:
#
# 1. **Claims made by ACC (January 2020):**
#    - ACC alleged that Fire Star failed to deliver coal with required sulfur content, causing additional costs for ACC. [Document: 66-12.pdf](s3://verbit-staging-attachments/customer_notes/husBrXftRKCKkE9zW5w8_66-12.pdf)
#
# 2. **Counterclaims by Fire (March 2020):**
#    - Fire Star claimed ACC used coal meant for the Archbold Plant at other locations, taking advantage of lower prices. [Document: Answer.pdf](s3://verbit-staging-attachments/customer_notes/UGi7XwN6SGS5zndTrfcz_Answer.pdf)
#
# 3. **Key Issues and Arguments (Trial Proceedings):**
#    - Main focus on whether Fire Star breached the Coal Supply Agreement by not delivering coal up to specifications.
#    - ACC sought damages, while Fire Star counterclaimed for misrepresentation by ACC. [Document: Complaint.pdf](s3://verbit-staging-attachments/customer_notes/TSNdrHNRSJvG12ICYi9R_Complaint.pdf)
#
# 4. **Pre-trial Hearings and Motions:**
#    - This needs additional research for full details.
#
# 5. **Ruling and Judgment (December 2020):**
#    - Information on specific outcomes and judgment has yet to be detailed.
#
# 6. **Grounds for Appeal by Fire (February 2021):**
#    - Fire Star's appeal alleged breaches by ACC for not allowing price matching on post-2022 coal, bad faith actions, resulting in damages to Fire Star. [Document: Answer.pdf](s3://verbit-staging-attachments/customer_notes/UGi7XwN6SGS5zndTrfcz_Answer.pdf)
#
# To achieve a more comprehensive understanding, additional details are needed about the pre-trial hearings and precise judgment specifics passed in December 2020. However, the above gathers much of the critical timeline and issues involved in the ACC vs Fire case from the available documents.
#
#
# Tell me about the ACC vs Fire case
#
# Answer:
# Here's a comprehensive overview of the ACC vs Fire case based on the refined queries:
#
# 1. **Key Facts:**
#    - **Parties Involved**: American Colloid Company (ACC) is the plaintiff, and Fire Star Energy Resources, LLC is the defendant.
#    - **Contractual Agreement**: Involves a Coal Supply Agreement where Fire Star was to supply ACC's Archbold, Ohio plant with coal from January 2021 to December 2022.
#    - **Breach of Contract**: Fire Star applied surcharge prices not agreed upon starting March 7, 2022, failing to fulfill ACC's orders.
#    - **Damages**: ACC had to find a new supplier and incurred extra costs due to Fire Star's breach.
#    - **Legal Proceedings**: Numerous depositions and arguments regarding the breach and damages.
#
# 2. **Court's Findings:**
#    - Fire Star breached the contract by failing to supply coal as agreed.
#    - ACC incurred damages by having to find alternative suppliers at a higher cost.
#    - Fire Star's failure to provide payment security further strained their relationship.
#    - ACC was entitled to compensatory damages, legal fees, and costs.
#
# 3. **Main Arguments by ACC:**
#    - **Usage and Orders**: Fire Star's coal was exclusively for ACC's plant, and the order quantities were within the agreed limits.
#    - **Supply and Demand**: ACC fulfilled part of its coal needs through other suppliers due to Fire Star's non-compliance.
#    - **Financial Losses**: ACC seeks compensatory damages for the breach causing significant financial losses.
#
# 4. **Final Judgment:**
#    - The case is ongoing, and ACC seeks compensatory damages expected to exceed $351,000, along with legal fees and other relief.
#
# These findings represent a detailed synthesis of the available data on the case. If there are any specific areas you need further details on, please let me know!
#
# Who are the main key players in ACC vs FIRE case
# ANSWER
# The main key players in the ACC vs FIRE case are as follows:
#
# 1. **Defendants and Plaintiffs:**
#    - Defendants: Fire Star Energy Resources, LLC
#    - Plaintiffs: American Colloid Company (ACC)
#
# 2. **Key Witnesses:**
#    - Timothy M. Jones
#    - Dwayne Jones
#    - Scott Warren (CFO at B&W, supplier to Defendant)
#    - Neil Miller
#
# 3. **Main Attorneys:**
#    - Sarah K. Rathke
#    - Lauryn B. Durham
#    - Barry Hunter
#
# These individuals and entities are integral to the proceedings of the ACC vs FIRE case.
#
# What is the allegation described in the ACC vs FIRE case
# ANSWER
# Here are the summarized allegations from the ACC vs FIRE case based on the search results:
#
# 1. **Breach of Contract**: The primary allegation involves Fire Star Energy Resources breaching the Coal Supply Agreement by not fulfilling an order made by American Colloid Company (ACC) on June 10, 2022.
#
# 2. **Material Breach**: This failure to supply coal constitutes a material breach of the agreement between ACC and Fire Star.
#
# 3. **Compensation Claim**: ACC is seeking $1,055,368.83 in compensatory cover damages due to the breach, as Fire Star's refusal forced ACC to source coal from alternative suppliers, incurring additional costs.
#
# These claims outline the core allegations ACC has raised against Fire Star in the case. If further validation or additional details are required, we can conduct more targeted searches or consult the expert agent again.
#
#
#
# How many people are involved in ACC vs Fire case and who are they
# ANSWER
# Here's the comprehensive information about the people involved in the "ACC vs Fire" case:
#
# 1. **Individuals Named in Case Documents:**
#    - Aric Wentz (Supervisor at Plaintiff)
#    - Neil Miller (Manager at Plaintiff)
#    - Rachel Perkins (Plant Administrator at ACC)
#    - Mike Wagner (former employee at ACC)
#    - Dwayne Couch (employee at Fire Star)
#    - Dorothy Dreher (Accounts Payable at ACC)
#
# 2. **Parties Involved in the Case:**
#    - **Plaintiff:** American Colloid Company (ACC), located at 2870 Forbs Avenue, Hoffman Estates, Illinois 60192.
#    - **Defendant:** Fire Star Energy Resources, LLC, located at 4505 Meadowridge Court, Lexington, Kentucky 40415.
#
# 3. **Witnesses Mentioned in Depositions:**
#    - Timothy M. Jones
#    - Dwayne Jones
#    - Scott Warren (CFO at B&W, supplier to Defendant)
#    - Aric Wentz (Supervisor at Plaintiff)
#    - Neil Miller (Manager at Plaintiff)
#    - Rachel Perkins (Plant Administrator at ACC)
#    - Mike Wagner (former employee at ACC)
#    - Dwayne Couch (employee at Fire Star)
#    - Dorothy Dreher (Accounts Payable at ACC)
#
# If further validation or additional information is needed, I can proceed to validate the completeness with the expert agent.