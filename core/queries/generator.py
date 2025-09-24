from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional
from core.models.main import Queries
from core.utils.query_distribution import get_query_distribution, get_distribution_summary, get_plan_filtered_distribution
from dotenv import load_dotenv
load_dotenv(override=True)
from core.prompts.query_generation import query_generation_system_prompt
from core.config import ModelConfig
import logging

logger = logging.getLogger(__name__)


def get_plan_filtered_prompt(base_prompt: str, plan: str, is_product_prompt: bool = False) -> str:
    """
    Filter the query generation prompt based on subscription plan.
    
    For free plans, only include informational and awareness intent descriptions.
    For paid plans, include all intent types.
    """
    if plan == "free":
        if is_product_prompt:
            # Product-specific free intent section
            free_intent_section = """INTENT CLASSIFICATION (REQUIRED)
⚠️  IMPORTANT: You must generate EXACTLY {k} queries. This is critical.
Each query MUST be classified into exactly one of these two intent types:
- "informational": General information, specifications, how-to guides about the product
- "awareness": Discovery phase, learning what the product is and does"""
            
            # Find and replace the intent section for product prompts
            import re
            pattern = r"INTENT CLASSIFICATION \(REQUIRED\).*?(?=\n+STRICT CONSTRAINTS)"
            modified_prompt = re.sub(pattern, free_intent_section, base_prompt, flags=re.DOTALL)
        else:
            # Regular category-based free intent section
            free_intent_section = """INTENT LABELING (REQUIRED)
⚠️  IMPORTANT: You must generate EXACTLY {k} queries. This is critical.
- For each query, classify it into exactly one of these two intent types:
  * "informational": General information, how-to guides, educational content
  * "awareness": Discovery phase, learning about product categories or solutions"""
            
            # Find and replace the intent section
            import re
            pattern = r"INTENT LABELING \(REQUIRED\).*?(?=\n+STRICT CONSTRAINTS)"
            modified_prompt = re.sub(pattern, free_intent_section, base_prompt, flags=re.DOTALL)
        
        # Also update the distribution instruction for free plan
        # Replace the specific distribution line to only mention allowed intents
        distribution_pattern = r"- Specific distribution: Generate exactly.*?awareness queries, and.*?consideration queries\."
        free_distribution = """- Specific distribution: Generate exactly {distribution[informational]} informational queries and {distribution[awareness]} awareness queries.
- IMPORTANT: This means you MUST generate {k} queries total. Do NOT generate fewer than {k} queries.
- BREAKDOWN: Generate {distribution[informational]} queries with "intent": "informational" AND {distribution[awareness]} queries with "intent": "awareness"."""
        modified_prompt = re.sub(distribution_pattern, free_distribution, modified_prompt, flags=re.DOTALL)
        
        # Update the schema in OUTPUT FORMAT to only include allowed intents
        # Replace the specific intent list in the JSON schema
        old_schema = '"intent": "navigational|informational|commercial|transactional|awareness|consideration"'
        new_schema = '"intent": "informational|awareness"'
        modified_prompt = modified_prompt.replace(old_schema, new_schema)
        
        return modified_prompt
    else:
        # For paid plan, return original prompt as-is
        return base_prompt


async def generate_queries(
    product_category: str, 
    openai_api_key: str, 
    audience_description: Optional[str] = None, 
    locales: Optional[List[str]] = None, 
    brand_summary: Optional[str] = None,
    brand_products: Optional[str] = None,
    k: int = 30,
    custom_instructions: Optional[str] = None,
    plan: str = "free"
):
    # Calculate query distribution across intent categories based on plan
    distribution = get_plan_filtered_distribution(k, plan)
    distribution_summary = get_distribution_summary(distribution)
    
    logger.info(f"Query generation ({plan} plan): {distribution_summary}")
    
    # Use GPT-4 instead of GPT-4o-mini for better instruction following with complex distributions
    llm = ChatOpenAI(api_key=openai_api_key, model=ModelConfig.QUERY_GENERATION_MODEL, temperature=ModelConfig.DEFAULT_TEMPERATURE)

    parser = PydanticOutputParser(pydantic_object=Queries)

    # Apply plan filtering to the prompt
    filtered_prompt = get_plan_filtered_prompt(query_generation_system_prompt, plan)
    
    # Use template with custom instructions placeholder
    final_prompt = f"{filtered_prompt}\n\n{{format_instructions}}"

    prompt = ChatPromptTemplate.from_template(final_prompt).partial(
        format_instructions=parser.get_format_instructions()
    )

    query_generation_chain = prompt | llm.with_structured_output(Queries)
    queries = await query_generation_chain.ainvoke(
        {
            "product_category": product_category,
            "audience_description": audience_description,
            "locales": locales,
            "brand_summary": brand_summary,
            "brand_products": brand_products,
            "k": k,
            "distribution": distribution,  # Pass the full dictionary for template access
            "distribution[navigational]": distribution.get("navigational", 0),
            "distribution[informational]": distribution.get("informational", 0),
            "distribution[commercial]": distribution.get("commercial", 0),
            "distribution[transactional]": distribution.get("transactional", 0),
            "distribution[awareness]": distribution.get("awareness", 0),
            "distribution[consideration]": distribution.get("consideration", 0),
            "distribution_summary": distribution_summary,
            "custom_query_instructions": custom_instructions or ""
        }
    )
    return queries.model_dump()

async def generate_product_queries(
    product_name: str,
    product_description: str,
    product_type: str,
    openai_api_key: str = None,
    audience_description: Optional[str] = None,
    k: int = 30,
    custom_instructions: Optional[str] = None,
    plan: str = "free"
):
    """Generate queries specific to a single product"""
    from core.prompts.query_generation_product import product_query_generation_prompt
    
    # Calculate query distribution across intent categories based on plan
    distribution = get_plan_filtered_distribution(k, plan)
    distribution_summary = get_distribution_summary(distribution)
    
    logger.info(f"Product query generation ({plan} plan): {distribution_summary}")
    
    # Use GPT-4 instead of GPT-4o-mini for better instruction following with complex distributions
    llm = ChatOpenAI(api_key=openai_api_key, model=ModelConfig.QUERY_GENERATION_MODEL, temperature=ModelConfig.DEFAULT_TEMPERATURE)
    parser = PydanticOutputParser(pydantic_object=Queries)
    
    # Apply plan filtering to the prompt
    filtered_prompt = get_plan_filtered_prompt(product_query_generation_prompt, plan, is_product_prompt=True)
    
    # Use template with custom instructions placeholder
    final_prompt = f"{filtered_prompt}\n\n{{format_instructions}}"
    
    prompt = ChatPromptTemplate.from_template(final_prompt).partial(
        format_instructions=parser.get_format_instructions()
    )
    
    query_generation_chain = prompt | llm.with_structured_output(Queries)
    
    queries = await query_generation_chain.ainvoke({
        "product_name": product_name,
        "product_description": product_description,
        "product_type": product_type,
        "audience_description": audience_description or "General audience",
        "k": k,
        "distribution": distribution,  # Pass the full dictionary for template access
        "distribution[navigational]": distribution.get("navigational", 0),
        "distribution[informational]": distribution.get("informational", 0),
        "distribution[commercial]": distribution.get("commercial", 0),
        "distribution[transactional]": distribution.get("transactional", 0),
        "distribution[awareness]": distribution.get("awareness", 0),
        "distribution[consideration]": distribution.get("consideration", 0),
        "distribution_summary": distribution_summary,
        "custom_query_instructions": custom_instructions or ""
    })
    
    return queries.model_dump()