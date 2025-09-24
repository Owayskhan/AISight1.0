from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from dotenv import load_dotenv
load_dotenv(override=True)
from core.prompts.citations_count import citations_count_prompt
from core.models.main import CitationsCount, LLMCitationResult, QueryVisibilityAnalysis, BrandVisibilityMetrics
from typing import Dict, List

async def analyze_citations_count(llm, response, brand_name):
    citations_count_parser = PydanticOutputParser(pydantic_object=CitationsCount)

    citations_count_prompt_template = ChatPromptTemplate.from_template(
        citations_count_prompt).partial(
        brand_name=brand_name,
        format_instructions=citations_count_parser.get_format_instructions()
    )

    citations_count_chain = citations_count_prompt_template | llm.with_structured_output(CitationsCount)

    count = await citations_count_chain.ainvoke({
        "response": response
    })
    return count

async def analyze_query_visibility(llm_responses: Dict[str, any], brand_name: str, citation_llm, include_responses: bool = True) -> QueryVisibilityAnalysis:
    """
    Analyze visibility percentage for a single query across all LLMs
    
    Args:
        llm_responses: Dict with LLM names as keys and response objects as values
        brand_name: The brand name to search for
        citation_llm: LLM instance for citation analysis
    
    Returns:
        QueryVisibilityAnalysis with visibility percentage and breakdown
    """
    import asyncio
    
    llm_breakdown = {}
    total_mentions = 0
    cited_llms = 0
    
    # Create async tasks for all citation analyses
    citation_tasks = []
    llm_names = []
    
    for llm_name, response in llm_responses.items():
        task = analyze_citations_count(citation_llm, response.content, brand_name)
        citation_tasks.append(task)
        llm_names.append(llm_name)
    
    # Run all citation analyses concurrently
    citation_results = await asyncio.gather(*citation_tasks)
    
    # Process results
    for llm_name, citation_result, response in zip(llm_names, citation_results, llm_responses.values()):
        # Create binary citation result
        cited = citation_result.count > 0
        if cited:
            cited_llms += 1
            
        total_mentions += citation_result.count
        
        llm_breakdown[llm_name] = LLMCitationResult(
            cited=cited,
            mention_count=citation_result.count,
            visibility_score=1.0 if cited else 0.0,
            response=response.content if include_responses else "",
            sentences_with_brand=citation_result.sentences
        )
    
    # Calculate visibility percentage (0-100)
    total_llms = len(llm_responses)
    citation_percentage = (cited_llms / total_llms * 100) if total_llms > 0 else 0
    
    # Create human-readable explanation
    cited_llm_names = [name for name, result in llm_breakdown.items() if result.cited]
    not_cited_llm_names = [name for name, result in llm_breakdown.items() if not result.cited]
    
    if cited_llms == total_llms:
        explanation = f"Perfect visibility! All {total_llms} AI assistants mentioned {brand_name}."
    elif cited_llms == 0:
        explanation = f"No visibility. None of the {total_llms} AI assistants mentioned {brand_name}."
    else:
        explanation = f"{cited_llms} out of {total_llms} AI assistants mentioned {brand_name}. "
        explanation += f"✅ Cited by: {', '.join(cited_llm_names)}. "
        if not_cited_llm_names:
            explanation += f"❌ Not cited by: {', '.join(not_cited_llm_names)}."
    
    return QueryVisibilityAnalysis(
        overall_citation_percentage=round(citation_percentage, 1),
        total_mentions=total_mentions,
        llm_breakdown=llm_breakdown,
        explanation=explanation
    )

def calculate_brand_visibility_metrics(query_analyses: Dict[str, QueryVisibilityAnalysis], query_intents: Dict[str, str] = None) -> BrandVisibilityMetrics:
    """
    Calculate aggregated visibility metrics across all queries
    
    Args:
        query_analyses: Dict with query text as keys and QueryVisibilityAnalysis as values
        
    Returns:
        BrandVisibilityMetrics with overall performance statistics
    """
    if not query_analyses:
        return BrandVisibilityMetrics(
            average_citation_percentage=0.0,
            total_queries_analyzed=0,
            queries_with_citations=0,
            llm_performance={}
        )
    
    total_queries = len(query_analyses)
    total_percentage = sum(analysis.overall_citation_percentage for analysis in query_analyses.values())
    average_percentage = total_percentage / total_queries if total_queries > 0 else 0
    
    queries_with_citations = sum(1 for analysis in query_analyses.values() 
                                if analysis.overall_citation_percentage > 0)
    
    # Calculate per-LLM statistics
    llm_stats = {}
    llm_names = set()
    for analysis in query_analyses.values():
        llm_names.update(analysis.llm_breakdown.keys())
    
    for llm_name in llm_names:
        cited_count = sum(1 for analysis in query_analyses.values() 
                         if llm_name in analysis.llm_breakdown and analysis.llm_breakdown[llm_name].cited)
        total_mentions = sum(analysis.llm_breakdown[llm_name].mention_count 
                           for analysis in query_analyses.values()
                           if llm_name in analysis.llm_breakdown)
        
        citation_rate = (cited_count / total_queries * 100) if total_queries > 0 else 0
        
        llm_stats[llm_name] = {
            "citation_rate": round(citation_rate, 1),
            "total_mentions": total_mentions
        }
    
    # Calculate intent-based visibility breakdown
    intent_visibility_breakdown = {}
    if query_intents:
        # Initialize intent categories
        intent_categories = ["awareness", "informational", "consideration", "transactional"]
        for intent in intent_categories:
            intent_visibility_breakdown[intent] = {
                "total_queries": 0,
                "queries_with_citations": 0,
                "average_citation_percentage": 0.0,
                "citation_rate": 0.0
            }
        
        # Group queries by intent and calculate metrics
        for query_text, analysis in query_analyses.items():
            intent = query_intents.get(query_text, "").lower()
            # Handle both "information" and "informational" labels
            if intent == "information":
                intent = "informational"
            
            if intent in intent_visibility_breakdown:
                intent_visibility_breakdown[intent]["total_queries"] += 1
                if analysis.overall_citation_percentage > 0:
                    intent_visibility_breakdown[intent]["queries_with_citations"] += 1
                intent_visibility_breakdown[intent]["average_citation_percentage"] += analysis.overall_citation_percentage
        
        # Calculate averages and rates for each intent
        for intent, stats in intent_visibility_breakdown.items():
            if stats["total_queries"] > 0:
                stats["average_citation_percentage"] = round(
                    stats["average_citation_percentage"] / stats["total_queries"], 1
                )
                stats["citation_rate"] = round(
                    (stats["queries_with_citations"] / stats["total_queries"]) * 100, 1
                )
            else:
                stats["average_citation_percentage"] = 0.0
                stats["citation_rate"] = 0.0
    
    return BrandVisibilityMetrics(
        average_citation_percentage=round(average_percentage, 1),
        total_queries_analyzed=total_queries,
        queries_with_citations=queries_with_citations,
        llm_performance=llm_stats,
        intent_visibility_breakdown=intent_visibility_breakdown
    )