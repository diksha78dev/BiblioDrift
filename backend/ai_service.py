# AI service logic with LLM integration (OpenAI/Gemini)
# Implements 'generate_book_note' and 'get_ai_recommendations'. All recommendations MUST be AI-based.
# Enhanced with comprehensive caching for expensive operations

import os
import logging
from typing import Optional

# Import caching decorators
from cache_service import (
    cache_recommendations, 
    cache_mood_tags, 
    cache_chat_response,
    cache_mood_analysis
)

# Setup logging from environment
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Try to import LLM clients
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Try to import mood analysis
try:
    from mood_analysis.ai_service_enhanced import get_book_mood_tags, generate_enhanced_book_note
    MOOD_ANALYSIS_AVAILABLE = True
except ImportError:
    MOOD_ANALYSIS_AVAILABLE = False

# Setup logger
logger = logging.getLogger(__name__)

# Import custom exceptions
from exceptions import (
    LLMRateLimitError, LLMTimeoutError, LLMConnectionError, 
    LLMAuthenticationError, LLMCircuitBreakerOpenError, AIServiceException
)
from time import time
from datetime import datetime, timedelta

class CircuitBreaker:
    """
    Circuit breaker pattern for LLM service to prevent cascading failures.
    Monitors error rates and temporarily disables the service when failures exceed threshold.
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 success_threshold: int = 2,
                 timeout_seconds: int = 300):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes needed to close circuit
            timeout_seconds: Time before attempting to half-open circuit
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def record_success(self):
        """Record a successful LLM call."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "CLOSED"
                self.success_count = 0
                logger.info(f"Circuit breaker CLOSED - LLM service recovered")
    
    def record_failure(self, error_type: str):
        """Record a failed LLM call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        self.success_count = 0
        
        logger.warning(f"LLM failure recorded ({self.failure_count}/{self.failure_threshold}): {error_type}")
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(f"Circuit breaker OPEN - LLM service disabled due to {self.failure_count} failures")
    
    def can_attempt(self) -> bool:
        """Check if an LLM call can be attempted."""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            # Check if timeout has passed to try half-open state
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed > self.timeout_seconds:
                    self.state = "HALF_OPEN"
                    logger.info(f"Circuit breaker HALF_OPEN - attempting recovery")
                    return True
            return False
        
        if self.state == "HALF_OPEN":
            return True
        
        return False
    
    def get_state_info(self) -> dict:
        """Get current circuit breaker state info."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


class PromptTemplates:
    """Configurable prompt templates for different use cases."""
    
    @staticmethod
    def get_book_note_prompt(title: str, author: str, description: str, mood_context: str = "", vibe: str = "") -> str:
        """Generate book note prompt template with vibe support."""
        template = os.getenv('BOOK_NOTE_PROMPT_TEMPLATE', 
            """You are a cozy, knowledgeable bookseller in a quiet shop. A customer is looking for a book recommendation based on their current vibe: "{vibe}".

Book: "{title}" by {author}
Description: {description}
{mood_context}

IMPORTANT: Do NOT use hardcoded lists. Generate a recommendation dynamically based purely on the provided vibe: "{vibe}".

Output a JSON object with the following structure:
{{
  "title": "A compelling book title that matches the vibe",
  "author": "Author name that fits the recommendation", 
  "cover_url": "URL or placeholder for book cover image",
  "bookseller_note": "A warm, 3-4 sentence paragraph describing the reading experience for this specific vibe"
}}

Constraint: Keep the bookseller_note under 50 words and make it feel personal and atmospheric.
Style: Warm, insightful, like a trusted bookseller sharing a hidden gem.""")
        
        max_words = os.getenv('BOOK_NOTE_MAX_WORDS', '30')
        
        return template.format(
            title=title,
            author=author, 
            description=description,
            mood_context=mood_context,
            vibe=vibe,
            max_words=max_words
        )
    
    @staticmethod
    def get_recommendation_prompt(query: str) -> str:
        """Generate recommendation prompt template."""
        template = os.getenv('RECOMMENDATION_PROMPT_TEMPLATE',
            """You are a knowledgeable librarian helping someone find books.
            
User is looking for: "{query}"

Provide book recommendation guidance that captures the mood and feeling they're seeking.
Focus on the emotional experience and atmosphere rather than specific titles.
Keep response under {max_words} words and make it warm and helpful.
Style: Personal, insightful, like talking to a trusted book friend.""")
        
        max_words = os.getenv('RECOMMENDATION_MAX_WORDS', '100')
        
        return template.format(query=query, max_words=max_words)

class LLMService:
    """
    Production-grade LLM service supporting OpenAI, Groq, and Google Gemini.
    All configuration via environment variables.
    Includes circuit breaker for resilience and health monitoring.
    """
    
    def __init__(self):
        self.openai_client = None
        self.groq_client = None
        self.gemini_client = None
        self.preferred_llm = os.getenv('PREFERRED_LLM', 'groq').lower()
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=int(os.getenv('LLM_CIRCUIT_FAILURE_THRESHOLD', '5')),
            success_threshold=int(os.getenv('LLM_CIRCUIT_SUCCESS_THRESHOLD', '2')),
            timeout_seconds=int(os.getenv('LLM_CIRCUIT_TIMEOUT', '300'))
        )
        
        # Configuration from environment
        self.config = {
            'openai_model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
            'openai_temperature': float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
            'openai_max_tokens': int(os.getenv('OPENAI_MAX_TOKENS', '150')),
            'groq_model': os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b'),
            'groq_temperature': float(os.getenv('GROQ_TEMPERATURE', '0.7')),
            'groq_max_tokens': int(os.getenv('GROQ_MAX_TOKENS', '150')),
            'gemini_model': os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'),
            'gemini_temperature': float(os.getenv('GEMINI_TEMPERATURE', '0.7')),
            'gemini_max_tokens': int(os.getenv('GEMINI_MAX_TOKENS', '150')),
            'default_max_tokens': int(os.getenv('DEFAULT_MAX_TOKENS', '150')),
            'book_note_max_tokens': int(os.getenv('BOOK_NOTE_MAX_TOKENS', '100')),
            'recommendation_max_tokens': int(os.getenv('RECOMMENDATION_MAX_TOKENS', '150')),
            'test_max_tokens': int(os.getenv('TEST_MAX_TOKENS', '10'))
        }
        
        self._setup_openai()
        self._setup_groq()
        self._setup_gemini()
        
    def _setup_openai(self):
        """Setup OpenAI client if API key available."""
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key and OPENAI_AVAILABLE:
            try:
                # Test if we can create a client
                from openai import OpenAI
                OpenAI(api_key=api_key)  # Test client creation
                self.openai_client = True  # Just mark as available
                logger.info(f"OpenAI client initialized with model: {self.config['openai_model']}")
            except Exception as e:
                logger.error(f"Failed to setup OpenAI: {e}")
    def _setup_groq(self):
        """Setup Groq client if API key available."""
        api_key = os.getenv('GROQ_API_KEY')
        if api_key and GROQ_AVAILABLE:
            try:
                self.groq_client = Groq(api_key=api_key)
                logger.info(f"Groq client initialized with model: {self.config['groq_model']}")
            except Exception as e:
                logger.error(f"Failed to setup Groq: {e}")
                self.groq_client = None
                
    def _setup_gemini(self):
        """Setup Gemini client if API key available."""
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key and GEMINI_AVAILABLE:
            try:
                self.gemini_client = genai.Client(api_key=api_key)
                logger.info(f"Gemini client initialized. configured model: {self.config['gemini_model']}")
            except ImportError as e:
                logger.warning(f"Google GenAI library not installed: {e}. Install with: pip install google-genai")
                self.gemini_client = None
            except ValueError as e:
                logger.error(f"Invalid Gemini API key configuration: {e}")
                self.gemini_client = None
            except Exception as e:
                logger.error(f"Failed to setup Gemini: {e}", exc_info=True)
                self.gemini_client = None
    
    def is_available(self) -> bool:
        """Check if any LLM service is available."""
        return (self.openai_client is not None) or (self.groq_client is not None) or (self.gemini_client is not None)
    
    def generate_text(self, prompt: str, max_tokens: Optional[int] = None, retry_count: int = 0) -> Optional[str]:
        """
        Generate text using available LLM service with retry logic and circuit breaker.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate (uses config default if None)
            retry_count: Current retry attempt
            
        Returns:
            Generated text or None if failed
            
        Raises:
            LLMCircuitBreakerOpenError: If circuit breaker is open
        """
        if not self.is_available():
            logger.warning("No LLM service available")
            return None
        
        # Check circuit breaker
        if not self.circuit_breaker.can_attempt():
            circuit_state = self.circuit_breaker.get_state_info()
            logger.error(f"Circuit breaker is {circuit_state['state']} - LLM service unavailable")
            raise LLMCircuitBreakerOpenError(
                f"LLM service degraded ({circuit_state['failure_count']} failures). Retry after {self.circuit_breaker.timeout_seconds}s"
            )
            
        if max_tokens is None:
            max_tokens = self.config['default_max_tokens']
            
        max_retries = int(os.getenv('LLM_MAX_RETRIES', '3'))
        
        try:
            # Try preferred LLM first
            if self.preferred_llm == 'openai' and self.openai_client:
                result = self._generate_with_openai(prompt, max_tokens)
            elif self.preferred_llm == 'groq' and self.groq_client:
                result = self._generate_with_groq(prompt, max_tokens)
            elif self.preferred_llm == 'gemini' and self.gemini_client:
                result = self._generate_with_gemini(prompt, max_tokens)
            else:
                # Fallback to any available LLM (priority: Groq > OpenAI > Gemini)
                if self.groq_client:
                    result = self._generate_with_groq(prompt, max_tokens)
                elif self.openai_client:
                    result = self._generate_with_openai(prompt, max_tokens)
                elif self.gemini_client:
                    result = self._generate_with_gemini(prompt, max_tokens)
                else:
                    logger.error("No LLM clients available after fallback check")
                    return None
            
            # Success - reset circuit breaker
            if result:
                self.circuit_breaker.record_success()
            
            return result
                
        except LLMRateLimitError as e:
            logger.warning(f"LLM rate limited (attempt {retry_count + 1}/{max_retries + 1}): {e}")
            self.circuit_breaker.record_failure("RATE_LIMIT")
            
            if retry_count < max_retries:
                import time
                backoff_delay = e.retry_after if hasattr(e, 'retry_after') else (2 ** (retry_count + 1))
                logger.info(f"Retrying after {backoff_delay}s")
                time.sleep(min(backoff_delay, 30))  # Cap backoff at 30s
                return self.generate_text(prompt, max_tokens, retry_count + 1)
            return None
            
        except (LLMTimeoutError, LLMConnectionError) as e:
            logger.warning(f"LLM transient error (attempt {retry_count + 1}/{max_retries + 1}): {type(e).__name__}: {e}")
            self.circuit_breaker.record_failure(type(e).__name__)
            
            if retry_count < max_retries:
                import time
                retry_delay = float(os.getenv('LLM_RETRY_DELAY', '1.0'))
                time.sleep(retry_delay * (retry_count + 1))  # Exponential backoff
                return self.generate_text(prompt, max_tokens, retry_count + 1)
            return None
            
        except LLMAuthenticationError as e:
            logger.error(f"LLM authentication failed - check API credentials: {e}")
            self.circuit_breaker.record_failure("AUTH_ERROR")
            return None
            
        except AIServiceException as e:
            logger.error(f"LLM service error: {type(e).__name__}: {e}")
            self.circuit_breaker.record_failure(type(e).__name__)
            return None
            
        except Exception as e:
            logger.error(f"Unexpected LLM error (attempt {retry_count + 1}): {type(e).__name__}: {e}", exc_info=True)
            self.circuit_breaker.record_failure("UNEXPECTED_ERROR")
            
            # Retry on unknown transient errors only
            if retry_count < max_retries and self._is_retryable_error(e):
                import time
                retry_delay = float(os.getenv('LLM_RETRY_DELAY', '1.0'))
                time.sleep(retry_delay * (retry_count + 1))
                return self.generate_text(prompt, max_tokens, retry_count + 1)
            
            return None
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if error is retryable (network, rate limit, etc.)."""
        error_str = str(error).lower()
        retryable_errors = [
            'rate limit',
            'timeout',
            'connection',
            'network',
            'service unavailable',
            'internal server error'
        ]
        return any(err in error_str for err in retryable_errors)
    
    def _generate_with_openai(self, prompt: str, max_tokens: int) -> Optional[str]:
        """Generate text using OpenAI with specific exception handling."""
        try:
            # Use the new OpenAI client API (v1.0+)
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            response = client.chat.completions.create(
                model=self.config['openai_model'],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=min(max_tokens, self.config['openai_max_tokens']),
                temperature=self.config['openai_temperature']
            )
            return response.choices[0].message.content.strip()
        except ImportError as e:
            logger.error(f"OpenAI library not installed: {e}")
            raise LLMConnectionError(f"OpenAI client unavailable: {str(e)}")
        except ValueError as e:
            logger.error(f"Invalid OpenAI API key or configuration: {e}")
            raise LLMAuthenticationError(f"OpenAI authentication failed: {str(e)}")
        except Exception as e:
            error_type = type(e).__name__
            error_str = str(e).lower()
            
            if 'rate limit' in error_str or 'quota' in error_str:
                logger.warning(f"OpenAI rate limit: {e}")
                raise LLMRateLimitError(f"OpenAI rate limited: {str(e)}", retry_after=60)
            elif 'timeout' in error_str:
                logger.warning(f"OpenAI timeout: {e}")
                raise LLMTimeoutError(f"OpenAI request timed out: {str(e)}")
            elif 'connection' in error_str or 'network' in error_str:
                logger.warning(f"OpenAI connection error: {e}")
                raise LLMConnectionError(f"OpenAI connection failed: {str(e)}")
            else:
                logger.error(f"OpenAI generation failed: {error_type}: {e}", exc_info=True)
                raise AIServiceException(f"OpenAI error: {error_type}: {str(e)}")
    
    def _generate_with_groq(self, prompt: str, max_tokens: int) -> Optional[str]:
        """
        Generate text using Groq LLM service with specific exception handling.
        
        Args:
            prompt (str): The input text prompt for the model.
            max_tokens (int): Maximum number of tokens to generate.
            
        Returns:
            Optional[str]: The generated text response.
            
        Raises:
            LLMRateLimitError: If rate limit exceeded
            LLMTimeoutError: If request times out
            LLMConnectionError: If connection fails
            LLMAuthenticationError: If authentication fails
        """
        try:
            response = self.groq_client.chat.completions.create(
                model=self.config['groq_model'],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=min(max_tokens, self.config['groq_max_tokens']),
                temperature=self.config['groq_temperature']
            )
            return response.choices[0].message.content.strip()
        except ImportError as e:
            logger.error(f"Groq library not installed: {e}")
            raise LLMConnectionError(f"Groq client unavailable: {str(e)}")
        except ValueError as e:
            logger.error(f"Invalid Groq API key or configuration: {e}")
            raise LLMAuthenticationError(f"Groq authentication failed: {str(e)}")
        except Exception as e:
            error_type = type(e).__name__
            error_str = str(e).lower()
            
            if 'rate limit' in error_str or 'quota' in error_str:
                logger.warning(f"Groq rate limit: {e}")
                raise LLMRateLimitError(f"Groq rate limited: {str(e)}", retry_after=60)
            elif 'timeout' in error_str:
                logger.warning(f"Groq timeout: {e}")
                raise LLMTimeoutError(f"Groq request timed out: {str(e)}")
            elif 'connection' in error_str or 'network' in error_str:
                logger.warning(f"Groq connection error: {e}")
                raise LLMConnectionError(f"Groq connection failed: {str(e)}")
            else:
                logger.error(f"Groq generation failed: {error_type}: {e}", exc_info=True)
                raise AIServiceException(f"Groq error: {error_type}: {str(e)}")
    
    def _generate_with_gemini(self, prompt: str, max_tokens: int) -> Optional[str]:
        """
        Generate text using Google Gemini LLM service with specific exception handling.
        
        Args:
            prompt (str): The input text prompt for the model.
            max_tokens (int): Maximum number of tokens to generate.
            
        Returns:
            Optional[str]: The generated text response.
            
        Raises:
            LLMRateLimitError: If rate limit exceeded
            LLMTimeoutError: If request times out
            LLMConnectionError: If connection fails
            LLMAuthenticationError: If authentication fails
        """
        try:
            from google.genai import types
            response = self.gemini_client.models.generate_content(
                model=self.config['gemini_model'],
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=min(max_tokens, self.config['gemini_max_tokens']),
                    temperature=self.config['gemini_temperature']
                )
            )
            return response.text.strip()
        except ImportError as e:
            logger.error(f"Google GenAI library not installed: {e}")
            raise LLMConnectionError(f"Gemini client unavailable: {str(e)}")
        except ValueError as e:
            logger.error(f"Invalid Gemini API key or configuration: {e}")
            raise LLMAuthenticationError(f"Gemini authentication failed: {str(e)}")
        except Exception as e:
            error_type = type(e).__name__
            error_str = str(e).lower()
            
            if 'rate limit' in error_str or 'quota' in error_str:
                logger.warning(f"Gemini rate limit: {e}")
                raise LLMRateLimitError(f"Gemini rate limited: {str(e)}", retry_after=60)
            elif 'timeout' in error_str:
                logger.warning(f"Gemini timeout: {e}")
                raise LLMTimeoutError(f"Gemini request timed out: {str(e)}")
            elif 'connection' in error_str or 'network' in error_str:
                logger.warning(f"Gemini connection error: {e}")
                raise LLMConnectionError(f"Gemini connection failed: {str(e)}")
            else:
                logger.error(f"Gemini generation failed: {error_type}: {e}", exc_info=True)
                raise AIServiceException(f"Gemini error: {error_type}: {str(e)}")

# Initialize LLM service
llm_service = LLMService()

# Export for external use
__all__ = ['generate_book_note', 'get_ai_recommendations', 'get_book_mood_tags_safe', 'generate_chat_response', 'llm_service', 'LLMService', 'PromptTemplates']

def generate_book_note(description, title="", author="", vibe=""):
    """
    Generate book note using LLM with vibe-based recommendations.
    
    Args:
        description: Book description
        title: Book title
        author: Book author
        vibe: User's current vibe for recommendation
        
    Returns:
        Generated book recommendation as JSON object or fallback text
        
    Raises:
        LLMCircuitBreakerOpenError: If LLM circuit breaker is open
        AIServiceException: For other LLM service errors
    """
    # Try mood analysis first for context
    mood_context = ""
    if MOOD_ANALYSIS_AVAILABLE and title and author:
        try:
            enhanced_note = generate_enhanced_book_note(description, title, author)
            mood_context = f"Based on reader sentiment analysis: {enhanced_note}"
        except Exception as e:
            logger.debug(f"Mood analysis failed (non-fatal): {type(e).__name__}: {e}")
    
    # Use LLM if available
    if llm_service.is_available():
        try:
            prompt = PromptTemplates.get_book_note_prompt(title, author, description, mood_context, vibe)
            llm_response = llm_service.generate_text(prompt, llm_service.config['book_note_max_tokens'])
            
            if llm_response:
                # Try to parse as JSON first
                try:
                    import json
                    parsed_response = json.loads(llm_response)
                    if isinstance(parsed_response, dict) and all(key in parsed_response for key in ['title', 'author', 'bookseller_note']):
                        logger.info(f"Successfully generated structured recommendation for vibe: {vibe}")
                        return parsed_response
                except (json.JSONDecodeError, TypeError):
                    # Fallback to plain text if JSON parsing fails
                    logger.warning("LLM response was not valid JSON, using as plain text")
                    return {
                        "vibe": llm_response,
                        "title": title or "A Perfect Match",
                        "author": author or "Recommended Author"
                    }
                
        except (LLMRateLimitError, LLMTimeoutError, LLMConnectionError, LLMCircuitBreakerOpenError) as e:
            logger.warning(f"LLM transient error in generate_book_note: {type(e).__name__}: {e}")
            raise  # Let app handle it
        except AIServiceException as e:
            logger.error(f"LLM service error in generate_book_note: {e}")
            raise  # Let app handle it
        except Exception as e:
            logger.error(f"Unexpected error in LLM generation: {type(e).__name__}: {e}", exc_info=True)
            raise AIServiceException(f"Unexpected LLM error: {str(e)}")
    
    # Enhanced fallback with mood analysis
    if MOOD_ANALYSIS_AVAILABLE and title and author:
        try:
            return generate_enhanced_book_note(description, title, author)
        except Exception as e:
            logger.debug(f"Mood analysis fallback failed: {type(e).__name__}: {e}")
    
    # Basic fallback
    if len(description) > 200:
        return {"vibe": "A deep, complex narrative that readers find emotionally resonant."}
    elif len(description) > 100:
        return {"vibe": "A compelling story with layers waiting to be discovered."}
    elif "mystery" in description.lower():
        return {"vibe": "A mysterious tale that will keep you guessing."}
    elif "romance" in description.lower():
        return {"vibe": "A heartwarming story perfect for cozy reading."}
    else:
        return {"vibe": "A delightful read for any quiet moment."}

@cache_recommendations
def get_ai_recommendations(query):
    """
    Generate AI-powered book recommendations based on query.
    
    Args:
        query: User's search query or mood
        
    Returns:
        AI-generated recommendation text
        
    Raises:
        LLMCircuitBreakerOpenError: If LLM circuit breaker is open
        AIServiceException: For other LLM service errors
    """
    # Use LLM if available
    if llm_service.is_available():
        try:
            prompt = PromptTemplates.get_recommendation_prompt(query)
            llm_response = llm_service.generate_text(prompt, llm_service.config['recommendation_max_tokens'])
            if llm_response:
                return llm_response
                
        except (LLMRateLimitError, LLMTimeoutError, LLMConnectionError, LLMCircuitBreakerOpenError) as e:
            logger.warning(f"LLM transient error in get_ai_recommendations: {type(e).__name__}: {e}")
            raise  # Let app handle it
        except AIServiceException as e:
            logger.error(f"LLM service error in get_ai_recommendations: {e}")
            raise  # Let app handle it
        except Exception as e:
            logger.error(f"Unexpected error in LLM recommendations: {type(e).__name__}: {e}", exc_info=True)
            raise AIServiceException(f"Unexpected error generating recommendations: {str(e)}")
    
    # Fallback mood-based mapping
    mood_queries = {
        'cozy': 'comfort reads with warm atmosphere and gentle pacing',
        'dark': 'psychological thrillers with mysterious undertones',
        'romantic': 'love stories with emotional depth and chemistry',
        'mysterious': 'suspenseful tales with intriguing puzzles',
        'uplifting': 'inspiring stories that restore faith in humanity',
        'melancholy': 'literary fiction exploring complex emotions',
        'adventurous': 'epic journeys and thrilling escapades'
    }
    
    query_lower = query.lower()
    for mood, description in mood_queries.items():
        if mood in query_lower:
            return f"For {mood} reads, I'd suggest exploring {description}. These books tend to resonate with readers seeking that particular emotional experience."
    
    return f"Based on your interest in '{query}', I'd recommend exploring books that capture similar themes and emotional resonance."

@cache_mood_tags
def get_book_mood_tags_safe(title: str, author: str = "") -> list:
    """
    Safe wrapper for getting book mood tags.
    
    Args:
        title: Book title
        author: Author name
        
    Returns:
        List of mood tags or empty list if not available
        
    Raises:
        AIServiceException: For mood analysis errors
    """
    if MOOD_ANALYSIS_AVAILABLE:
        try:
            return get_book_mood_tags(title, author)
        except Exception as e:
            logger.error(f"Error getting mood tags for {title}: {type(e).__name__}: {e}", exc_info=True)
            # Return empty list for graceful degradation
    
    return []


def build_session_memory(conversation_history: list, max_items: int = 12) -> str:
    """
    Build a lightweight session memory summary from recent conversation history.
    This function extracts user preferences, repeated moods, favorite genres/authors,
    and recent book mentions to include as context for follow-up responses.

    The summary is intentionally conservative and deterministic (no extra LLM calls),
    so it can be used safely in prompts.
    """
    if not conversation_history:
        return ""

    recent = conversation_history[-max_items:]
    prefs = set()
    authors = set()
    titles = set()

    mood_keywords = [
        'cozy', 'comfort', 'romance', 'mystery', 'thriller', 'dark', 'uplifting',
        'melancholy', 'adventure', 'fantasy', 'science fiction', 'sci-fi', 'historical',
        'literary', 'non-fiction', 'biography', 'memoir'
    ]

    for msg in recent:
        try:
            text = ''
            if isinstance(msg, dict):
                text = (msg.get('content') or '')
            else:
                text = str(msg)

            text_low = text.lower()
            # detect mood keywords
            for k in mood_keywords:
                if k in text_low:
                    prefs.add(k)

            # detect quoted titles (simple heuristic)
            import re
            for match in re.findall(r'"([^"]+)"', text):
                if len(match.split()) <= 8:
                    titles.add(match.strip())

            # detect 'by <Author>' patterns
            for match in re.findall(r'by\s+([A-Z][\w\s\-\.]+)', text):
                authors.add(match.strip())

        except Exception:
            continue

    parts = []
    if prefs:
        parts.append('preferred_moods: ' + ', '.join(sorted(prefs)))
    if authors:
        parts.append('favorite_authors: ' + ', '.join(sorted(authors)))
    if titles:
        parts.append('recent_books_mentioned: ' + ', '.join(sorted(titles)))

    return ' | '.join(parts)

@cache_chat_response
def generate_chat_response(user_message, conversation_history=[]):
    """
    Generate truly AI-driven chat responses for the bookseller interface.
    Returns generic, non-hardcoded responses that rely on the frontend to provide context.
    
    Args:
        user_message: The user's current message
        conversation_history: Previous conversation messages
        
    Returns:
        String response from the bookseller
        
    Raises:
        LLMCircuitBreakerOpenError: If LLM circuit breaker is open
        AIServiceException: For other LLM service errors
    """
    # Build lightweight session memory summary from recent conversation
    session_memory = build_session_memory(conversation_history)

    # Use LLM if available for more natural, context-aware responses
    if llm_service.is_available():
        try:
            # More structured system prompt that includes session memory and instructions
            system_prompt = (
                "You are a warm, knowledgeable personal bookseller assistant. Use the session memory to answer follow-up questions, "
                "and prefer concise, personalized recommendations. Do NOT invent facts or make up authors. If unsure, ask a clarifying question."
            )

            memory_note = f"Session memory: {session_memory}" if session_memory else "Session memory: none"

            prompt = (
                f"{system_prompt}\n{memory_note}\n"
                f"Conversation history (most recent first): {conversation_history[-6:]}\n"
                f"Customer: '{user_message}'\n"
                "Respond warmly in under 60 words. If the user asks for books, prefer asking clarifying follow-ups when necessary, otherwise suggest 3 short options with one-sentence rationale."
            )

            llm_response = llm_service.generate_text(prompt, llm_service.config['recommendation_max_tokens'])
            if llm_response:
                return llm_response
        except (LLMRateLimitError, LLMTimeoutError, LLMConnectionError, LLMCircuitBreakerOpenError) as e:
            logger.warning(f"LLM transient error in generate_chat_response: {type(e).__name__}: {e}")
            # Fall through to fallback response, don't raise for chat
        except AIServiceException as e:
            logger.error(f"LLM service error in generate_chat_response: {e}")
            # Fall through to fallback response, don't raise for chat
        except Exception as e:
            logger.error(f"Unexpected error in LLM chat response: {type(e).__name__}: {e}", exc_info=True)
            # Fall through to fallback response, don't raise for chat
    
    # Simple fallback response
    return "I'd be happy to help you find the perfect book! Let me search for some great recommendations based on what you're looking for."