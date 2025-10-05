from fastapi import FastAPI, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, List, Optional, Any
import sys
from pathlib import Path
import logging
import time
import traceback

# Add parent directory to path to import core modules
sys.path.append(str(Path(__file__).parent.parent))

from core.website_crawler.crawler import find_sitemap_url, find_sitemap_url_async, load_single_product_document
from core.indexer.indexer_optimized import  create_vector_store_optimized, get_smart_retriever
from core.brand_profiler.main import research_brand_info
from core.queries.generator import generate_queries, generate_product_queries
from core.queries.retriever import retrieve_queries_context_concurrent
from core.queries.answer_generator import run_query_answering_chain
from core.citation_counter.counter import analyze_query_visibility, calculate_brand_visibility_metrics
from core.models.main import Queries
from core.utils import get_progress_sender,  get_distribution_summary
from langchain_openai import ChatOpenAI

# Import error handling utilities
from core.utils.error_handling import (
    handle_api_error,
    APIException,
    ProcessingError
)
from core.utils.api_middleware import (
    ErrorHandlingMiddleware,
    RequestLoggingMiddleware
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Citation Count API", 
    version="1.0.0",
    description="API for analyzing brand visibility across AI assistants"
)

# Add error handling middleware
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)


class SocketIOBlockerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle Socket.IO polling requests and prevent log flooding
    """
    
    async def dispatch(self, request: Request, call_next):
        # Check if this is a Socket.IO polling request
        if "/ws/socket.io/" in str(request.url) or request.url.path.startswith("/socket.io/"):
            logger.info(f"Blocked Socket.IO request from {request.client.host}: {request.url}")
            return Response(
                content='{"error": "Socket.IO not supported. Please connect directly to Azure Web PubSub."}',
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        return await call_next(request)


# Add the middleware to block Socket.IO requests
app.add_middleware(SocketIOBlockerMiddleware)

class APIKeys(BaseModel):
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key (used for embeddings, query generation, citation analysis, and optionally brand profiling)")
    gemini_api_key: Optional[str] = Field(None, description="Google Gemini API key (preferred for brand profiling, also used for answer generation)")
    perplexity_api_key: Optional[str] = Field(None, description="Perplexity API key (used for answer generation and optionally brand profiling)")
    
    @model_validator(mode='after')
    def at_least_one_key_required(self):
        """Ensure at least one API key is provided"""
        if not any([self.openai_api_key, self.gemini_api_key, self.perplexity_api_key]):
            raise ValueError("At least one API key must be provided (openai_api_key, gemini_api_key, or perplexity_api_key)")
        
        return self

class CitationCountRequest(BaseModel):
    brand_name: str = Field(..., description="Name of the brand")
    brand_url: str = Field(..., description="Brand website URL or specific product URL")
    url_type: str = Field("website", description="Type of URL: 'website' or 'product'")
    sitemap_url: Optional[str] = Field(None, description="Sitemap URL (optional - will be auto-discovered if not provided)")
    product_category: str = Field(..., description="Product category for query generation")
    api_keys: APIKeys = Field(..., description="API keys for different services")
    k: int = Field(30, description="Number of queries to generate (minimum 6 - one per intent category)", ge=6, le=100)
    # Optional brand profile fields - if provided, skip brand profiling step
    audience_description: Optional[str] = Field(None, description="Target audience/ICP description (optional)")
    brand_summary: Optional[str] = Field(None, description="Brand summary (optional)")
    brand_products: Optional[str] = Field(None, description="Brand products description (optional)")
    # Product-specific fields (only for url_type='product')
    product_description: Optional[str] = Field(None, description="Product description (optional - will be extracted if not provided)")
    product_type: Optional[str] = Field(None, description="Product type/category (optional - will be extracted if not provided)")
    # Response control
    include_responses: bool = Field(False, description="Include LLM responses in the output (default: False to reduce response size)")
    # Real-time updates
    group_name: Optional[str] = Field(None, description="Azure Web PubSub group name for real-time progress updates")
    # Indexing optimization
    indexing_batch_size: int = Field(500, description="Batch size for embedding operations (10-1000)", ge=10, le=1000)
    use_concurrent_indexing: bool = Field(True, description="Use concurrent indexing for faster performance (default: True)")
    # Pinecone settings
    use_pinecone: bool = Field(True, description="Use Pinecone for persistent vector storage (default: True)")
    force_reindex: bool = Field(False, description="Force re-indexing even if brand namespace exists in Pinecone")
    # Custom prompt instructions
    custom_query_generation_instructions: Optional[str] = Field(
        None, 
        description="Custom instructions to append to the query generation prompt. Use this to add specific requirements, constraints, or guidelines for query generation."
    )
    # Intent control
    user_intent: Optional[List[str]] = Field(
        None, 
        description="Specific intent types to generate queries for. Valid values: 'navigational', 'informational', 'commercial', 'transactional', 'awareness', 'consideration'. If not provided, uses all intent types."
    )
    # Pre-defined queries
    queries: Optional[List[Dict[str, str]]] = Field(
        None, 
        description="Pre-defined queries to use instead of generation. If provided, skips query generation entirely and uses these queries. Each query should have: query, intent, sub_intent, persona, category, expected_brand_relevance, locale, notes."
    )
    
    @field_validator('url_type')
    @classmethod
    def validate_url_type(cls, v):
        if v not in ['website', 'product']:
            raise ValueError("url_type must be either 'website' or 'product'")
        return v
    
    @field_validator('user_intent')
    @classmethod
    def validate_user_intent(cls, v):
        if v is not None:
            valid_intents = ['navigational', 'informational', 'commercial', 'transactional', 'awareness', 'consideration']
            invalid_intents = [intent for intent in v if intent not in valid_intents]
            if invalid_intents:
                raise ValueError(f"Invalid intent types: {invalid_intents}. Valid values: {valid_intents}")
            if len(set(v)) != len(v):
                raise ValueError("Duplicate intent types are not allowed")
        return v
    
    @field_validator('queries')
    @classmethod
    def validate_queries(cls, v):
        if v is not None:
            if not v:  # Empty list
                raise ValueError("queries field cannot be empty if provided")
            if len(v) > 100:
                raise ValueError("Maximum 100 pre-defined queries allowed")
            
            # Validate required fields for each query
            required_fields = ['query', 'intent', 'sub_intent', 'persona', 'category', 'expected_brand_relevance', 'locale', 'notes']
            for i, query_item in enumerate(v):
                missing_fields = [field for field in required_fields if field not in query_item]
                if missing_fields:
                    raise ValueError(f"Query {i+1} missing required fields: {missing_fields}")
        return v
    
    @field_validator('sitemap_url')
    @classmethod
    def validate_sitemap_url(cls, v, info):
        url_type = info.data.get('url_type', 'website')
        if url_type == 'product' and v is not None:
            raise ValueError("sitemap_url should not be provided when url_type is 'product'")
        return v
    
    @field_validator('api_keys')
    @classmethod
    def validate_required_api_keys(cls, v, info):
        """Validate that required API keys are provided based on request parameters"""
        # At least one API key is required (already validated by APIKeys model)
        # No specific key is mandatory - the system will use whichever keys are available
        
        # If brand profile info is not provided, we need at least one key that can do brand profiling
        audience_desc = info.data.get('audience_description')
        brand_summary = info.data.get('brand_summary')
        if not (audience_desc and brand_summary):
            # Ensure we have at least one key that can perform brand profiling
            if not any([v.openai_api_key, v.gemini_api_key, v.perplexity_api_key]):
                raise ValueError("At least one API key is required for brand profiling when audience_description and brand_summary are not provided")
        
        return v
    class Config:
        json_schema_extra = {
            "example": {
                "brand_name": "Example Brand",
                "brand_url": "https://example.com",
                "url_type": "website",
                "product_category": "Electronics",
                "k": 30,
                "api_keys": {
                    "openai_api_key": "sk-...",
                    "gemini_api_key": "AIza...",
                    "perplexity_api_key": "pplx-..."
                },
                "include_responses": False,
                "group_name": "analysis-session-123",
                "indexing_batch_size": 500,
                "use_concurrent_indexing": True,
                "use_pinecone": True,
                "force_reindex": False,
                "custom_query_generation_instructions": "Focus on eco-friendly and sustainable product options. Include queries about environmental impact and certifications."
            }
        }

class CitationCountResponse(BaseModel):
    brand_profile: Dict[str, Any]
    queries: List[Dict[str, Any]]
    intent_distribution: Dict[str, int] = Field(..., description="Distribution of queries by intent type")
    citation_analysis: Dict[str, Dict[str, Any]]
    overall_brand_visibility: Dict[str, Any]
    timing_breakdown: Dict[str, Any] = Field(..., description="Detailed breakdown of processing time by step")
    
@app.get("/")
async def root():
    return {"message": "Citation Count API", "endpoints": ["/analyze"]}


@app.get("/ws/socket.io/")
async def socket_io_redirect():
    """Handle Socket.IO polling requests with proper error message"""
    return {
        "error": "Socket.IO not supported by this API",
        "message": "This API uses Azure Web PubSub for real-time updates, not Socket.IO",
        "instructions": {
            "for_real_time_updates": "Connect directly to Azure Web PubSub using the connection string",
            "api_usage": "Use POST /analyze endpoint for citation analysis",
            "documentation": "See API documentation for proper usage"
        }
    }


@app.api_route("/socket.io/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def socket_io_fallback(path: str):
    """Catch-all for any Socket.IO requests"""
    return {
        "error": "Socket.IO not supported by this API",
        "message": "This API uses Azure Web PubSub for real-time updates, not Socket.IO",
        "requested_path": f"/socket.io/{path}",
        "instructions": {
            "for_real_time_updates": "Connect directly to Azure Web PubSub using the connection string",
            "api_usage": "Use POST /analyze endpoint for citation analysis"
        }
    }

@app.post("/analyze", response_model=CitationCountResponse)
async def analyze_citation_count(request: CitationCountRequest):
    start_time = time.time()
    step_timings = {}  # Track timing for each step
    logger.info(f"🚀 Starting citation analysis for brand: {request.brand_name}")
    logger.info(f"📊 URL type: {request.url_type}, Category: {request.product_category}, Queries to generate: {request.k}")
    
    # Initialize progress sender if group_name is provided
    progress_sender = get_progress_sender(request.group_name) if request.group_name else None
    
    try:
        # API keys are already validated by Pydantic model
        logger.info("✅ API keys validated successfully")
        
        # Send initial status
        if progress_sender:
            progress_sender.send_status("starting", f"Starting citation analysis for {request.brand_name}")
        
        # Branch logic based on URL type
        if request.url_type == "product":
            logger.info("🛍️ Processing single product URL...")
            step_start = time.time()
            try:
                product_docs = await load_single_product_document(
                    product_url=request.brand_url,
                    openai_api_key=request.api_keys.openai_api_key,
                    product_description=request.product_description,
                    product_type=request.product_type
                )
                if not product_docs:
                    logger.error("❌ Failed to load product page")
                    raise HTTPException(status_code=400, detail="Could not load product page")
                
                logger.info(f"✅ Product page loaded and chunked into {len(product_docs)} documents")
                
                # Get extracted product info from the first document
                if product_docs:
                    extracted_info = product_docs[0].metadata
                    product_desc = extracted_info.get("product_description", "N/A")
                    product_type = extracted_info.get("product_type", "N/A")
                    
                    if request.product_description and request.product_type:
                        logger.info("📝 Using provided product information:")
                    else:
                        logger.info("🧠 Extracted product information using LLM:")
                    
                    logger.info(f"   📋 Product Type: {product_type}")
                    logger.info(f"   📄 Description: {product_desc[:100]}...")
                

                # Create vector store with the single product document
                logger.info("🔍 Creating vector store for product...")
                
                # Send progress update for indexing
                if progress_sender:
                    progress_sender.send_status("indexing_brand_data", "Indexing brand data")
                
                # Create progress callback for indexing
                def indexing_progress_callback(current, total, message):
                    if progress_sender:
                        progress_sender.send_progress(current, total, message)
                
                vector_store = await create_vector_store_optimized(
                    product_docs, 
                    request.api_keys.openai_api_key,
                    batch_size=request.indexing_batch_size,
                    progress_callback=indexing_progress_callback
                )
                retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
                content_preloaded = True
                logger.info("✅ Vector store created for product")
                step_timings["product_processing"] = time.time() - step_start
                
            except Exception as e:
                error = handle_api_error(e, service="product_processing")
                logger.error(f"❌ Product processing failed: {error.message}")
                if progress_sender:
                    progress_sender.send_error(error.message, "product_processing", status_code=error.status_code)
                raise error
            
        else:
            logger.info("🌐 Processing website URL...")
            step_start = time.time()
            # Website flow with optimization: Check namespace first before sitemap fetching
            
            # Step 1: Check if brand already has indexed data (optimization)
            logger.info("🔍 Checking if brand data is already indexed...")
            sitemap_url = None
            
            if request.use_pinecone and not request.force_reindex:
                try:
                    # Send progress update for checking existing index
                    if progress_sender:
                        progress_sender.send_status("checking_existing_index", "Checking existing brand index")
                    
                    from core.indexer.pinecone_indexer import get_brand_namespace_stats
                    namespace_stats = await get_brand_namespace_stats(request.brand_name)
                    logger.info(f"Namespace stats for '{request.brand_name}': {namespace_stats}")
                    
                    if namespace_stats['exists'] and namespace_stats['vector_count'] > 0:
                        # Brand already indexed - skip sitemap fetching entirely!
                        logger.info(f"✅ Found existing index for '{request.brand_name}' with {namespace_stats['vector_count']} vectors")
                        logger.info("🚀 Skipping sitemap discovery - using cached vectors (major time savings!)")
                        sitemap_url = "existing_namespace"  # Placeholder to indicate we're using existing data
                    else:
                        logger.info(f"📥 No existing index found for '{request.brand_name}' - will need sitemap")
                        sitemap_url = None
                        
                except Exception as e:
                    logger.warning(f"⚠️ Could not check existing namespace: {str(e)}")
                    logger.info("📝 Proceeding with sitemap discovery as fallback")
                    sitemap_url = None
            
            # Step 2: Find sitemap URL only if we don't have existing data
            if sitemap_url != "existing_namespace":
                if request.sitemap_url:
                    sitemap_url = request.sitemap_url
                    logger.info(f"📋 Using provided sitemap URL: {sitemap_url}")
                else:
                    logger.info("🔍 Auto-discovering sitemap URL...")
                    try:
                        sitemap_url = await find_sitemap_url_async(request.brand_url)
                        logger.info(f"✅ Sitemap discovered: {sitemap_url}")
                    except Exception as e:
                        error = handle_api_error(e, service="web_scraping")
                        logger.error(f"❌ Sitemap discovery failed: {error.message}")
                        if progress_sender:
                            progress_sender.send_error(error.message, "sitemap_discovery", status_code=error.status_code)
                        raise error
            
            # Step 3: Smart indexing with Pinecone or FAISS fallback
            logger.info("🔍 Setting up smart retriever...")
            try:
                # Send progress update for indexing
                if progress_sender:
                    progress_sender.send_status("indexing_brand_data", "Indexing brand data")
                
                # Create progress callback for indexing
                def indexing_progress_callback(current, total, message):
                    if progress_sender:
                        progress_sender.send_progress(current, total, message)
                
                # Use smart retriever that handles Pinecone vs FAISS automatically
                # Note: sitemap_url will be "existing_namespace" if we're using cached data
                retriever = await get_smart_retriever(
                    brand_name=request.brand_name,
                    sitemap_url=sitemap_url if sitemap_url != "existing_namespace" else None, 
                    api_key=request.api_keys.openai_api_key,
                    k=4,
                    batch_size=request.indexing_batch_size,
                    use_pinecone=request.use_pinecone,
                    force_reindex=request.force_reindex,
                    use_parallel_sitemap=True,  # Always use parallel sitemap loading
                    progress_callback=indexing_progress_callback,
                    skip_namespace_check=(sitemap_url == "existing_namespace")  # New parameter to avoid double-checking
                )
                content_preloaded = False  # URLs indexed, content loaded during retrieval
                logger.info("✅ Smart retriever created successfully")
                step_timings["website_indexing"] = time.time() - step_start
                
            except Exception as e:
                error = handle_api_error(e, service="indexing")
                logger.error(f"❌ Sitemap processing failed: {error.message}")
                if progress_sender:
                    progress_sender.send_error(error.message, "sitemap_processing", status_code=error.status_code)
                raise error
        
        # Step 2: Handle brand profile - either use provided info or generate it
        logger.info("👥 Processing brand profile...")
        step_start = time.time()
        
        # Send progress update for collecting brand data
        if progress_sender:
            progress_sender.send_status("collecting_brand_data", "Collecting brand data")
        
        if request.audience_description and request.brand_summary:
            logger.info("📝 Using provided brand profile information")
            audience_description = request.audience_description
            brand_summary = request.brand_summary
            locales = None  # User can provide this if needed
            brand_profile = None  # We'll create a mock profile for the response
        else:
            logger.info("🧠 Generating brand profile using AI...")
            try:
                import os
                from dotenv import load_dotenv
                load_dotenv(override=True)

                brand_profile = await research_brand_info(
                    brand_name=request.brand_name,
                    brand_url=request.brand_url,
                    api_keys={
                        'openai_api_key': request.api_keys.openai_api_key,
                        'gemini_api_key': request.api_keys.gemini_api_key,
                        'perplexity_api_key': request.api_keys.perplexity_api_key
                    },
                    tavily_api_key=os.getenv("TAVILY_API_KEY", "")
                )
                audience_description = brand_profile.icp
                brand_summary = brand_profile.summary
                locales = brand_profile.locales
                logger.info("✅ Brand profile generated successfully")
                logger.info(f"🎯 Target audience: {audience_description[:100]}...")
                
            except Exception as e:
                error = handle_api_error(e, service="brand_profiling")
                logger.error(f"❌ Brand profile generation failed: {error.message}")
                if progress_sender:
                    progress_sender.send_error(error.message, "brand_profiling", status_code=error.status_code)
                raise error
        
        step_timings["brand_profiling"] = time.time() - step_start
        
        # Step 3: Generate queries based on URL type
        logger.info(f"❓ Generating {request.k} queries...")
        step_start = time.time()
        
        # Log if custom instructions are provided
        if request.custom_query_generation_instructions:
            logger.info(f"📝 Using custom query generation instructions: {request.custom_query_generation_instructions[:100]}...")
        
        # Show query distribution
        from core.utils.query_distribution import get_query_distribution, get_user_intent_distribution
        if request.user_intent:
            distribution = get_user_intent_distribution(request.k, request.user_intent)
        else:
            distribution = get_query_distribution(request.k)
        distribution_summary = get_distribution_summary(distribution)
        logger.info(f"📊 Query Distribution: {distribution_summary}")
        
        # Send progress update for generating queries
        if progress_sender:
            progress_sender.send_status("generating_queries", "Generating queries")
        
        try:
            # Use smart query distribution to handle all edge cases
            from core.utils.query_distribution import get_smart_query_distribution
            from core.queries.generator import generate_missing_intent_queries
            
            # Analyze what queries we need to generate
            smart_distribution = get_smart_query_distribution(
                total_queries=request.k,
                user_intent=request.user_intent,
                provided_queries=request.queries
            )
            
            logger.info(f"🤖 Smart query mode: {smart_distribution['mode']}")
            
            # Handle different modes
            if smart_distribution['mode'] == 'provided_only':
                # Use pre-defined queries as-is
                logger.info(f"📋 Using {smart_distribution['provided_queries']} pre-defined queries only")
                
                # Convert dict queries to QueryItem format
                from core.models.main import QueryItem
                query_items = []
                for query_dict in request.queries:
                    query_item = QueryItem(**query_dict)
                    query_items.append(query_item)
                
                queries = {"queries": [query.model_dump() for query in query_items]}
                
                # Show coverage analysis if available
                if 'coverage_analysis' in smart_distribution:
                    coverage = smart_distribution['coverage_analysis']
                    logger.info(f"📊 Intent coverage: {coverage['coverage_percentage']}% ({len(coverage['covered_intents'])}/{len(coverage['requested_intents'])} intents)")
                
            elif smart_distribution['mode'] == 'hybrid':
                # Hybrid mode: Use provided queries + generate missing intents
                coverage = smart_distribution['coverage_analysis']
                logger.info(f"🔗 Hybrid mode: {smart_distribution['provided_queries']} provided + {smart_distribution['needs_generation']} generated")
                logger.info(f"📊 Provided queries cover {coverage['coverage_percentage']}% of requested intents")
                logger.info(f"🔧 Missing intents to generate: {smart_distribution['missing_intents']}")
                
                # Start with provided queries
                from core.models.main import QueryItem
                provided_query_items = []
                for query_dict in request.queries:
                    query_item = QueryItem(**query_dict)
                    provided_query_items.append(query_item)
                
                # Generate queries for missing intents
                if smart_distribution['needs_generation'] > 0:
                    # Determine generation parameters based on URL type
                    if request.url_type == "product":
                        if product_docs:
                            extracted_info = product_docs[0].metadata
                            product_desc = extracted_info.get("product_description", "Product description")
                            product_type = extracted_info.get("product_type", "product")
                        else:
                            product_desc = "Product description"
                            product_type = "product"
                        
                        logger.info("🛍️ Generating missing queries using product-specific generation")
                        additional_queries = await generate_missing_intent_queries(
                            missing_intents=smart_distribution['missing_intents'],
                            generation_distribution=smart_distribution['generation_distribution'],
                            product_name=request.brand_name,
                            product_description=product_desc,
                            product_type=product_type,
                            openai_api_key=request.api_keys.openai_api_key,
                            audience_description=audience_description,
                            custom_instructions=request.custom_query_generation_instructions,
                            is_product=True
                        )
                    else:
                        logger.info("🌐 Generating missing queries using category-based generation")
                        additional_queries = await generate_missing_intent_queries(
                            missing_intents=smart_distribution['missing_intents'],
                            generation_distribution=smart_distribution['generation_distribution'],
                            product_category=request.product_category,
                            openai_api_key=request.api_keys.openai_api_key,
                            audience_description=audience_description,
                            locales=locales,
                            brand_summary=brand_summary,
                            brand_products=request.brand_products,
                            custom_instructions=request.custom_query_generation_instructions,
                            is_product=False
                        )
                    
                    # Combine provided and generated queries
                    all_query_dicts = [query.model_dump() for query in provided_query_items] + additional_queries['queries']
                    queries = {"queries": all_query_dicts}
                    
                    logger.info(f"✅ Hybrid generation complete: {len(provided_query_items)} provided + {len(additional_queries['queries'])} generated = {len(queries['queries'])} total")
                else:
                    # No additional generation needed
                    queries = {"queries": [query.model_dump() for query in provided_query_items]}
                    logger.info(f"✅ All requested intents covered by provided queries")
            
            elif smart_distribution['mode'] in ['provided_plus_all', 'user_intent_only', 'all_intents']:
                # Standard generation modes (existing behavior with enhancements)
                if smart_distribution['mode'] == 'provided_plus_all':
                    logger.info(f"📋➕ Using {smart_distribution['provided_queries']} provided queries + {smart_distribution['needs_generation']} additional generation")
                elif smart_distribution['mode'] == 'user_intent_only':
                    logger.info(f"🎯 Generating {smart_distribution['needs_generation']} queries for user-specified intents: {request.user_intent}")
                else:
                    logger.info(f"📋 Generating {smart_distribution['needs_generation']} queries using all intent types")
                
                # Generate queries based on URL type and user intent
                if request.url_type == "product":
                    logger.info("🛍️ Using product-specific query generation")
                    
                    # Get product info from the loaded documents
                    if product_docs:
                        extracted_info = product_docs[0].metadata
                        product_desc = extracted_info.get("product_description", "Product description")
                        product_type = extracted_info.get("product_type", "product")
                    else:
                        product_desc = "Product description"
                        product_type = "product"
                    
                    generated_queries = await generate_product_queries(
                        product_name=request.brand_name,
                        product_description=product_desc,
                        product_type=product_type,
                        openai_api_key=request.api_keys.openai_api_key,
                        audience_description=audience_description,
                        k=smart_distribution['needs_generation'],
                        custom_instructions=request.custom_query_generation_instructions,
                        user_intent=request.user_intent
                    )
                else:
                    logger.info("🌐 Using category-based query generation")
                    generated_queries = await generate_queries(
                        product_category=request.product_category,
                        openai_api_key=request.api_keys.openai_api_key,
                        audience_description=audience_description,
                        locales=locales,
                        brand_summary=brand_summary,
                        brand_products=request.brand_products,
                        k=smart_distribution['needs_generation'],
                        custom_instructions=request.custom_query_generation_instructions,
                        user_intent=request.user_intent
                    )
                
                # Combine with provided queries if applicable
                if smart_distribution['mode'] == 'provided_plus_all' and request.queries:
                    from core.models.main import QueryItem
                    provided_query_items = []
                    for query_dict in request.queries:
                        query_item = QueryItem(**query_dict)
                        provided_query_items.append(query_item)
                    
                    all_query_dicts = [query.model_dump() for query in provided_query_items] + generated_queries['queries']
                    queries = {"queries": all_query_dicts}
                    logger.info(f"✅ Combined generation: {len(provided_query_items)} provided + {len(generated_queries['queries'])} generated = {len(queries['queries'])} total")
                else:
                    queries = generated_queries
            
            queries_obj = Queries(**queries)
            
            # Only show query details if they were generated (not pre-defined)
            if request.queries is None:
                logger.info(f"✅ Generated {len(queries_obj.queries)} queries successfully")
                for i, query in enumerate(queries_obj.queries[:3], 1):  # Show first 3 queries
                    logger.info(f"   {i}. {query.query} ({query.intent})")
                if len(queries_obj.queries) > 3:
                    logger.info(f"   ... and {len(queries_obj.queries) - 3} more queries")
                
            step_timings["query_generation"] = time.time() - step_start
                
        except Exception as e:
            logger.error(f"❌ Query generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Query generation error: {str(e)}")
        
        # Step 4: Retrieve context for queries
        logger.info("🔍 Retrieving context for queries...")
        step_start = time.time()
        try:
            # Use concurrent context retrieval for better performance
            from core.config import BatchConfig
            
            # Adaptive concurrency: use more connections for more queries/URLs
            base_concurrent = BatchConfig.MAX_CONCURRENT_CONTEXT_DOWNLOADS
            # Scale concurrency based on number of queries (4 URLs per query average)
            estimated_urls = len(queries_obj.queries) * 4
            # Use full concurrency for large workloads, scale down for smaller ones
            max_concurrent_downloads = min(base_concurrent, max(20, estimated_urls // 2))
            
            logger.info(f"🚀 Using up to {max_concurrent_downloads} concurrent connections for context retrieval (estimated ~{estimated_urls} URLs)")
            retrieved_queries = await retrieve_queries_context_concurrent(
                queries_obj, 
                retriever, 
                content_preloaded=content_preloaded,
                max_concurrent=max_concurrent_downloads
            )
            logger.info(f"✅ Retrieved context for {len(retrieved_queries)} queries")
            
            # Diagnostic: Check context quality
            empty_contexts = 0
            for item in retrieved_queries:
                context = item.get("context", "")
                # Handle case where context might be a list or other type
                if isinstance(context, list):
                    context_str = " ".join(str(c) for c in context) if context else ""
                elif isinstance(context, str):
                    context_str = context
                else:
                    context_str = str(context) if context else ""
                
                if not context_str.strip():
                    empty_contexts += 1
            
            if empty_contexts > 0:
                logger.warning(f"⚠️  {empty_contexts}/{len(retrieved_queries)} queries have empty context - this will impact citation analysis quality")
                logger.info("🔍 Possible causes: website blocking, failed indexing, or content extraction issues")
            else:
                logger.info(f"✅ All {len(retrieved_queries)} queries have valid context")
            
            context_duration = time.time() - step_start
            step_timings["context_retrieval"] = context_duration
            logger.info(f"⚡ Context retrieval optimization: {context_duration:.2f}s total (target <20s for major improvement)")
            
        except Exception as e:
            logger.error(f"❌ Context retrieval failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Context retrieval error: {str(e)}")
        
        # Step 5: Generate answers and analyze visibility
        logger.info("🤖 Starting LLM answer generation and citation analysis...")
        step_start = time.time()
        import asyncio
        
        # Initialize LLM for citation analysis (using OpenAI for consistency)
        citation_llm = ChatOpenAI(api_key=request.api_keys.openai_api_key, model="gpt-4o-mini", temperature=0)
        logger.info("✅ Citation analysis LLM initialized")
        
        total_queries = len(retrieved_queries)
        logger.info(f"🚀 Processing {total_queries} queries with concurrent optimization...")
        
        # Process queries with true concurrent processing and intelligent rate limiting
        citation_results = {}
        
        # Get list of active APIs for progress reporting and set concurrency limits
        from core.config import BatchConfig
        
        active_apis = []
        api_concurrency_limits = {}
        if request.api_keys.openai_api_key:
            active_apis.append("OpenAI")
            api_concurrency_limits["openai"] = BatchConfig.MAX_CONCURRENT_OPENAI_REQUESTS
        if request.api_keys.gemini_api_key:
            active_apis.append("Gemini")
            api_concurrency_limits["gemini"] = BatchConfig.MAX_CONCURRENT_GEMINI_REQUESTS
        if request.api_keys.perplexity_api_key:
            active_apis.append("Perplexity")
            api_concurrency_limits["perplexity"] = BatchConfig.MAX_CONCURRENT_PERPLEXITY_REQUESTS
            
        logger.info(f"🚀 Processing {total_queries} queries with true concurrency across {', '.join(active_apis)}")
        logger.info(f"📊 Concurrency limits: {api_concurrency_limits}")
        
        # Import rate limiter - ensure it's configured
        from core.utils.rate_limiter import wait_for_rate_limit
        
        # Create semaphores for per-API concurrency control
        api_semaphores = {}
        for api_name, limit in api_concurrency_limits.items():
            api_semaphores[api_name] = asyncio.Semaphore(limit)
        
        # Enhanced process_single_query with rate limiting and concurrency control
        async def process_single_query_with_rate_limiting(idx, item):
            query = item["query"]
            context = item["context"]
            
            logger.info(f"🔄 Processing query {idx}/{total_queries}: '{query.query[:60]}...'")
            
            try:
                async def call_llms_with_rate_limiting():
                    # Acquire semaphores for all APIs we'll use before making any calls
                    acquired_semaphores = []
                    try:
                        # Acquire semaphores based on which API keys are available
                        if request.api_keys.openai_api_key and "openai" in api_semaphores:
                            await api_semaphores["openai"].acquire()
                            acquired_semaphores.append(("openai", api_semaphores["openai"]))
                            
                        if request.api_keys.gemini_api_key and "gemini" in api_semaphores:
                            await api_semaphores["gemini"].acquire()
                            acquired_semaphores.append(("gemini", api_semaphores["gemini"]))
                            
                        if request.api_keys.perplexity_api_key and "perplexity" in api_semaphores:
                            await api_semaphores["perplexity"].acquire()
                            acquired_semaphores.append(("perplexity", api_semaphores["perplexity"]))
                        
                        # Now make the LLM calls (already concurrent within this function)
                        num_llms = len(acquired_semaphores)
                        logger.info(f"   🤖 Generating answers from {num_llms} LLMs with rate limiting...")
                        
                        # Wait for rate limits for each API we'll use
                        rate_limit_waits = []
                        for api_name, _ in acquired_semaphores:
                            wait_task = wait_for_rate_limit(api_name, tokens=1)
                            rate_limit_waits.append(wait_task)
                        
                        # Wait for all rate limits concurrently
                        if rate_limit_waits:
                            await asyncio.gather(*rate_limit_waits)
                        
                        # Debug: Check context quality - handle list or string context
                        if isinstance(context, list):
                            context_str = " ".join(str(c) for c in context) if context else ""
                        elif isinstance(context, str):
                            context_str = context
                        else:
                            context_str = str(context) if context else ""
                        
                        context_preview = context_str[:200] if context_str else "No context"
                        logger.info(f"   📄 Context preview: {context_preview}...")
                        brand_in_context = request.brand_name.lower() in context_str.lower() if context_str else False
                        logger.info(f"   🔍 Brand '{request.brand_name}' in context: {brand_in_context}")
                        
                        # Make the actual LLM calls
                        llm_responses = await run_query_answering_chain(
                            query=query.query,
                            context=context_str,
                            brand_name=request.brand_name,
                            api_keys={
                                "OPENAI_API_KEY": request.api_keys.openai_api_key,
                                "GOOGLE_API_KEY": request.api_keys.gemini_api_key,
                                "PERPLEXITY_API_KEY": request.api_keys.perplexity_api_key
                            }
                        )
                        logger.info(f"   ✅ Got responses from {len(llm_responses)} LLMs")
                        
                        # Debug: Check if responses mention the brand
                        for llm_name, response in llm_responses.items():
                            response_content = response.content if hasattr(response, 'content') else str(response)
                            brand_in_response = request.brand_name.lower() in response_content.lower()
                            response_preview = response_content[:100] if response_content else "No response"
                            logger.info(f"   🤖 {llm_name} mentions '{request.brand_name}': {brand_in_response} | Preview: {response_preview}...")
                        return llm_responses
                        
                    finally:
                        # Release all acquired semaphores
                        for api_name, semaphore in acquired_semaphores:
                            semaphore.release()
                
                llm_responses = await call_llms_with_rate_limiting()
                
                # Analyze visibility for this query across all LLMs (already concurrent within this function)
                logger.info(f"   📊 Analyzing brand visibility...")
                
                # Rate limit the citation analysis (uses OpenAI)
                await wait_for_rate_limit("openai", tokens=1)
                visibility_analysis = await analyze_query_visibility(
                    llm_responses=llm_responses,
                    brand_name=request.brand_name,
                    citation_llm=citation_llm,
                    include_responses=request.include_responses
                )
                
                citation_percentage = visibility_analysis.overall_citation_percentage
                logger.info(f"   ✅ Visibility: {citation_percentage}% ({visibility_analysis.explanation})")
                
                return query.query, visibility_analysis.model_dump()
                
            except Exception as e:
                logger.error(f"   ❌ Failed processing query {idx}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Query processing error for query {idx}: {str(e)}")
        
        # Process all queries concurrently with progress tracking
        logger.info("🚀 Starting concurrent processing of all queries...")
        
        # Send initial progress update
        if progress_sender:
            progress_sender.send_progress(
                current=0,
                total=len(retrieved_queries),
                step=f"Running queries over {', '.join(active_apis)}"
            )
        
        # Track progress in real-time
        completed_queries = 0
        progress_lock = asyncio.Lock()
        
        async def process_with_progress(idx, item):
            nonlocal completed_queries
            
            try:
                result = await process_single_query_with_rate_limiting(idx, item)
                
                # Update progress atomically
                async with progress_lock:
                    completed_queries += 1
                    if progress_sender:
                        progress_sender.send_progress(
                            current=completed_queries,
                            total=len(retrieved_queries),
                            step=f"Running queries over {', '.join(active_apis)}"
                        )
                
                return result
            except Exception:
                # Still update progress on error
                async with progress_lock:
                    completed_queries += 1
                    if progress_sender:
                        progress_sender.send_progress(
                            current=completed_queries,
                            total=len(retrieved_queries),
                            step=f"Running queries over {', '.join(active_apis)} (error in query {idx})"
                        )
                raise
        
        # Create all tasks and run them concurrently
        tasks = [process_with_progress(i + 1, item) for i, item in enumerate(retrieved_queries)]
        
        # Process all queries concurrently - this is the key optimization!
        logger.info(f"⚡ Processing all {len(tasks)} queries concurrently...")
        concurrent_start_time = time.time()
        concurrent_results = await asyncio.gather(*tasks, return_exceptions=True)
        concurrent_duration = time.time() - concurrent_start_time
        
        # Process results and handle any exceptions
        for result in concurrent_results:
            if isinstance(result, Exception):
                logger.error(f"Query processing failed: {str(result)}")
                # Continue processing other queries, don't fail the entire batch
            else:
                query_text, analysis = result
                citation_results[query_text] = analysis
        
        logger.info(f"🎉 Completed concurrent processing of {len(citation_results)} queries successfully!")
        if len(citation_results) > 0:
            logger.info(f"⚡ Concurrent processing performance: {concurrent_duration:.2f}s total ({concurrent_duration/len(citation_results):.2f}s per query average)")
        else:
            logger.warning(f"⚠️  No queries completed successfully in {concurrent_duration:.2f}s")
        
        # Calculate estimated old vs new performance
        if len(citation_results) > 0:
            estimated_old_time = len(citation_results) * 3.0  # Rough estimate: 3 seconds per query in old batched approach
            performance_improvement = ((estimated_old_time - concurrent_duration) / estimated_old_time) * 100
            logger.info(f"📈 Performance improvement: ~{performance_improvement:.0f}% faster than sequential batch processing")
        else:
            logger.warning("⚠️  Cannot calculate performance improvement - no queries completed")
        
        step_timings["llm_analysis"] = time.time() - step_start
        
        # Calculate overall brand visibility metrics
        logger.info("📈 Calculating overall brand visibility metrics...")
        step_start = time.time()
        
        # Send progress update for generating report
        if progress_sender:
            progress_sender.send_status("generating_report", "Generating report")
        
        try:
            query_analyses = {}
            for query_text, analysis_data in citation_results.items():
                # Reconstruct QueryVisibilityAnalysis objects for metrics calculation
                from core.models.main import QueryVisibilityAnalysis, LLMCitationResult
                
                llm_breakdown = {}
                for llm_name, llm_data in analysis_data["llm_breakdown"].items():
                    llm_breakdown[llm_name] = LLMCitationResult(**llm_data)
                
                query_analyses[query_text] = QueryVisibilityAnalysis(
                    overall_citation_percentage=analysis_data["overall_citation_percentage"],
                    total_mentions=analysis_data["total_mentions"],
                    llm_breakdown=llm_breakdown,
                    explanation=analysis_data["explanation"]
                )
            
            # Create a mapping of query text to intent for the metrics calculation
            query_intents = {q.query: q.intent for q in queries_obj.queries}
            overall_visibility = calculate_brand_visibility_metrics(query_analyses, query_intents)
            
            logger.info(f"✅ Overall brand visibility calculated:")
            logger.info(f"   📊 Average Citation Percentage: {overall_visibility.average_citation_percentage}%")
            logger.info(f"   📈 Queries with Citations: {overall_visibility.queries_with_citations}/{overall_visibility.total_queries_analyzed}")
            
            # Log intent breakdown if available
            if overall_visibility.intent_visibility_breakdown:
                logger.info(f"   📋 Visibility by Intent Type:")
                for intent, stats in overall_visibility.intent_visibility_breakdown.items():
                    if stats["total_queries"] > 0:
                        logger.info(f"      • {intent.capitalize()}: {stats['citation_rate']}% citation rate ({stats['queries_with_citations']}/{stats['total_queries']} queries)")
            
        except Exception as e:
            logger.error(f"❌ Overall metrics calculation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Metrics calculation error: {str(e)}")
        
        step_timings["metrics_calculation"] = time.time() - step_start
        
        # Prepare brand profile for response
        logger.info("📋 Preparing final response...")
        if brand_profile:
            brand_profile_data = brand_profile.model_dump()
        else:
            # Create a minimal profile when using provided data
            brand_profile_data = {
                "icp": request.audience_description,
                "summary": request.brand_summary,
                "products": request.brand_products or "",
                "locales": locales or [],
                "is_international": False
            }
        
        # Calculate intent distribution
        intent_distribution = {
            "navigational": 0,
            "informational": 0,
            "commercial": 0,
            "transactional": 0,
            "awareness": 0,
            "consideration": 0
        }
        
        # Count queries by intent type
        for query in queries_obj.queries:
            intent = query.intent.lower()
            # Handle both "information" and "informational" labels
            if intent == "information":
                intent = "informational"
            if intent in intent_distribution:
                intent_distribution[intent] += 1
        
        # Calculate total time and create comprehensive timing breakdown
        total_time = time.time() - start_time
        
        # Format total time in minutes and seconds
        def format_duration(seconds):
            if seconds >= 60:
                minutes = int(seconds // 60)
                remaining_seconds = seconds % 60
                return f"{minutes}m {remaining_seconds:.1f}s"
            else:
                return f"{seconds:.2f}s"
        
        logger.info(f"🎉 Citation analysis completed successfully!")
        logger.info(f"⏱️ Total processing time: {format_duration(total_time)}")
        
        # Log detailed step-by-step timing breakdown
        logger.info("📊 Detailed timing breakdown:")
        step_percentages = {}
        for step_name, step_duration in step_timings.items():
            percentage = (step_duration / total_time) * 100
            step_percentages[step_name] = percentage
            logger.info(f"   • {step_name.replace('_', ' ').title()}: {format_duration(step_duration)} ({percentage:.1f}%)")
        
        logger.info(f"📊 Final Results Summary:")
        logger.info(f"   🎯 Brand: {request.brand_name}")
        logger.info(f"   ❓ Queries Processed: {len(queries_obj.queries)}")
        logger.info(f"   📈 Average Visibility: {overall_visibility.average_citation_percentage}%")
        logger.info(f"   📋 Intent Distribution: {intent_distribution}")
        
        # Add timing breakdown to the response data for API consumers
        timing_breakdown = {
            "total_duration_seconds": round(total_time, 2),
            "total_duration_formatted": format_duration(total_time),
            "step_timings": {step: round(duration, 2) for step, duration in step_timings.items()},
            "step_percentages": {step: round(percentage, 1) for step, percentage in step_percentages.items()}
        }
        
        # Send final results via progress sender
        if progress_sender:
            progress_sender.send_final_results(
                overall_visibility=overall_visibility.average_citation_percentage,
                queries_analyzed=len(queries_obj.queries),
                intent_distribution=intent_distribution,
                processing_time=round(total_time, 2)
            )
            progress_sender.send_status("completed", "Analysis completed successfully")
        
        return CitationCountResponse(
            brand_profile=brand_profile_data,
            queries=[q.model_dump() for q in queries_obj.queries],
            intent_distribution=intent_distribution,
            citation_analysis=citation_results,
            overall_brand_visibility=overall_visibility.model_dump(),
            timing_breakdown=timing_breakdown
        )
        
    except APIException as e:
        # Handle our custom API exceptions
        total_time = time.time() - start_time
        logger.error(f"💥 API error after {total_time:.2f}s: {e.message}")
        
        # Send error notification via progress sender
        if progress_sender:
            progress_sender.send_error(
                error_message=e.message,
                error_type=e.error_type.value,
                status_code=e.status_code,
                processing_time=round(total_time, 2)
            )
        
        # Re-raise APIException (will be handled by middleware)
        raise
    except HTTPException as e:
        # Handle FastAPI HTTP exceptions
        total_time = time.time() - start_time
        logger.error(f"💥 HTTP error after {total_time:.2f}s: {str(e.detail)}")
        
        # Send error notification via progress sender
        if progress_sender:
            progress_sender.send_error(
                error_message=str(e.detail),
                error_type="http_error",
                status_code=e.status_code,
                processing_time=round(total_time, 2)
            )
        
        # Convert to APIException for consistent handling
        raise ProcessingError(str(e.detail), operation="api_processing")
    except Exception as e:
        # Handle unexpected exceptions
        total_time = time.time() - start_time
        logger.error(f"💥 Unexpected error after {total_time:.2f}s: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Send error notification via progress sender
        if progress_sender:
            progress_sender.send_error(
                error_message=str(e),
                error_type="internal_error",
                processing_time=round(total_time, 2)
            )
        
        # Convert to APIException for consistent handling
        raise ProcessingError(f"Internal server error: {str(e)}", operation="api_processing")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)