from core.models.main import BrandProfile
from core.utils.error_handling import (
    handle_api_error, async_retry, APIException, 
    parse_openai_error, parse_gemini_error, parse_perplexity_error,
    ExternalServiceError, ValidationError
)
from core.utils.rate_limiter import wait_for_rate_limit
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch
from dotenv import load_dotenv
load_dotenv(override=True)
from langchain_core.prompts import ChatPromptTemplate
import os
import asyncio
from langchain_core.output_parsers import PydanticOutputParser
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)
parser = PydanticOutputParser(pydantic_object=BrandProfile)

brand_profiler_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant that helps researching brand information for a brand. You have expertise in identifying the ICP of a brand and building a contextual profile for the brand."),
    ("user", "Research the brand {brand_name} using the website {brand_url} and build the brand's profile including ICP, products, summary, locale, and whether it is national or international.\n\nFormat the output in this format: {format_instructions}")
]).partial(format_instructions=parser.get_format_instructions())

@async_retry(
    retries=3,
    delay=2.0,
    exceptions=(APIException, Exception)
)
async def research_brand_info(
    brand_name: str, 
    brand_url: str, 
    api_keys: Dict[str, Optional[str]], 
    tavily_api_key: str = ""
) -> BrandProfile:
    """
    Research brand information using available LLM with comprehensive error handling.
    
    Args:
        brand_name: Name of the brand
        brand_url: Brand website URL
        api_keys: Dictionary with keys 'openai_api_key', 'gemini_api_key', 'perplexity_api_key'
        tavily_api_key: Optional Tavily API key for enhanced search
    
    Returns:
        BrandProfile object with brand information
        
    Raises:
        ValidationError: If invalid input parameters
        APIException: If API calls fail
        ExternalServiceError: If external services are unavailable
    """
    # Validate inputs
    if not brand_name or not brand_name.strip():
        raise ValidationError("Brand name is required", field="brand_name")
    
    if not brand_url or not brand_url.strip():
        raise ValidationError("Brand URL is required", field="brand_url")
    
    if not any(api_keys.get(key) for key in ['openai_api_key', 'gemini_api_key', 'perplexity_api_key']):
        raise ValidationError("At least one API key is required for brand profiling")
    
    # Determine which LLM to use based on available API keys
    model = None
    model_name = None
    api_service = None
    
    try:
        # Priority: Gemini > OpenAI > Perplexity
        if api_keys.get('gemini_api_key'):
            logger.info("Using Google Gemini for brand profiling")
            # Wait for rate limit before making request
            await wait_for_rate_limit('gemini', 1)
            
            model = init_chat_model(
                "gemini-2.5-flash", 
                model_provider="google_genai", 
                api_key=api_keys['gemini_api_key']
            )
            model_name = "Gemini"
            api_service = "gemini"
            
        elif api_keys.get('openai_api_key'):
            logger.info("Using OpenAI GPT-4 for brand profiling")
            # Wait for rate limit before making request
            await wait_for_rate_limit('openai', 1)
            
            model = init_chat_model(
                "gpt-4o-mini", 
                model_provider="openai", 
                api_key=api_keys['openai_api_key']
            )
            model_name = "OpenAI"
            api_service = "openai"
            
        elif api_keys.get('perplexity_api_key'):
            logger.info("Using Perplexity for brand profiling")
            # Wait for rate limit before making request
            await wait_for_rate_limit('perplexity', 1)
            
            # Perplexity uses OpenAI-compatible API
            model = init_chat_model(
                "perplexity:sonar", 
                api_key=api_keys['perplexity_api_key'],
            )
            model_name = "Perplexity"
            api_service = "perplexity"
            
        else:
            raise ValidationError("No valid API key provided for brand profiling")
        
        # Configure model with tools if Tavily is available
        logger.debug(f"Tavily API key received: '{tavily_api_key}' (length: {len(tavily_api_key)})")
        
        if tavily_api_key and tavily_api_key.strip():
            try:
                logger.info(f"Initializing Tavily search with API key: {tavily_api_key[:10]}...")
                search = TavilySearch(max_results=2, tavily_api_key=tavily_api_key)
                model_with_tools = model.bind_tools([search])
                model_w_structured_output = model_with_tools.with_structured_output(BrandProfile)
                logger.info("Enhanced brand profiling with Tavily search enabled")
            except Exception as e:
                error_msg = str(e) if str(e) else f"No error message (Exception type: {type(e).__name__})"
                logger.warning(f"Failed to initialize Tavily search: {error_msg}. Proceeding without search.")
                logger.debug(f"Tavily error details: {type(e).__name__}: {e}")
                model_w_structured_output = model.with_structured_output(BrandProfile)
        else:
            # Without Tavily, just use structured output
            logger.debug("No valid Tavily API key provided, using basic structured output")
            model_w_structured_output = model.with_structured_output(BrandProfile)
        
        # Create the chain
        chain = brand_profiler_prompt | model_w_structured_output
        
        # Make the API call with timeout
        logger.info(f"Starting brand profile generation for '{brand_name}' using {model_name}")
        
        try:
            # Run the chain with asyncio timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    chain.invoke,
                    {"brand_name": brand_name, "brand_url": brand_url}
                ),
                timeout=120.0  # 2 minute timeout
            )
            
            # Validate response
            if not response:
                raise ExternalServiceError(
                    f"Empty response from {model_name}",
                    service=api_service
                )
            
            # Validate that we got the expected fields
            if not hasattr(response, 'icp') or not hasattr(response, 'summary'):
                raise ExternalServiceError(
                    f"Invalid response format from {model_name}",
                    service=api_service
                )
            
            logger.info(f"✅ Brand profile generated successfully using {model_name}")
            logger.debug(f"Profile summary: {response.summary[:100]}...")
            
            return response
            
        except asyncio.TimeoutError:
            raise ExternalServiceError(
                f"Brand profiling timed out using {model_name}",
                service=api_service
            )
        
    except APIException:
        # Re-raise API exceptions as-is
        raise
    except Exception as e:
        # Handle and convert any other exceptions
        logger.error(f"Brand profiling failed with {model_name}: {str(e)}")
        
        # Try to parse service-specific errors
        if api_service:
            raise handle_api_error(e, api_service)
        else:
            raise ExternalServiceError(
                f"Brand profiling failed: {str(e)}",
                service="brand_profiler"
            )


async def research_brand_info_legacy(brand_name: str, brand_url: str, gemini_api_key: str, tavily_api_key: str = ""):
    """
    Legacy function signature for backward compatibility.
    Converts old parameters to new format and calls the updated function.
    """
    api_keys = {
        'gemini_api_key': gemini_api_key,
        'openai_api_key': None,
        'perplexity_api_key': None
    }
    return await research_brand_info(brand_name, brand_url, api_keys, tavily_api_key)


# Convenience function for backward compatibility with sync code
def research_brand_info_sync(
    brand_name: str, 
    brand_url: str, 
    api_keys: Dict[str, Optional[str]], 
    tavily_api_key: str = ""
) -> BrandProfile:
    """
    Synchronous wrapper for the async research_brand_info function.
    Only use this when you cannot use the async version.
    """
    return asyncio.run(research_brand_info(brand_name, brand_url, api_keys, tavily_api_key))