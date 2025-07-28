import logging
import asyncio
import openai

logger = logging.getLogger(__name__)

async def generate_legal_keywords(query: str) -> str:
    """
    Generate extensive keywords for legal deposition and case document searches.
    Uses LLM to expand the query with relevant legal terminology and synonyms.
    
    Args:
        query: The search query to generate legal keywords for
        
    Returns:
        A comma-separated list of legal keywords and synonyms
    """
    try:
        logger.info(f"[KEYWORD_GEN] Starting keyword generation for query: {query}")
        print(f"[DEBUG] Starting keyword generation for query: {query}")
        
        keyword_prompt = f"""You are a legal research assistant specializing in OpenSearch queries for legal cases and depositions.

Given the user query: "{query}"

Generate a comprehensive list of search keywords optimized for OpenSearch that would help find relevant legal documents, depositions, case files, and court records.

Consider the context of:
- Legal cases and litigation
- Deposition transcripts and testimony
- Court proceedings and legal documents
- Evidence and witness statements

For each concept in the query, provide:
1. The original terms
2. Legal synonyms and related terminology
3. Common variations and alternate spellings
4. Related procedural terms
5. Evidence and documentation keywords

Focus on terms that would likely appear in:
- Deposition transcripts
- Legal briefs and motions
- Court records and filings
- Witness testimony
- Expert reports
- Case documentation

IMPORTANT: Generate a maximum of the 20 most relevant keywords only.

Output format: comma-separated list of keywords only, no explanations."""

        logger.info(f"[KEYWORD_GEN] About to call OpenAI directly with prompt: {keyword_prompt}")
        print(f"[DEBUG] About to call OpenAI directly...")
        
        # Direct OpenAI API call with timeout
        client = openai.AsyncOpenAI()
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": keyword_prompt}
                ],
                temperature=0
            ),
            timeout=30.0  # 30 second timeout
        )
        
        keywords = response.choices[0].message.content.strip()
        logger.info(f"[KEYWORD_GEN] LLM Output - Generated keywords: {keywords}")
        print(f"[DEBUG] Successfully generated keywords: {keywords}")
        return keywords
        
    except asyncio.TimeoutError as e:
        fallback_keywords = f"{query}, legal case, deposition, testimony, evidence, witness, court document, legal proceeding"
        logger.warning(f"[KEYWORD_GEN] Keyword generation timed out: {e}, using fallback: {fallback_keywords}")
        print(f"[DEBUG] Keyword generation timed out: {e}, using fallback")
        return fallback_keywords
    except Exception as e:
        fallback_keywords = f"{query}, legal case, deposition, testimony, evidence, witness, court document, legal proceeding"
        logger.error(f"[KEYWORD_GEN] Error generating legal keywords: {type(e).__name__}: {e}, using fallback: {fallback_keywords}")
        print(f"[DEBUG] Error generating legal keywords: {type(e).__name__}: {e}")
        # Fallback to basic query expansion
        return fallback_keywords