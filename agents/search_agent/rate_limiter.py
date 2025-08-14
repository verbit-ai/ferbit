import asyncio
import time
import logging
from typing import Optional, Callable, Any
import openai
from functools import wraps

logger = logging.getLogger(__name__)

class EnhancedRateLimiter:
    """Enhanced rate limiter with exponential backoff for 429 errors"""
    
    def __init__(self, delay_seconds: float = 5.0):
        """
        Initialize rate limiter
        
        Args:
            delay_seconds: Minimum seconds between requests (default: 5.0 for TPM limits)
        """
        self.delay_seconds = delay_seconds
        self.last_request_time: Optional[float] = None
        self._lock = asyncio.Lock()
        
    async def wait_if_needed(self):
        """Wait if needed to respect rate limits"""
        async with self._lock:
            current_time = time.time()
            
            if self.last_request_time is not None:
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.delay_seconds:
                    wait_time = self.delay_seconds - time_since_last
                    logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    
            self.last_request_time = time.time()
    
    async def call_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with exponential backoff on 429 errors"""
        max_retries = 3
        base_delay = 2.0
        
        for attempt in range(max_retries + 1):
            try:
                # Apply standard rate limiting first
                await self.wait_if_needed()
                
                # Call the function
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except (openai.RateLimitError, Exception) as e:
                # Check if it's a rate limit error (catch both openai.RateLimitError and HTTP 429)
                if not (isinstance(e, openai.RateLimitError) or '429' in str(e) or 'Too Many Requests' in str(e)):
                    # Not a rate limit error, re-raise
                    logger.error(f"Non-rate-limit error in call_with_backoff: {e}")
                    raise
                    
                if attempt == max_retries:
                    logger.error(f"Rate limit exceeded after {max_retries} retries: {e}")
                    raise
                
                # Extract suggested wait time from error message or use exponential backoff
                suggested_wait = self._extract_wait_time(str(e))
                wait_time = suggested_wait if suggested_wait else base_delay * (2 ** attempt)
                
                logger.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries + 1}), waiting {wait_time:.2f}s: {e}")
                await asyncio.sleep(wait_time)
    
    async def stream_with_backoff(self, async_gen_func: Callable, *args, **kwargs):
        """Stream from async generator with exponential backoff on 429 errors"""
        max_retries = 3
        base_delay = 2.0
        
        for attempt in range(max_retries + 1):
            try:
                # Apply standard rate limiting first
                await self.wait_if_needed()
                
                # Create and yield from the async generator
                async_gen = async_gen_func(*args, **kwargs)
                async for item in async_gen:
                    yield item
                return  # Success, exit retry loop
                    
            except (openai.RateLimitError, Exception) as e:
                # Check if it's a rate limit error (catch both openai.RateLimitError and HTTP 429)
                if not (isinstance(e, openai.RateLimitError) or '429' in str(e) or 'Too Many Requests' in str(e)):
                    # Not a rate limit error, re-raise
                    logger.error(f"Non-rate-limit error in stream_with_backoff: {e}")
                    raise
                    
                if attempt == max_retries:
                    logger.error(f"Rate limit exceeded after {max_retries} retries: {e}")
                    raise
                
                # Extract suggested wait time from error message or use exponential backoff
                suggested_wait = self._extract_wait_time(str(e))
                wait_time = suggested_wait if suggested_wait else base_delay * (2 ** attempt)
                
                logger.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries + 1}), waiting {wait_time:.2f}s: {e}")
                await asyncio.sleep(wait_time)
    
    def _extract_wait_time(self, error_message: str) -> Optional[float]:
        """Extract suggested wait time from OpenAI error message"""
        try:
            # Look for pattern like "Please try again in 2.476s"
            import re
            match = re.search(r'try again in ([\d.]+)s', error_message)
            if match:
                return float(match.group(1)) + 0.5  # Add small buffer
        except:
            pass
        return None

# Global rate limiter instance - increased delay for TPM limits
openai_rate_limiter = EnhancedRateLimiter(delay_seconds=15.0)  # 15 second delay for TPM limits