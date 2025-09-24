from typing import Any, List, Mapping, Optional
from pydantic import BaseModel, Field

class BrandProfile(BaseModel):
    
    icp: str = Field(..., description="Ideal Customer Profile")
    products: list[str] = Field(..., description="Range and types of products offered by the brand")
    summary: str = Field(..., description="Brief summary of the brand")
    locales: List[str] = Field(..., description="Locales of the brand")

class QueryItem(BaseModel):
    query: str = Field(..., description="The user search query")
    intent: str = Field(..., description="The main intent label")
    sub_intent: str = Field(None, description="Optional short tag (e.g., 'compare', 'sizing', 'care')")
    persona: str = Field(..., description="The user persona (e.g., novice, enthusiast, pro, budget_shopper, eco_conscious, gift_buyer)")
    category: str = Field(..., description="One of PRODUCT_CATEGORIES")
    expected_brand_relevance: str = Field(..., description="Expected brand relevance (high|medium|low)")
    locale: str = Field(..., description="IETF tag (e.g., en-US, fr-FR, ar-MA)")
    notes: str = Field(..., description="A short reason why this query exists in the real world")

class Queries(BaseModel):
    queries : list[QueryItem] = Field(..., description="A list of user search queries with their metadata")
    


class CitationsCount(BaseModel):
    count: int = Field(..., description="The number of times the brand name is mentioned")
    sentences: list[str] = Field(..., description="The sentences where the brand name is mentioned")

class LLMCitationResult(BaseModel):
    cited: bool = Field(..., description="Whether this LLM mentioned the brand (binary)")
    mention_count: int = Field(..., description="How many times the brand was mentioned")
    visibility_score: float = Field(..., description="1.0 if cited, 0.0 if not cited")
    response: str = Field(..., description="The full LLM response")
    sentences_with_brand: list[str] = Field(..., description="Sentences containing brand mentions")

class QueryVisibilityAnalysis(BaseModel):
    overall_citation_percentage: float = Field(..., description="Percentage of LLMs that mentioned the brand (0-100)")
    total_mentions: int = Field(..., description="Total number of brand mentions across all LLMs")
    llm_breakdown: dict[str, LLMCitationResult] = Field(..., description="Per-LLM citation analysis")
    explanation: str = Field(..., description="Human-readable explanation of the results")

class BrandVisibilityMetrics(BaseModel):
    average_citation_percentage: float = Field(..., description="Average visibility across all queries")
    total_queries_analyzed: int = Field(..., description="Number of queries processed")
    queries_with_citations: int = Field(..., description="Number of queries where at least one LLM mentioned the brand")
    llm_performance: dict[str, dict[str, float]] = Field(..., description="Per-LLM performance statistics")
    intent_visibility_breakdown: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Visibility breakdown by intent type")

class ProductInfo(BaseModel):
    product_description: str = Field(..., description="Brief description of what the product is and does")
    product_type: str = Field(..., description="Category or type of the product (e.g., 'sneakers', 'laptop', 'skincare cream')")
