import os
import asyncio
import re
from typing import Dict, Any, List
from pydantic import BaseModel
from pydantic_ai import Agent
# No MCP needed for this agent
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class SearchValidationRequest(BaseModel):
    search_agent_response: str
    lawyer_question: str


class SearchValidationResult(BaseModel):
    is_complete: bool
    missing_information: List[str]
    additional_searches_needed: List[str]


class ExpertAgent:
    def __init__(self):
        # Ensure OpenAI API key is set
        openai_key = os.environ.get('OPENAI_API_KEY')
        if not openai_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        print(f"OpenAI API Key loaded: {openai_key[:10]}..." if openai_key else "No API key found")
        
        # Initialize the validation agent (no MCP tools needed)
        self.agent = Agent(
            'openai:gpt-4o',
            system_prompt="""You are an expert validation agent in a legal search system serving lawyers. Your specific role is to:

            1. Receive a search agent's response to a lawyer's case question
            2. Validate whether the search response comprehensively answers the lawyer's question
            3. Identify specific gaps or missing information in the search results
            4. Determine what additional searches are needed to complete the answer
            
            WORKFLOW CONTEXT:
            - Lawyer asks case question → Search Orchestrator → Search Agent (OpenSearch) → YOU → Back to Orchestrator for additional searches if needed → Formatter Agent → Final response to lawyer
            
            Your validation should focus on:
            
            SEARCH COMPLETENESS:
            - Does the search response contain all necessary information to answer the lawyer's question?
            - Are there obvious gaps in the retrieved case information?
            - Is the information specific enough for the lawyer's needs?
            
            CASE-SPECIFIC INFORMATION GAPS:
            - Missing key people, dates, or events relevant to the question
            - Absent case documents or evidence that should be referenced
            - Lack of procedural history or timeline information
            - Missing party relationships, roles, or responsibilities
            - Incomplete information about case facts, claims, or defenses
            
            PRACTICAL LEGAL CONSIDERATIONS:
            - For deposition questions: Are relevant case facts, witness statements, and document references included?
            - For case overview questions: Are all key parties, claims, timeline, and current status covered?
            - For timeline questions: Are chronological events, deadlines, and procedural steps complete?
            - For strategy questions: Is sufficient factual foundation provided for legal analysis?
            
            When identifying missing information, be specific about what additional searches would help:
            - Specific document types needed
            - Particular time periods to search
            - Specific parties or entities to research
            - Key legal concepts or case elements to explore further
            """
        )

    async def validate_search_response(self, validation_request: SearchValidationRequest) -> SearchValidationResult:
        """
        Validate if the search agent response contains sufficient information to answer the lawyer's question.
        """
        validation_prompt = f"""
        LAWYER'S QUESTION: {validation_request.lawyer_question}
        
        SEARCH AGENT RESPONSE: {validation_request.search_agent_response}
        
        You are validating whether the search agent's response contains sufficient information from the case documents to fully answer the lawyer's question.
        
        Analyze the search response for completeness:
        
        1. INFORMATION COMPLETENESS:
        - Does the search response contain all necessary case information to answer the question?
        - Are there obvious information gaps that would prevent a complete answer?
        - Is the retrieved information specific and detailed enough?
        
        2. CASE-SPECIFIC GAPS:
        - Missing key people, dates, events, or documents
        - Incomplete procedural history or timeline
        - Absent party relationships or case context
        - Lack of relevant case facts or evidence
        
        3. QUESTION-SPECIFIC REQUIREMENTS:
        - For deposition questions: Are relevant facts, prior statements, and supporting documents included?
        - For case overview questions: Are all key parties, claims, timeline, and status covered?
        - For timeline questions: Are chronological events and deadlines complete?
        - For people/roles questions: Are party relationships and responsibilities clear?
        
        Return your validation in this exact format:
        
        - Is the search response complete? (Yes/No and explanation)
        
        - What specific information is missing from the search results?
          1. [specific missing item 1]
          2. [specific missing item 2]
          3. [etc.]
        
        - What additional searches should the orchestrator request from the search agent?
          1. "[specific search request 1]"
          2. "[specific search request 2]"
          3. "[etc.]"
        
        Be specific about missing information and suggest targeted searches with quotes around each search request.
        """
        
        try:
            result = await self.agent.run(validation_prompt)
            
            # Parse the agent's response to determine completeness
            response_text = str(result.output).lower()
            
            # Simple heuristic to determine if response is complete
            is_complete = (
                "yes" in response_text and 
                ("complete" in response_text or "fully addresses" in response_text) and
                "missing" not in response_text
            )
            
            # Extract missing information and additional searches from the response
            missing_information = self._extract_missing_information(str(result.output))
            additional_searches = self._extract_additional_searches(str(result.output))
            
            return SearchValidationResult(
                is_complete=is_complete,
                missing_information=missing_information,
                additional_searches_needed=additional_searches
            )
            
        except Exception as e:
            print(f"Error during search validation: {e}")
            return SearchValidationResult(
                is_complete=False,
                missing_information=[f"Search validation error: {str(e)}"],
                additional_searches_needed=[]
            )

    def _extract_missing_information(self, response: str) -> List[str]:
        """Extract missing information from the agent's response."""
        missing_info = []
        lines = response.split('\n')
        
        in_missing_section = False
        for line in lines:
            line = line.strip()
            
            # Start capturing when we see the missing information section
            if "what specific information is missing" in line.lower():
                in_missing_section = True
                continue
            
            # Stop when we reach the additional searches section
            if "what additional searches" in line.lower():
                in_missing_section = False
                break
            
            # Extract numbered items in the missing information section
            if in_missing_section and line and len(line) > 3:
                # Check if line starts with a number (1., 2., 3., etc.)
                number_match = re.match(r'^\d+\.\s*(.+)', line)
                if number_match:
                    cleaned_line = number_match.group(1).strip()
                    if cleaned_line:
                        missing_info.append(cleaned_line)
        
        return missing_info

    def _extract_additional_searches(self, response: str) -> List[str]:
        """Extract additional search suggestions from the agent's response."""
        searches = []
        lines = response.split('\n')
        
        in_searches_section = False
        for line in lines:
            line = line.strip()
            
            # Start capturing when we see the additional searches section
            if "what additional searches" in line.lower():
                in_searches_section = True
                continue
            
            # Extract numbered search requests with quotes in the searches section
            if in_searches_section and line and len(line) > 3:
                # Check if line starts with a number (1., 2., 3., etc.) and contains quotes
                number_match = re.match(r'^\d+\.\s*"([^"]+)"', line)
                if number_match:
                    search_text = number_match.group(1).strip()
                    if search_text:
                        searches.append(search_text)
        
        return searches


    async def process_search_validation(self, search_agent_response: str, lawyer_question: str) -> Dict[str, Any]:
        """
        Main processing function that validates search response and returns validation results.
        """
        validation_request = SearchValidationRequest(
            search_agent_response=search_agent_response,
            lawyer_question=lawyer_question
        )
        
        # Validate the search response
        validation_result = await self.validate_search_response(validation_request)
        
        # Return validation results - the orchestrator will handle additional searches if needed
        return {
            "validation": validation_result.model_dump()
        }


async def main():
    """Main function for testing the expert agent."""
    expert = ExpertAgent()
    
    # Example realistic lawyer case questions and search agent responses
    test_cases = [
        {
            "question": "I want to have a deposition in this case, based on the context of the case - what should I ask the defendant?",
            "search_response": "The defendant is John Smith, CEO of ABC Corp. He was involved in the contract negotiations in March 2023."
        },
        {
            "question": "What is this case about?",
            "search_response": "This is a breach of contract case filed on June 15, 2023. The plaintiff claims non-payment of $50,000 for services rendered."
        },
        {
            "question": "Who are the main people, places, roles and main timelines in the case?",
            "search_response": "Plaintiff: Jane Doe (consultant). Defendant: ABC Corp. Contract signed March 1, 2023. Services completed May 30, 2023."
        }
    ]
    
    print("Legal Search Validation Agent - Test Cases")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTEST CASE {i}:")
        print(f"Lawyer's Question: {test_case['question']}")
        print(f"Search Agent Response: {test_case['search_response']}")
        print("-" * 50)
        
        result = await expert.process_search_validation(test_case['search_response'], test_case['question'])
        
        print("Validation Result:")
        print(f"Complete: {result['validation']['is_complete']}")
        print(f"Missing Information: {result['validation']['missing_information']}")
        print(f"Additional Searches Needed: {result['validation']['additional_searches_needed']}")
        
        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
