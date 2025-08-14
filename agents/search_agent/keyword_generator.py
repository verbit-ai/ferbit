import logging
import asyncio
import openai
from rate_limiter import openai_rate_limiter

logger = logging.getLogger(__name__)

async def generate_legal_keywords(query: str) -> str:
    """
    Generate extensive keywords for legal deposition and case document searches.
    Uses LLM to expand the query with relevant legal terminology and synonyms.
    
    Args:
        query: The search query to generate legal keywords for
        
    Returns:
        A space-separated list of legal keywords and synonyms
    """
    try:
        logger.info(f"[KEYWORD_GEN] Starting keyword generation for query: {query}")
        print(f"[DEBUG] Starting keyword generation for query: {query}")
        
        keyword_prompt = f"""Generate 10 legal keywords for: "{query}"

Include: original terms, legal synonyms, variations, procedural terms.

Output: space-separated keywords only."""

        logger.info(f"[KEYWORD_GEN] About to call OpenAI directly with prompt: {keyword_prompt}")
        print(f"[DEBUG] About to call OpenAI directly...")
        
        # Direct OpenAI API call with enhanced rate limiting and backoff
        client = openai.AsyncOpenAI()
        
        async def make_openai_call():
            return await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "user", "content": keyword_prompt}
                    ],
                    temperature=0
                ),
                timeout=30.0  # 30 second timeout
            )
        
        response = await openai_rate_limiter.call_with_backoff(make_openai_call)
        
        keywords = response.choices[0].message.content.strip()
        logger.info(f"[KEYWORD_GEN] LLM Output - Generated keywords: {keywords}")
        print(f"[DEBUG] Successfully generated keywords: {keywords}")
        return keywords
        
    except asyncio.TimeoutError as e:
        fallback_keywords = f"{query} legal case deposition testimony evidence witness court document legal proceeding"
        logger.warning(f"[KEYWORD_GEN] Keyword generation timed out: {e}, using fallback: {fallback_keywords}")
        print(f"[DEBUG] Keyword generation timed out: {e}, using fallback")
        return fallback_keywords
    except Exception as e:
        fallback_keywords = f"{query} legal case deposition testimony evidence witness court document legal proceeding"
        logger.error(f"[KEYWORD_GEN] Error generating legal keywords: {type(e).__name__}: {e}, using fallback: {fallback_keywords}")
        print(f"[DEBUG] Error generating legal keywords: {type(e).__name__}: {e}")
        # Fallback to basic query expansion
        return fallback_keywords