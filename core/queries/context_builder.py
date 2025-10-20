"""
Context Builder Module

This module builds context for LLM answer generation by combining:
1. Brand profile information (ICP, summary, products)
2. Product category research via Tavily search
3. Optional product-specific information

This replaces the previous approach of crawling/indexing brand websites.
"""

import logging
from typing import Optional, Dict, Any
from langchain_tavily import TavilySearch
from datetime import datetime

logger = logging.getLogger(__name__)


async def build_context_from_brand_and_category(
    brand_name: str,
    brand_profile: Dict[str, Any],
    product_category: str,
    tavily_api_key: Optional[str] = None,
    product_info: Optional[Dict[str, str]] = None
) -> str:
    """
    Build context for LLM answer generation using brand profile and category research.

    Args:
        brand_name: Name of the brand
        brand_profile: Dictionary containing brand profile (icp, summary, products, locales)
        product_category: Product category for research
        tavily_api_key: Optional Tavily API key for enhanced search
        product_info: Optional dict with product_description and product_type

    Returns:
        Formatted context string combining brand and category information
    """
    logger.info(f"Building context for {brand_name} in {product_category} category")

    # Start with brand profile information
    context_parts = []

    # Add brand summary (neutralized)
    if brand_profile.get('summary'):
        # Remove brand name from summary if it appears at the start
        summary = brand_profile['summary']
        context_parts.append(f"## Brand Overview\n{summary}")

    # Add target audience (generic heading)
    if brand_profile.get('icp'):
        context_parts.append(f"## Target Market\n{brand_profile['icp']}")

    # Add products (less explicit brand mention)
    if brand_profile.get('products'):
        products = brand_profile['products']
        if isinstance(products, list):
            products_str = ", ".join(products)
        else:
            products_str = str(products)
        context_parts.append(f"## Product Offerings\nAvailable products include: {products_str}")

    # Add locales if available
    if brand_profile.get('locales'):
        locales = brand_profile['locales']
        if isinstance(locales, list) and locales:
            context_parts.append(f"## Geographic Markets\nAvailable in: {', '.join(locales)}")

    # Add product-specific information if provided
    if product_info:
        product_desc = product_info.get('product_description', '')
        product_type = product_info.get('product_type', '')

        if product_desc or product_type:
            product_section = f"## Product Details"
            if product_type:
                product_section += f"\nProduct Type: {product_type}"
            if product_desc:
                product_section += f"\nDescription: {product_desc}"
            context_parts.append(product_section)

    # Add category research via Tavily if available
    if tavily_api_key and tavily_api_key.strip():
        try:
            logger.info(f"Performing Tavily research for {product_category} category")

            # Initialize Tavily search
            search = TavilySearch(max_results=3, tavily_api_key=tavily_api_key)

            current_year = datetime.now().year

            # Research queries - focus on competitive landscape, not just the target brand
            search_queries = [
                f"best {product_category} {current_year}",
                f"{product_category} top brands and alternatives comparison",
                f"popular {product_category} options and features"
            ]

            category_research = []
            for query in search_queries:
                try:
                    logger.debug(f"Searching: {query}")
                    results = search.invoke(query)

                    # Tavily returns a list of search results
                    if results:
                        # Extract content from results
                        if isinstance(results, list):
                            for result in results[:2]:  # Take top 2 results per query
                                if isinstance(result, dict):
                                    content = result.get('content', '')
                                    if content:
                                        category_research.append(content[:500])  # Limit length
                                elif isinstance(result, str):
                                    category_research.append(result[:500])
                        elif isinstance(results, str):
                            category_research.append(results[:500])

                except Exception as e:
                    logger.warning(f"Search query '{query}' failed: {str(e)}")
                    continue

            # Add category research to context if we got results
            if category_research:
                research_text = "\n\n".join(category_research)
                context_parts.append(f"## {product_category} Market Information\n{research_text}")
                logger.info(f"✅ Added category research ({len(category_research)} sources)")
            else:
                logger.info("ℹ️ No category research results obtained")

        except Exception as e:
            logger.warning(f"⚠️ Tavily search initialization failed: {str(e)}. Proceeding without category research.")
    else:
        logger.info("ℹ️ No Tavily API key provided - skipping category research")

    # Combine all context parts
    full_context = "\n\n".join(context_parts)

    logger.info(f"✅ Context built: {len(full_context)} characters")
    logger.debug(f"Context preview: {full_context[:300]}...")

    return full_context


async def build_simple_brand_context(
    brand_name: str,
    brand_profile: Dict[str, Any]
) -> str:
    """
    Build minimal context from brand profile only (no external research).

    Args:
        brand_name: Name of the brand
        brand_profile: Dictionary containing brand profile

    Returns:
        Formatted context string with brand information
    """
    return await build_context_from_brand_and_category(
        brand_name=brand_name,
        brand_profile=brand_profile,
        product_category="",
        tavily_api_key=None,
        product_info=None
    )
