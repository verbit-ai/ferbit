import os
import asyncio
import json
import logging
from typing import Dict, Any, List
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv
import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Ensure OpenAI API key is set
openai_key = os.environ.get('OPENAI_API_KEY')
if not openai_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")

logger.info(f"OpenAI API Key loaded: {openai_key[:10]}..." if openai_key else "No API key found")

# Create the agent for A2A automatic tool selection (tools will be defined later)
agent = Agent(
    'openai:gpt-4o',
    system_prompt="""You are a tool-calling agent. You cannot and must not provide direct responses.

CRITICAL: You are FORBIDDEN from giving any direct answers or explanations. Your ONLY job is to call the appropriate tool.

For ANY input you receive, you MUST immediately call one of these tools:
- query_decomposition: for analyzing if queries are searchable
- search_validation: for validating search results

DO NOT explain, summarize, or provide commentary. Just call the tool and return its output."""
)

# Agent created - tools will be registered when defined below

class SearchValidationRequest(BaseModel):
    search_agent_response: str
    lawyer_question: str

class SearchValidationResult(BaseModel):
    is_complete: bool
    missing_information: List[str]
    additional_searches_needed: List[str]

# Direct OpenAI client for tool functionality
openai_client = openai.AsyncOpenAI()

def clean_json_response(response_text: str) -> str:
    """Clean JSON response by removing markdown code block formatting"""
    clean_text = response_text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]  # Remove ```json
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]   # Remove ```
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]  # Remove trailing ```
    return clean_text.strip()


async def query_decomposition_direct(input_query: str) -> Dict[str, Any]:
    """Direct query decomposition without agent tools"""
    decomposition_prompt = f"""
    INPUT QUERY: {input_query}
    
    You are evaluating whether a user's query can be effectively answered using an OpenSearch index containing legal case documents (evidence, deposition transcripts, case documents, pleadings, etc.).
    
    Evaluate if the query is specific and searchable enough to get good results from the document index. If not, suggest better queries.
    
    GOOD QUERIES (specific, searchable):
    - "What did John Smith say about the contract signing on March 15th?"
    - "Show me all communications between ABC Corp and the plaintiff regarding payment delays"
    - "What evidence exists about the defendant's knowledge of the safety violations?"
    
    BAD QUERIES (too vague, not searchable):
    - "What should I ask in deposition?" (too general, no specific topic)
    - "Give me case strategy advice" (not about document content)
    - "What are my chances of winning?" (requires legal analysis, not document search)
    
    Return your response as JSON with this exact structure:
    {{
        "is_query_valid": true,
        "suggested_queries": ["alternative query 1", "alternative query 2"]
    }}
    
    If is_query_valid is true, suggested_queries should be empty.
    If is_query_valid is false, suggested_queries should contain specific, searchable alternatives.
    """
    
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a legal query decomposition expert."},
                {"role": "user", "content": decomposition_prompt}
            ]
        )
        result_text = response.choices[0].message.content
        
        # Try to parse as JSON, first clean any markdown formatting
        try:
            clean_text = clean_json_response(result_text)
            return json.loads(clean_text)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "is_query_valid": False,
                "suggested_queries": [f"Please rephrase: {input_query}"]
            }
    except Exception as e:
        logger.error(f"Error during query decomposition: {e}")
        return {
            "is_query_valid": False,
            "suggested_queries": [f"Error processing query: {input_query}"]
        }

async def search_validation_direct(search_agent_response: str, lawyer_question: str) -> Dict[str, Any]:
    """Direct search validation without agent tools"""
    validation_prompt = f"""
    LAWYER'S QUESTION: {lawyer_question}
    
    SEARCH RESULTS: {search_agent_response}
    
    You are evaluating whether the search results provide sufficient information (at least 80% complete) to answer the lawyer's question about this legal case.
    
    GOOD EXAMPLES (answered_in_full = true):
    - Question: "What did John Smith say about the contract?" 
      Results: "John Smith testified on May 15th that he reviewed the contract terms and found them acceptable..."
    - Question: "What communications exist about payment delays?"
      Results: "Found 5 emails between Jan-March showing ABC Corp requested payment extensions due to cash flow issues..."
    
    BAD EXAMPLES (answered_in_full = false):
    - Question: "What did John Smith say about the contract?"
      Results: "John Smith was deposed on May 15th" (missing what he actually said)
    - Question: "What evidence exists of safety violations?"
      Results: "There were several incidents reported" (too vague, no specific evidence)
    
    Return your response as JSON with this exact structure:
    {{
        "answered_in_full": true,
        "additional_queries_needed": ["specific query 1 to get missing info", "specific query 2"],
        "raw_response": "{search_agent_response}",
        "missing_information": "explanation of what key information is missing to fully answer the question"
    }}
    
    If answered_in_full is true, additional_queries_needed should be empty and missing_information should be empty.
    If answered_in_full is false, specify what's missing and suggest targeted queries to get that information.
    """
    
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a legal search validation expert."},
                {"role": "user", "content": validation_prompt}
            ]
        )
        result_text = response.choices[0].message.content
        
        # Try to parse as JSON, first clean any markdown formatting
        try:
            clean_text = clean_json_response(result_text)
            return json.loads(clean_text)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "answered_in_full": False,
                "additional_queries_needed": [lawyer_question],
                "raw_response": search_agent_response,
                "missing_information": "Could not parse validation response"
            }
    except Exception as e:
        logger.error(f"Error during search validation: {e}")
        return {
            "answered_in_full": False,
            "additional_queries_needed": [lawyer_question],
            "raw_response": search_agent_response,
            "missing_information": f"Search validation error: {str(e)}"
        }

# Separate tools for A2A automatic selection
@agent.tool
async def query_decomposition(ctx: RunContext, input_text: str) -> str:
    """
    Evaluates if user queries are valid for legal document search. Use this tool for ANY query evaluation.
    Input: plain text query or JSON with 'input_query' field.
    """
    logger.info("🔧 Query Decomposition selected")
    
    # Try to extract input query from JSON first, then fallback to plain text
    input_query = ""
    try:
        data = json.loads(input_text)
        input_query = data.get("input_query", data.get("lawyer_question", ""))  # Support both new and old field names
        if not input_query:
            # If JSON parsing worked but no input_query field, treat the whole input as the query
            input_query = input_text
    except json.JSONDecodeError:
        # If not JSON, treat the whole input as the query
        input_query = input_text
    
    if not input_query.strip():
        return json.dumps({"error": "No input query provided"})
        
    result = await query_decomposition_direct(input_query)
    return json.dumps(result)

@agent.tool  
async def search_validation(ctx: RunContext, input_text: str) -> str:
    """
    Validates if search results adequately answer questions. Use ONLY when input has both search results AND questions.
    Input: JSON with 'search_agent_response' and 'lawyer_question' fields.
    """
    logger.info("🔧 Search Validation selected")
    try:
        data = json.loads(input_text)
        search_agent_response = data.get("search_agent_response", "")
        lawyer_question = data.get("lawyer_question", "")
        
        if not search_agent_response or not lawyer_question:
            return json.dumps({"error": "Missing search_agent_response or lawyer_question field. Input must be JSON with both fields."})
        
        result = await search_validation_direct(search_agent_response, lawyer_question)
        return json.dumps(result, indent=2)
    except json.JSONDecodeError:
        logger.error("   ❌ JSON parsing error - input must be valid JSON with search_agent_response and lawyer_question fields")
        return json.dumps({"error": "Invalid JSON input - must contain search_agent_response and lawyer_question fields"})


# Compatibility wrapper class
class ExpertAgent:
    """Wrapper class to maintain compatibility with existing code"""
    
    def __init__(self):
        pass
    
    async def validate_search_response(self, validation_request: SearchValidationRequest) -> SearchValidationResult:
        result = await search_validation_direct(
            validation_request.search_agent_response,
            validation_request.lawyer_question
        )
        
        return SearchValidationResult(
            is_complete=result["is_complete"],
            missing_information=result["missing_information"],
            additional_searches_needed=result["additional_searches_needed"]
        )
    
    async def decompose_input_query(self, input_query: str) -> Dict[str, Any]:
        return await query_decomposition_direct(input_query)
    
    # Keep old method for backward compatibility
    async def decompose_lawyer_query(self, lawyer_question: str) -> Dict[str, Any]:
        return await query_decomposition_direct(lawyer_question)
    
    async def process_search_validation(self, search_agent_response: str, lawyer_question: str) -> Dict[str, Any]:
        validation_request = SearchValidationRequest(
            search_agent_response=search_agent_response,
            lawyer_question=lawyer_question
        )
        
        validation_result = await self.validate_search_response(validation_request)
        
        return {
            "validation": validation_result.model_dump()
        }

async def main():
    """Main function for testing the expert agent."""
    expert = ExpertAgent()
    
    # Test the problematic case
    test_question = "What is this case about and what are the key legal issues I should focus on?"
    logger.info(f"Testing: {test_question}")
    
    result = await expert.decompose_lawyer_query(test_question)
    logger.info(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())