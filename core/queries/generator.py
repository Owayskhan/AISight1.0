from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from core.models.main import Queries
from core.utils.query_distribution import get_query_distribution, get_distribution_summary
from dotenv import load_dotenv
load_dotenv(override=True)
from core.prompts.query_generation import query_generation_system_prompt
from core.config import ModelConfig
import logging

logger = logging.getLogger(__name__)


def create_intent_specific_prompt(intent_type: str, query_count: int, **kwargs):
    """
    Create a simplified, intent-specific prompt for faster parallel generation
    """
    from langchain_core.prompts import ChatPromptTemplate
    
    # Intent-specific descriptions
    intent_descriptions = {
        "navigational": "Direct brand searches and specific product lookups (e.g., 'Nike Air Max', 'Apple iPhone 15')",
        "informational": "Educational and how-to queries seeking general information (e.g., 'how to choose running shoes', 'what is sustainable fashion')",
        "commercial": "Product comparison and research queries (e.g., 'best smartphones 2024', 'Nike vs Adidas running shoes')",
        "transactional": "Purchase-intent queries ready to buy (e.g., 'buy iPhone 15 online', 'Nike store near me')",
        "awareness": "Problem recognition and category discovery (e.g., 'why do I need running shoes', 'sustainable clothing brands')",
        "consideration": "Solution evaluation and brand comparison (e.g., 'top eco-friendly brands', 'best value laptops')"
    }
    
    # Create simplified prompt for this specific intent
    intent_prompt = f"""You are an expert at generating realistic search queries that users type into search engines.

TASK: Generate exactly {query_count} {intent_type} search queries for the {kwargs.get('product_category', 'product')} category.

INTENT FOCUS: {intent_descriptions.get(intent_type, intent_type)}

AUDIENCE: {kwargs.get('audience_description', 'General consumers')}

BRAND CONTEXT: {kwargs.get('brand_summary', 'No specific brand focus')}

REQUIREMENTS:
- Generate exactly {query_count} unique queries
- All queries must have intent: "{intent_type}"
- Queries should be natural, realistic searches that real users would type
- Include variety in query length and phrasing
- Consider different user personas (novice, enthusiast, budget-conscious, etc.)
- Include different locales if relevant: {kwargs.get('locales', ['en-US'])}

CUSTOM INSTRUCTIONS: {kwargs.get('custom_instructions', 'None')}

FORMAT: Return a JSON object with "queries" array containing QueryItem objects.
Each QueryItem must have: query, intent, sub_intent, persona, category, expected_brand_relevance, locale, notes.

Generate {query_count} {intent_type} queries now:"""

    return ChatPromptTemplate.from_template(intent_prompt)


def create_product_intent_prompt(intent_type: str, query_count: int, **kwargs):
    """
    Create a simplified, intent-specific prompt for product query generation
    """
    from langchain_core.prompts import ChatPromptTemplate
    
    # Intent-specific descriptions for products
    intent_descriptions = {
        "navigational": f"Direct searches for the specific product '{kwargs.get('product_name', 'product')}' and its variations",
        "informational": f"Educational queries about '{kwargs.get('product_name', 'product')}' specifications, features, and how-to information",
        "commercial": f"Comparison and research queries involving '{kwargs.get('product_name', 'product')}' vs competitors",
        "transactional": f"Purchase-intent queries to buy '{kwargs.get('product_name', 'product')}' online or in stores",
        "awareness": f"Problem recognition queries where '{kwargs.get('product_name', 'product')}' could be a solution",
        "consideration": f"Evaluation queries comparing '{kwargs.get('product_name', 'product')}' with similar products"
    }
    
    # Create simplified prompt for this specific intent and product
    intent_prompt = f"""You are an expert at generating realistic search queries that users type into search engines when looking for products.

TASK: Generate exactly {query_count} {intent_type} search queries for the product: "{kwargs.get('product_name', 'product')}"

PRODUCT DETAILS:
- Name: {kwargs.get('product_name', 'Unknown product')}
- Description: {kwargs.get('product_description', 'No description')}
- Type: {kwargs.get('product_type', 'Product')}

INTENT FOCUS: {intent_descriptions.get(intent_type, intent_type)}

AUDIENCE: {kwargs.get('audience_description', 'General consumers')}

REQUIREMENTS:
- Generate exactly {query_count} unique queries
- All queries must have intent: "{intent_type}"
- Queries should be natural, realistic searches that real users would type
- Include variety in query length and phrasing
- Consider different user personas (novice, enthusiast, budget-conscious, etc.)
- Focus specifically on the product: "{kwargs.get('product_name', 'product')}"

CUSTOM INSTRUCTIONS: {kwargs.get('custom_instructions', 'None')}

FORMAT: Return a JSON object with "queries" array containing QueryItem objects.
Each QueryItem must have: query, intent, sub_intent, persona, category, expected_brand_relevance, locale, notes.

Generate {query_count} {intent_type} queries for "{kwargs.get('product_name', 'product')}" now:"""

    return ChatPromptTemplate.from_template(intent_prompt)



async def generate_queries(
    product_category: str, 
    openai_api_key: str, 
    audience_description: Optional[str] = None, 
    locales: Optional[List[str]] = None, 
    brand_summary: Optional[str] = None,
    brand_products: Optional[str] = None,
    k: int = 30,
    custom_instructions: Optional[str] = None,
    user_intent: Optional[List[str]] = None
):
    # Calculate query distribution across intent categories
    if user_intent is not None:
        # Use user-specified intents
        from core.utils.query_distribution import get_user_intent_distribution
        distribution = get_user_intent_distribution(k, user_intent)
        distribution_summary = get_distribution_summary(distribution)
        logger.info(f"Query generation (user_intent={user_intent}): {distribution_summary}")
    else:
        # Use all intent types by default
        from core.utils.query_distribution import get_query_distribution
        distribution = get_query_distribution(k)
        distribution_summary = get_distribution_summary(distribution)
        logger.info(f"Query generation (all intents): {distribution_summary}")
    
    logger.info("🚀 Using parallel generation by intent for maximum speed")
    
    # Use fast GPT-4o-mini for parallel generation
    llm = ChatOpenAI(api_key=openai_api_key, model=ModelConfig.QUERY_GENERATION_MODEL, temperature=ModelConfig.DEFAULT_TEMPERATURE)

    # Create simplified intent-specific prompts for parallel generation
    intent_prompts = {}
    
    # Only generate for intents that have queries allocated
    active_intents = {intent: count for intent, count in distribution.items() if count > 0}
    
    logger.info(f"📊 Generating queries for {len(active_intents)} intent types: {list(active_intents.keys())}")
    
    # Create intent-specific generation functions
    async def generate_for_intent(intent_type: str, query_count: int):
        """Generate queries for a specific intent type"""
        logger.info(f"🎯 Generating {query_count} {intent_type} queries...")
        
        # Create simplified prompt for this specific intent
        intent_prompt = create_intent_specific_prompt(
            intent_type=intent_type,
            query_count=query_count,
            product_category=product_category,
            audience_description=audience_description,
            brand_summary=brand_summary,
            brand_products=brand_products,
            locales=locales,
            custom_instructions=custom_instructions
        )
        
        # Use structured output for consistent parsing
        from core.models.main import QueryItem
        from pydantic import BaseModel
        
        class IntentQueries(BaseModel):
            queries: List[QueryItem]
        
        intent_chain = intent_prompt | llm.with_structured_output(IntentQueries)
        
        try:
            result = await intent_chain.ainvoke({
                "product_category": product_category,
                "audience_description": audience_description or "General consumers",
                "brand_summary": brand_summary or "",
                "brand_products": brand_products or "",
                "locales": locales or ["en-US"],
                "custom_instructions": custom_instructions or "",
                "query_count": query_count,
                "intent_type": intent_type
            })
            
            logger.info(f"✅ Generated {len(result.queries)} {intent_type} queries")
            return result.queries
            
        except Exception as e:
            logger.error(f"❌ Failed to generate {intent_type} queries: {str(e)}")
            # Return empty list to not break the entire generation
            return []
    
    # Generate all intent types in parallel
    import asyncio
    
    generation_tasks = [
        generate_for_intent(intent_type, count) 
        for intent_type, count in active_intents.items()
    ]
    
    # Execute all intent generation tasks concurrently
    logger.info(f"⚡ Running {len(generation_tasks)} intent generations in parallel...")
    intent_results = await asyncio.gather(*generation_tasks, return_exceptions=True)
    
    # Combine all results
    all_queries = []
    for i, result in enumerate(intent_results):
        if isinstance(result, Exception):
            intent_type = list(active_intents.keys())[i]
            logger.error(f"❌ Intent generation failed for {intent_type}: {str(result)}")
        elif isinstance(result, list):
            all_queries.extend(result)
    
    logger.info(f"🎉 Parallel generation completed: {len(all_queries)} total queries generated")
    
    # Return in the expected format
    return {"queries": [query.model_dump() for query in all_queries]}


async def generate_missing_intent_queries(
    missing_intents: List[str],
    generation_distribution: Dict[str, int],
    product_category: str = None,
    product_name: str = None,
    product_description: str = None,
    product_type: str = None,
    openai_api_key: str = None,
    audience_description: Optional[str] = None,
    locales: Optional[List[str]] = None,
    brand_summary: Optional[str] = None,
    brand_products: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    is_product: bool = False
):
    """
    Generate queries for specific missing intents only (used in hybrid mode).
    
    Args:
        missing_intents: List of intent types that need queries generated
        generation_distribution: Dict with count per intent to generate
        product_category: Product category (for category-based generation)
        product_name: Product name (for product-based generation)
        product_description: Product description (for product-based generation)
        product_type: Product type (for product-based generation)
        openai_api_key: OpenAI API key
        audience_description: Target audience description
        locales: List of locales
        brand_summary: Brand summary
        brand_products: Brand products description
        custom_instructions: Custom generation instructions
        is_product: Whether this is product-specific generation
        
    Returns:
        Dict with generated queries for missing intents only
    """
    logger.info(f"🔧 Generating queries for missing intents: {missing_intents}")
    
    # Use fast GPT-4o-mini for parallel generation
    llm = ChatOpenAI(api_key=openai_api_key, model=ModelConfig.QUERY_GENERATION_MODEL, temperature=ModelConfig.DEFAULT_TEMPERATURE)

    # Only generate for intents that have queries allocated
    active_intents = {intent: count for intent, count in generation_distribution.items() if count > 0 and intent in missing_intents}
    
    if not active_intents:
        logger.info("🔧 No missing intents need generation")
        return {"queries": []}
    
    logger.info(f"📊 Generating missing intent queries: {list(active_intents.keys())}")
    
    # Create intent-specific generation functions
    async def generate_for_missing_intent(intent_type: str, query_count: int):
        """Generate queries for a specific missing intent type"""
        logger.info(f"🎯 Generating {query_count} {intent_type} queries to fill gap...")
        
        try:
            if is_product:
                # Use product-specific prompt for missing intent
                intent_prompt = create_product_intent_prompt(
                    intent_type=intent_type,
                    query_count=query_count,
                    product_name=product_name,
                    product_description=product_description,
                    product_type=product_type,
                    audience_description=audience_description,
                    custom_instructions=custom_instructions
                )
            else:
                # Use category-based prompt for missing intent
                intent_prompt = create_intent_specific_prompt(
                    intent_type=intent_type,
                    query_count=query_count,
                    product_category=product_category,
                    audience_description=audience_description,
                    brand_summary=brand_summary,
                    brand_products=brand_products,
                    locales=locales,
                    custom_instructions=custom_instructions
                )
            
            # Use structured output for consistent parsing
            from core.models.main import QueryItem
            from pydantic import BaseModel
            
            class IntentQueries(BaseModel):
                queries: List[QueryItem]
            
            intent_chain = intent_prompt | llm.with_structured_output(IntentQueries)
            
            # Prepare parameters based on generation type
            if is_product:
                params = {
                    "product_name": product_name or "product",
                    "product_description": product_description or "product description",
                    "product_type": product_type or "product",
                    "audience_description": audience_description or "General audience",
                    "custom_instructions": custom_instructions or "",
                    "query_count": query_count,
                    "intent_type": intent_type
                }
            else:
                params = {
                    "product_category": product_category or "general",
                    "audience_description": audience_description or "General consumers",
                    "brand_summary": brand_summary or "",
                    "brand_products": brand_products or "",
                    "locales": locales or ["en-US"],
                    "custom_instructions": custom_instructions or "",
                    "query_count": query_count,
                    "intent_type": intent_type
                }
            
            result = await intent_chain.ainvoke(params)
            
            logger.info(f"✅ Generated {len(result.queries)} {intent_type} queries to fill gap")
            return result.queries
            
        except Exception as e:
            logger.error(f"❌ Failed to generate {intent_type} missing queries: {str(e)}")
            # Return empty list to not break the entire generation
            return []
    
    # Generate all missing intent types in parallel
    import asyncio
    
    generation_tasks = [
        generate_for_missing_intent(intent_type, count) 
        for intent_type, count in active_intents.items()
    ]
    
    # Execute all intent generation tasks concurrently
    logger.info(f"⚡ Running {len(generation_tasks)} missing intent generations in parallel...")
    intent_results = await asyncio.gather(*generation_tasks, return_exceptions=True)
    
    # Combine all results
    all_queries = []
    for i, result in enumerate(intent_results):
        if isinstance(result, Exception):
            intent_type = list(active_intents.keys())[i]
            logger.error(f"❌ Missing intent generation failed for {intent_type}: {str(result)}")
        elif isinstance(result, list):
            all_queries.extend(result)
    
    logger.info(f"🎉 Missing intent generation completed: {len(all_queries)} queries generated for gaps")
    
    # Return in the expected format
    return {"queries": [query.model_dump() for query in all_queries]}


async def generate_product_queries(
    product_name: str,
    product_description: str,
    product_type: str,
    openai_api_key: str = None,
    audience_description: Optional[str] = None,
    k: int = 30,
    custom_instructions: Optional[str] = None,
    user_intent: Optional[List[str]] = None
):
    """Generate queries specific to a single product using parallel generation by intent"""
    # Calculate query distribution across intent categories
    if user_intent is not None:
        # Use user-specified intents
        from core.utils.query_distribution import get_user_intent_distribution
        distribution = get_user_intent_distribution(k, user_intent)
        distribution_summary = get_distribution_summary(distribution)
        logger.info(f"Product query generation (user_intent={user_intent}): {distribution_summary}")
    else:
        # Use all intent types by default
        from core.utils.query_distribution import get_query_distribution
        distribution = get_query_distribution(k)
        distribution_summary = get_distribution_summary(distribution)
        logger.info(f"Product query generation (all intents): {distribution_summary}")
    
    logger.info("🚀 Using parallel generation by intent for maximum speed")
    
    # Use fast GPT-4o-mini for parallel generation
    llm = ChatOpenAI(api_key=openai_api_key, model=ModelConfig.QUERY_GENERATION_MODEL, temperature=ModelConfig.DEFAULT_TEMPERATURE)

    # Only generate for intents that have queries allocated
    active_intents = {intent: count for intent, count in distribution.items() if count > 0}
    
    logger.info(f"📊 Generating product queries for {len(active_intents)} intent types: {list(active_intents.keys())}")
    
    # Create intent-specific generation functions for products
    async def generate_product_intent(intent_type: str, query_count: int):
        """Generate product queries for a specific intent type"""
        logger.info(f"🎯 Generating {query_count} {intent_type} product queries...")
        
        # Create simplified product-specific prompt for this intent
        intent_prompt = create_product_intent_prompt(
            intent_type=intent_type,
            query_count=query_count,
            product_name=product_name,
            product_description=product_description,
            product_type=product_type,
            audience_description=audience_description,
            custom_instructions=custom_instructions
        )
        
        # Use structured output for consistent parsing
        from core.models.main import QueryItem
        from pydantic import BaseModel
        
        class IntentQueries(BaseModel):
            queries: List[QueryItem]
        
        intent_chain = intent_prompt | llm.with_structured_output(IntentQueries)
        
        try:
            result = await intent_chain.ainvoke({
                "product_name": product_name,
                "product_description": product_description,
                "product_type": product_type,
                "audience_description": audience_description or "General audience",
                "custom_instructions": custom_instructions or "",
                "query_count": query_count,
                "intent_type": intent_type
            })
            
            logger.info(f"✅ Generated {len(result.queries)} {intent_type} product queries")
            return result.queries
            
        except Exception as e:
            logger.error(f"❌ Failed to generate {intent_type} product queries: {str(e)}")
            # Return empty list to not break the entire generation
            return []
    
    # Generate all intent types in parallel
    import asyncio
    
    generation_tasks = [
        generate_product_intent(intent_type, count) 
        for intent_type, count in active_intents.items()
    ]
    
    # Execute all intent generation tasks concurrently
    logger.info(f"⚡ Running {len(generation_tasks)} product intent generations in parallel...")
    intent_results = await asyncio.gather(*generation_tasks, return_exceptions=True)
    
    # Combine all results
    all_queries = []
    for i, result in enumerate(intent_results):
        if isinstance(result, Exception):
            intent_type = list(active_intents.keys())[i]
            logger.error(f"❌ Product intent generation failed for {intent_type}: {str(result)}")
        elif isinstance(result, list):
            all_queries.extend(result)
    
    logger.info(f"🎉 Parallel product generation completed: {len(all_queries)} total queries generated")
    
    # Return in the expected format
    return {"queries": [query.model_dump() for query in all_queries]}