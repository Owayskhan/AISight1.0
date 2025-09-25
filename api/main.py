from fastapi import FastAPI, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, List, Optional, Any
import sys
from pathlib import Path
import logging
import time

# Add parent directory to path to import core modules
sys.path.append(str(Path(__file__).parent.parent))

from core.website_crawler.crawler import find_sitemap_url, load_single_product_document
from core.indexer.indexer_optimized import  create_vector_store_optimized, get_smart_retriever
from core.brand_profiler.main import research_brand_info
from core.queries.generator import generate_queries, generate_product_queries
from core.queries.retriever import retrieve_queries_context_concurrent
from core.queries.answer_generator import run_query_answering_chain
from core.citation_counter.counter import analyze_query_visibility, calculate_brand_visibility_metrics
from core.models.main import Queries
from core.utils import get_progress_sender,  get_distribution_summary, get_plan_filtered_distribution
from langchain_openai import ChatOpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Citation Count API", version="1.0.0")


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
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    gemini_api_key: Optional[str] = Field(None, description="Google Gemini API key")
    perplexity_api_key: Optional[str] = Field(None, description="Perplexity API key")
    
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
    # Subscription plan
    plan: str = Field("free", description="User subscription plan: 'free' or 'paid'. Free plan only generates informational and awareness queries.")
    
    @field_validator('url_type')
    @classmethod
    def validate_url_type(cls, v):
        if v not in ['website', 'product']:
            raise ValueError("url_type must be either 'website' or 'product'")
        return v
    
    @field_validator('plan')
    @classmethod
    def validate_plan(cls, v):
        if v not in ['free', 'paid']:
            raise ValueError("plan must be either 'free' or 'paid'")
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
        # OpenAI is required for core functionality (embeddings, query generation, citation analysis)
        if not v.openai_api_key:
            raise ValueError("openai_api_key is required for embeddings, query generation, and citation analysis")
        
        # Gemini is required if brand profile info is not provided
        audience_desc = info.data.get('audience_description')
        brand_summary = info.data.get('brand_summary')
        if not (audience_desc and brand_summary) and not v.gemini_api_key:
            raise ValueError("gemini_api_key is required when audience_description and brand_summary are not provided")
        
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
                "custom_query_generation_instructions": "Focus on eco-friendly and sustainable product options. Include queries about environmental impact and certifications.",
                "plan": "free"
            }
        }

class CitationCountResponse(BaseModel):
    brand_profile: Dict[str, Any]
    queries: List[Dict[str, Any]]
    intent_distribution: Dict[str, int] = Field(..., description="Distribution of queries by intent type")
    citation_analysis: Dict[str, Dict[str, Any]]
    overall_brand_visibility: Dict[str, Any]
    plan_used: str = Field(..., description="Subscription plan used for the analysis")
    
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
                
            except Exception as e:
                logger.error(f"❌ Product processing failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Product processing error: {str(e)}")
            
        else:
            logger.info("🌐 Processing website URL...")
            # Website flow (existing logic)
            # Step 1: Find sitemap URL if not provided
            if request.sitemap_url:
                sitemap_url = request.sitemap_url
                logger.info(f"📋 Using provided sitemap URL: {sitemap_url}")
            else:
                logger.info("🔍 Auto-discovering sitemap URL...")
                try:
                    sitemap_url = find_sitemap_url(request.brand_url)
                    logger.info(f"✅ Sitemap discovered: {sitemap_url}")
                except ValueError as e:
                    logger.error(f"❌ Sitemap discovery failed: {str(e)}")
                    raise HTTPException(status_code=400, detail=str(e))
            
            # Step 2: Smart indexing with Pinecone or FAISS fallback
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
                retriever = await get_smart_retriever(
                    brand_name=request.brand_name,
                    sitemap_url=sitemap_url, 
                    api_key=request.api_keys.openai_api_key,
                    k=4,
                    batch_size=request.indexing_batch_size,
                    use_pinecone=request.use_pinecone,
                    force_reindex=request.force_reindex,
                    use_parallel_sitemap=True,  # Always use parallel sitemap loading
                    progress_callback=indexing_progress_callback
                )
                content_preloaded = False  # URLs indexed, content loaded during retrieval
                logger.info("✅ Smart retriever created successfully")
                
            except Exception as e:
                logger.error(f"❌ Sitemap processing failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Sitemap processing error: {str(e)}")
        
        # Step 2: Handle brand profile - either use provided info or generate it
        logger.info("👥 Processing brand profile...")
        
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

                brand_profile = research_brand_info(
                    brand_name=request.brand_name,
                    brand_url=request.brand_url,
                    gemini_api_key=request.api_keys.gemini_api_key,
                    tavily_api_key=os.getenv("TAVILY_API_KEY", "")
                )
                audience_description = brand_profile.icp
                brand_summary = brand_profile.summary
                locales = brand_profile.locales
                logger.info("✅ Brand profile generated successfully")
                logger.info(f"🎯 Target audience: {audience_description[:100]}...")
                
            except Exception as e:
                logger.error(f"❌ Brand profile generation failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Brand profile generation error: {str(e)}")
        
        # Step 3: Generate queries based on URL type
        logger.info(f"❓ Generating {request.k} queries...")
        
        # Log if custom instructions are provided
        if request.custom_query_generation_instructions:
            logger.info(f"📝 Using custom query generation instructions: {request.custom_query_generation_instructions[:100]}...")
        
        # Show query distribution based on plan
        distribution = get_plan_filtered_distribution(request.k, request.plan)
        distribution_summary = get_distribution_summary(distribution)
        logger.info(f"📊 Query Distribution ({request.plan} plan): {distribution_summary}")
        
        # Send progress update for generating queries
        if progress_sender:
            progress_sender.send_status("generating_queries", "Generating queries")
        
        try:
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
                
                queries = await generate_product_queries(
                    product_name=request.brand_name,
                    product_description=product_desc,
                    product_type=product_type,
                    openai_api_key=request.api_keys.openai_api_key,
                    audience_description=audience_description,
                    k=request.k,
                    custom_instructions=request.custom_query_generation_instructions,
                    plan=request.plan
                )
            else:
                logger.info("🌐 Using category-based query generation")
                queries = await generate_queries(
                    product_category=request.product_category,
                    openai_api_key=request.api_keys.openai_api_key,
                    audience_description=audience_description,
                    locales=locales,
                    brand_summary=brand_summary,
                    brand_products=request.brand_products,
                    k=request.k,
                    custom_instructions=request.custom_query_generation_instructions,
                    plan=request.plan
                )
            
            queries_obj = Queries(**queries)
            logger.info(f"✅ Generated {len(queries_obj.queries)} queries successfully")
            for i, query in enumerate(queries_obj.queries[:3], 1):  # Show first 3 queries
                logger.info(f"   {i}. {query.query} ({query.intent})")
            if len(queries_obj.queries) > 3:
                logger.info(f"   ... and {len(queries_obj.queries) - 3} more queries")
                
        except Exception as e:
            logger.error(f"❌ Query generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Query generation error: {str(e)}")
        
        # Step 4: Retrieve context for queries
        logger.info("🔍 Retrieving context for queries...")
        try:
            # Use concurrent context retrieval for better performance
            retrieved_queries = await retrieve_queries_context_concurrent(
                queries_obj, 
                retriever, 
                content_preloaded=content_preloaded,
                max_concurrent=20  # Allow up to 20 concurrent downloads
            )
            logger.info(f"✅ Retrieved context for {len(retrieved_queries)} queries")
            
        except Exception as e:
            logger.error(f"❌ Context retrieval failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Context retrieval error: {str(e)}")
        
        # Step 5: Generate answers and analyze visibility
        logger.info("🤖 Starting LLM answer generation and citation analysis...")
        import asyncio
        
        # Initialize LLM for citation analysis (using OpenAI for consistency)
        citation_llm = ChatOpenAI(api_key=request.api_keys.openai_api_key, model="gpt-4o-mini", temperature=0)
        logger.info("✅ Citation analysis LLM initialized")
        
        total_queries = len(retrieved_queries)
        logger.info(f"🚀 Processing {total_queries} queries with concurrent optimization...")
        
        async def process_single_query(idx, item):
            query = item["query"]
            context = item["context"]
            
            logger.info(f"🔄 Processing query {idx}/{total_queries}: '{query.query[:60]}...'")
            
            try:
                # Generate answers from all LLMs (already concurrent within this function)
                num_llms = sum(1 for key in ["openai_api_key", "gemini_api_key", "perplexity_api_key"] 
                             if getattr(request.api_keys, key))
                logger.info(f"   🤖 Generating answers from {num_llms} LLMs...")
                llm_responses = await run_query_answering_chain(
                    query=query.query,
                    context=context,
                    brand_name=request.brand_name,
                    api_keys={
                        "OPENAI_API_KEY": request.api_keys.openai_api_key,
                        "GOOGLE_API_KEY": request.api_keys.gemini_api_key,
                        "PERPLEXITY_API_KEY": request.api_keys.perplexity_api_key
                    }
                )
                logger.info(f"   ✅ Got responses from {len(llm_responses)} LLMs")
                
                # Analyze visibility for this query across all LLMs (already concurrent within this function)
                logger.info(f"   📊 Analyzing brand visibility...")
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
        
        # Process queries with adaptive batch sizing based on available LLMs
        citation_results = {}
        
        # Calculate optimal batch size based on number of active LLMs and total queries
        active_llms = sum(1 for key in ["openai_api_key", "gemini_api_key", "perplexity_api_key"] 
                         if getattr(request.api_keys, key))
        
        # Adaptive batch sizing logic:
        # - 1 LLM: batch_size = 4-5 (can handle more queries since less API pressure)
        # - 2 LLMs: batch_size = 3-4 (moderate batching)
        # - 3 LLMs: batch_size = 2-3 (conservative to avoid rate limits)
        if active_llms == 1:
            batch_size = min(5, max(4, total_queries // 3))  # 4-5 queries per batch
        elif active_llms == 2:
            batch_size = min(4, max(3, total_queries // 4))  # 3-4 queries per batch
        else:  # 3 LLMs
            batch_size = min(3, max(2, total_queries // 5))  # 2-3 queries per batch
        
        # Ensure at least 1 query per batch
        batch_size = max(1, batch_size)
        
        logger.info(f"🚀 Using adaptive batch size: {batch_size} (based on {active_llms} active LLMs, {total_queries} total queries)")
        
        for i in range(0, len(retrieved_queries), batch_size):
            batch = retrieved_queries[i:i + batch_size]
            logger.info(f"📦 Processing batch {i//batch_size + 1}/{(len(retrieved_queries) + batch_size - 1)//batch_size}")
            
            # Send progress update for running queries
            if progress_sender:
                # Get model names that will be used
                models = []
                if request.api_keys.openai_api_key:
                    models.append("OpenAI")
                if request.api_keys.gemini_api_key:
                    models.append("Gemini")
                if request.api_keys.perplexity_api_key:
                    models.append("Perplexity")
                    
                progress_sender.send_progress(
                    current=i,
                    total=len(retrieved_queries),
                    step=f"Running queries over {', '.join(models)}"
                )
            
            # Create tasks for current batch
            tasks = [process_single_query(i + j + 1, item) for j, item in enumerate(batch)]
            
            # Process batch concurrently
            batch_results = await asyncio.gather(*tasks)
            
            # Update results
            for query_text, analysis in batch_results:
                citation_results[query_text] = analysis
            
            # Add adaptive delay between batches to prevent rate limiting
            # Smaller batches = shorter delays, larger batches = longer delays
            if i + batch_size < len(retrieved_queries):
                delay = max(0.5, min(2.0, batch_size * 0.3))  # 0.5-2.0 second delay based on batch size
                await asyncio.sleep(delay)
        
        # Calculate overall brand visibility metrics
        logger.info("📈 Calculating overall brand visibility metrics...")
        
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
        
        # Calculate total time
        total_time = time.time() - start_time
        logger.info(f"🎉 Citation analysis completed successfully!")
        logger.info(f"⏱️ Total processing time: {total_time:.2f} seconds")
        logger.info(f"📊 Final Results Summary:")
        logger.info(f"   🎯 Brand: {request.brand_name}")
        logger.info(f"   ❓ Queries Processed: {len(queries_obj.queries)}")
        logger.info(f"   📈 Average Visibility: {overall_visibility.average_citation_percentage}%")
        logger.info(f"   📋 Intent Distribution: {intent_distribution}")
        
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
            plan_used=request.plan
        )
        
    except HTTPException as e:
        # Send error notification via progress sender
        if progress_sender:
            progress_sender.send_error(
                error_message=str(e.detail),
                error_type="http_error",
                status_code=e.status_code
            )
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors
        total_time = time.time() - start_time
        logger.error(f"💥 Unexpected error after {total_time:.2f}s: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        
        # Send error notification via progress sender
        if progress_sender:
            progress_sender.send_error(
                error_message=str(e),
                error_type="internal_error",
                processing_time=round(total_time, 2)
            )
        
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)