from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
import sys
from pathlib import Path
import logging
import time

# Add parent directory to path to import core modules
sys.path.append(str(Path(__file__).parent.parent))

from core.website_crawler.crawler import load_sitemap_documents, find_sitemap_url, load_single_product_document
from core.indexer.indexer import get_retriever, create_vector_store
from core.brand_profiler.main import research_brand_info
from core.queries.generator import generate_queries, generate_product_queries
from core.queries.retriever import retrieve_queries_context
from core.queries.answer_generator import run_query_answering_chain
from core.citation_counter.counter import analyze_query_visibility, calculate_brand_visibility_metrics
from core.models.main import Queries
from langchain_openai import ChatOpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Citation Count API", version="1.0.0")

class APIKeys(BaseModel):
    openai_api_key: str = Field(..., description="OpenAI API key")
    gemini_api_key: str = Field(..., description="Google Gemini API key")
    perplexity_api_key: str = Field(..., description="Perplexity API key")

class CitationCountRequest(BaseModel):
    brand_name: str = Field(..., description="Name of the brand")
    brand_url: str = Field(..., description="Brand website URL or specific product URL")
    url_type: str = Field("website", description="Type of URL: 'website' or 'product'")
    sitemap_url: Optional[str] = Field(None, description="Sitemap URL (optional - will be auto-discovered if not provided)")
    product_category: str = Field(..., description="Product category for query generation")
    api_keys: APIKeys = Field(..., description="API keys for different services")
    k: int = Field(10, description="Number of queries to generate", ge=1, le=50)
    # Optional brand profile fields - if provided, skip brand profiling step
    audience_description: Optional[str] = Field(None, description="Target audience/ICP description (optional)")
    brand_summary: Optional[str] = Field(None, description="Brand summary (optional)")
    brand_products: Optional[str] = Field(None, description="Brand products description (optional)")
    # Product-specific fields (only for url_type='product')
    product_description: Optional[str] = Field(None, description="Product description (optional - will be extracted if not provided)")
    product_type: Optional[str] = Field(None, description="Product type/category (optional - will be extracted if not provided)")
    
    @validator('url_type')
    def validate_url_type(cls, v):
        if v not in ['website', 'product']:
            raise ValueError("url_type must be either 'website' or 'product'")
        return v
    
    @validator('sitemap_url')
    def validate_sitemap_url(cls, v, values):
        url_type = values.get('url_type', 'website')
        if url_type == 'product' and v is not None:
            raise ValueError("sitemap_url should not be provided when url_type is 'product'")
        return v
    class Config:
        schema_extra = {
            "example": {
                "brand_name": "Example Brand",
                "brand_url": "https://example.com",
                "url_type": "website",
                "product_category": "Electronics",
                "k": 10,
                "api_keys": {
                    "openai_api_key": "sk-...",
                    "gemini_api_key": "AIza...",
                    "perplexity_api_key": "pplx-..."
                }
            }
        }

class CitationCountResponse(BaseModel):
    brand_profile: Dict[str, Any]
    queries: List[Dict[str, Any]]
    citation_analysis: Dict[str, Dict[str, Any]]
    overall_brand_visibility: Dict[str, Any]
    
@app.get("/")
async def root():
    return {"message": "Citation Count API", "endpoints": ["/analyze"]}

@app.post("/analyze", response_model=CitationCountResponse)
async def analyze_citation_count(request: CitationCountRequest):
    start_time = time.time()
    logger.info(f"🚀 Starting citation analysis for brand: {request.brand_name}")
    logger.info(f"📊 URL type: {request.url_type}, Category: {request.product_category}, Queries to generate: {request.k}")
    
    try:
        # API keys are already validated by Pydantic model
        logger.info("✅ API keys validated successfully")
        
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
                vector_store = await create_vector_store(product_docs, request.api_keys.openai_api_key)
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
            
            # Step 2: Extract and index sitemap URLs
            logger.info("📥 Loading sitemap documents...")
            try:
                sitemap_docs = load_sitemap_documents(sitemap_url)
                if not sitemap_docs:
                    logger.error("❌ No URLs found in sitemap")
                    raise HTTPException(status_code=400, detail="No URLs found in sitemap")
                
                logger.info(f"✅ Loaded {len(sitemap_docs)} URLs from sitemap")
                
                logger.info("🔍 Creating retriever from sitemap...")
                retriever = await get_retriever(sitemap_url, request.api_keys.openai_api_key)
                content_preloaded = False
                logger.info("✅ Retriever created successfully")
                
            except Exception as e:
                logger.error(f"❌ Sitemap processing failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Sitemap processing error: {str(e)}")
        
        # Step 2: Handle brand profile - either use provided info or generate it
        logger.info("👥 Processing brand profile...")
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
                    k=request.k
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
                    k=request.k
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
            retrieved_queries = await retrieve_queries_context(
                queries_obj, 
                retriever, 
                content_preloaded=content_preloaded
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
                logger.info(f"   🤖 Generating answers from 3 LLMs...")
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
                    citation_llm=citation_llm
                )
                
                citation_percentage = visibility_analysis.overall_citation_percentage
                logger.info(f"   ✅ Visibility: {citation_percentage}% ({visibility_analysis.explanation})")
                
                return query.query, visibility_analysis.model_dump()
                
            except Exception as e:
                logger.error(f"   ❌ Failed processing query {idx}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Query processing error for query {idx}: {str(e)}")
        
        # Process queries with controlled concurrency (batches of 3 to respect API limits)
        citation_results = {}
        batch_size = 3  # Process 3 queries at a time to balance speed vs API limits
        
        for i in range(0, len(retrieved_queries), batch_size):
            batch = retrieved_queries[i:i + batch_size]
            logger.info(f"📦 Processing batch {i//batch_size + 1}/{(len(retrieved_queries) + batch_size - 1)//batch_size}")
            
            # Create tasks for current batch
            tasks = [process_single_query(i + j + 1, item) for j, item in enumerate(batch)]
            
            # Process batch concurrently
            batch_results = await asyncio.gather(*tasks)
            
            # Update results
            for query_text, analysis in batch_results:
                citation_results[query_text] = analysis
        
        # Calculate overall brand visibility metrics
        logger.info("📈 Calculating overall brand visibility metrics...")
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
            
            overall_visibility = calculate_brand_visibility_metrics(query_analyses)
            
            logger.info(f"✅ Overall brand visibility calculated:")
            logger.info(f"   📊 Average Citation Percentage: {overall_visibility.average_citation_percentage}%")
            logger.info(f"   📈 Queries with Citations: {overall_visibility.queries_with_citations}/{overall_visibility.total_queries_analyzed}")
            
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
        
        # Calculate total time
        total_time = time.time() - start_time
        logger.info(f"🎉 Citation analysis completed successfully!")
        logger.info(f"⏱️ Total processing time: {total_time:.2f} seconds")
        logger.info(f"📊 Final Results Summary:")
        logger.info(f"   🎯 Brand: {request.brand_name}")
        logger.info(f"   ❓ Queries Processed: {len(queries_obj.queries)}")
        logger.info(f"   📈 Average Visibility: {overall_visibility.average_citation_percentage}%")
        
        return CitationCountResponse(
            brand_profile=brand_profile_data,
            queries=[q.model_dump() for q in queries_obj.queries],
            citation_analysis=citation_results,
            overall_brand_visibility=overall_visibility.model_dump()
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors
        total_time = time.time() - start_time
        logger.error(f"💥 Unexpected error after {total_time:.2f}s: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)