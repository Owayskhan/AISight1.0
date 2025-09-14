from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional
from core.models.main import Queries
from dotenv import load_dotenv
load_dotenv(override=True)
from core.prompts.query_generation import query_generation_system_prompt


async def generate_queries(
    product_category: str, 
    openai_api_key: str, 
    audience_description: Optional[str] = None, 
    locales: Optional[List[str]] = None, 
    brand_summary: Optional[str] = None,
    brand_products: Optional[str] = None,
    k: int = 5
):
    llm = ChatOpenAI(api_key=openai_api_key, model="gpt-4o-mini", temperature=0)

    parser = PydanticOutputParser(pydantic_object=Queries)

    prompt = ChatPromptTemplate.from_template(
        query_generation_system_prompt).partial(
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
            "k": k
        }
    )
    return queries.model_dump()

async def generate_product_queries(
    product_name: str,
    product_description: str,
    product_type: str,
    openai_api_key: str = None,
    audience_description: Optional[str] = None,
    k: int = 10
):
    """Generate queries specific to a single product"""
    from core.prompts.query_generation_product import product_query_generation_prompt
    
    llm = ChatOpenAI(api_key=openai_api_key, model="gpt-4o-mini", temperature=0)
    parser = PydanticOutputParser(pydantic_object=Queries)
    
    prompt = ChatPromptTemplate.from_template(
        product_query_generation_prompt
    ).partial(format_instructions=parser.get_format_instructions())
    
    query_generation_chain = prompt | llm.with_structured_output(Queries)
    
    queries = await query_generation_chain.ainvoke({
        "product_name": product_name,
        "product_description": product_description,
        "product_type": product_type,
        "audience_description": audience_description or "General audience",
        "k": k
    })
    
    return queries.model_dump()