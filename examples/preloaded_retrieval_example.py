"""
Example script demonstrating how to use the pre-loaded content feature
for improved performance when processing product pages.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.website_crawler.crawler_enhanced import load_sitemap_documents, find_sitemap_url
from core.indexer.indexer_enhanced import get_retriever, save_vector_store, get_retriever_from_saved_store
from core.queries.retriever import retrieve_queries_context_preloaded
from core.models.main import Queries, QueryItem
import os
from dotenv import load_dotenv

load_dotenv()

async def example_preloaded_retrieval():
    """
    Example showing how to use pre-loaded content for better performance.
    """
    # Example configuration
    brand_url = "https://example.com"  # Replace with actual brand URL
    api_key = os.getenv("OPENAI_API_KEY")  # Make sure this is set in your .env file
    
    print("Finding sitemap URL...")
    sitemap_url = find_sitemap_url(brand_url)
    print(f"Found sitemap: {sitemap_url}")
    
    # Option 1: Create retriever with pre-loaded content
    print("\nCreating retriever with pre-loaded content...")
    retriever = get_retriever(
        sitemap_url=sitemap_url,
        api_key=api_key,
        k=4,
        preload_content=True,  # This loads all page content during indexing
        max_pages=10  # Limit for testing
    )
    print("Retriever created with pre-loaded content!")
    
    # Create sample queries
    sample_queries = Queries(
        queries=[
            QueryItem(
                query="best running shoes for marathon",
                intent="purchase",
                sub_intent="compare",
                persona="enthusiast",
                category="footwear",
                expected_brand_relevance="high",
                locale="en-US",
                notes="User looking for high-performance marathon shoes"
            ),
            QueryItem(
                query="waterproof hiking boots",
                intent="research",
                sub_intent="features",
                persona="novice",
                category="footwear",
                expected_brand_relevance="medium",
                locale="en-US",
                notes="User needs boots for wet conditions"
            )
        ]
    )
    
    # Retrieve context using pre-loaded documents
    print("\nRetrieving context for queries...")
    retrieved = await retrieve_queries_context_preloaded(sample_queries, retriever)
    
    print(f"\nRetrieved context for {len(retrieved)} queries:")
    for item in retrieved:
        query = item["query"]
        context_docs = item["context"]
        print(f"\nQuery: {query.query}")
        print(f"Number of context documents: {len(context_docs)}")
        if context_docs:
            # Show snippet of first document
            first_doc = context_docs[0]
            content_preview = first_doc.page_content[:200] + "..." if len(first_doc.page_content) > 200 else first_doc.page_content
            print(f"First document preview: {content_preview}")
            print(f"Document metadata: {first_doc.metadata}")
    
    # Option 2: Save and load vector store for reuse
    print("\n\nSaving vector store to disk for future use...")
    vector_store_path = "./saved_vector_stores/example_brand"
    
    # Note: To save the vector store, we need to access it from the retriever
    # This is a simplified example - in practice, you might want to expose this functionality
    print(f"Vector store would be saved to: {vector_store_path}")
    
    print("\nExample completed!")

async def example_performance_comparison():
    """
    Example comparing performance between URL-only and pre-loaded approaches.
    """
    import time
    
    brand_url = "https://example.com"  # Replace with actual brand URL
    api_key = os.getenv("OPENAI_API_KEY")
    
    sitemap_url = find_sitemap_url(brand_url)
    
    # Test queries
    test_queries = Queries(
        queries=[
            QueryItem(
                query="product features and benefits",
                intent="research",
                sub_intent="features",
                persona="novice",
                category="general",
                expected_brand_relevance="high",
                locale="en-US",
                notes="General product inquiry"
            )
        ]
    )
    
    # Method 1: Traditional approach (URL-only indexing)
    print("Method 1: URL-only indexing (loads content on-demand)")
    start_time = time.time()
    
    retriever_traditional = get_retriever(
        sitemap_url=sitemap_url,
        api_key=api_key,
        k=4,
        preload_content=False,  # Traditional approach
        max_pages=10
    )
    
    retrieved_traditional = await retrieve_queries_context(
        test_queries, 
        retriever_traditional,
        preloaded=False
    )
    
    traditional_time = time.time() - start_time
    print(f"Time taken: {traditional_time:.2f} seconds")
    
    # Method 2: Pre-loaded approach
    print("\nMethod 2: Pre-loaded content indexing")
    start_time = time.time()
    
    retriever_preloaded = get_retriever(
        sitemap_url=sitemap_url,
        api_key=api_key,
        k=4,
        preload_content=True,  # Pre-load all content
        max_pages=10
    )
    
    # First retrieval (includes loading time)
    retrieved_preloaded = await retrieve_queries_context_preloaded(
        test_queries,
        retriever_preloaded
    )
    
    first_retrieval_time = time.time() - start_time
    print(f"Time for first retrieval (includes loading): {first_retrieval_time:.2f} seconds")
    
    # Subsequent retrieval (content already loaded)
    start_time = time.time()
    retrieved_preloaded_2 = await retrieve_queries_context_preloaded(
        test_queries,
        retriever_preloaded
    )
    subsequent_retrieval_time = time.time() - start_time
    print(f"Time for subsequent retrieval: {subsequent_retrieval_time:.2f} seconds")
    
    print(f"\nPerformance improvement for subsequent queries: {traditional_time/subsequent_retrieval_time:.2f}x faster")

if __name__ == "__main__":
    print("Pre-loaded Retrieval Example")
    print("=" * 50)
    
    # Run the example
    asyncio.run(example_preloaded_retrieval())
    
    # Uncomment to run performance comparison
    # print("\n\nPerformance Comparison")
    # print("=" * 50)
    # asyncio.run(example_performance_comparison())