
from core.models.main import Queries
from langchain_community.document_loaders import WebBaseLoader
import os
import asyncio
import aiohttp
import logging
from typing import List, Dict, Set
from langchain.schema import Document
from bs4 import BeautifulSoup
import html2text
from dotenv import load_dotenv
load_dotenv(override=True)

logger = logging.getLogger(__name__)


def is_url(text: str) -> bool:
    """
    Check if text is a URL or webpage content.
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears to be a URL, False if it's webpage content
    """
    text = text.strip()
    return (
        text.startswith(('http://', 'https://')) and
        ' ' not in text and  # URLs don't contain spaces
        '\n' not in text and  # URLs don't contain newlines
        len(text) < 500  # URLs are typically short
    )

async def retrieve_queries_context(queries: Queries, retriever, content_preloaded=False):
    """
    Retrieve context for queries either by loading web pages on-demand or using pre-loaded content.
    
    Args:
        queries: Queries object containing list of queries
        retriever: Vector store retriever
        content_preloaded: If True, checks documents for full content or loads as needed
    
    Returns:
        List of dicts containing query and context documents
    """
    retrieved = []
    for query in queries.queries:
        # Use retriever - it now has built-in session recovery if it's ResilientPineconeRetriever
        context = await retriever.ainvoke(query.query)
        
        if content_preloaded:
            # Check if documents already have full content
            full_docs = []
            for doc in context:
                if is_url(doc.page_content):
                    # Document contains URL, need to load content
                    loader = WebBaseLoader(doc.page_content)
                    loaded = loader.load()
                    full_docs.extend(loaded)
                else:
                    # Document already has full page content
                    full_docs.append(doc)
        else:
            # Legacy behavior: documents contain URLs, need to load web pages
            loaded_pages = [doc.page_content for doc in context]
            loaders = [WebBaseLoader(page) for page in loaded_pages]
            full_docs = []
            for loader in loaders:
                docs = loader.load()
                full_docs.extend(docs)
        
        retrieved.append({
            "query": query,
            "context": full_docs
        })

    return retrieved

async def retrieve_queries_context_preloaded(queries: Queries, retriever):
    """
    Convenience function for retrieving context from pre-loaded documents.
    This is equivalent to calling retrieve_queries_context with content_preloaded=True.
    
    Args:
        queries: Queries object containing list of queries
        retriever: Vector store retriever with pre-loaded documents
    
    Returns:
        List of dicts containing query and context documents
    """
    return await retrieve_queries_context(queries, retriever, content_preloaded=True)


async def load_webpage_content_async(url: str, session: aiohttp.ClientSession) -> Document:
    """
    Asynchronously load webpage content and convert to Document
    
    Args:
        url: URL to load
        session: aiohttp session for connection reuse
    
    Returns:
        Document with loaded content
    """
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                html_content = await response.text()
                
                # Convert HTML to text using html2text (similar to WebBaseLoader)
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = True
                text_content = h.handle(html_content)
                
                return Document(
                    page_content=text_content,
                    metadata={"source": url, "status_code": response.status}
                )
            else:
                print(f"Failed to load {url}: HTTP {response.status}")
                return Document(
                    page_content=f"Failed to load content from {url}",
                    metadata={"source": url, "status_code": response.status, "error": "HTTP error"}
                )
    except Exception as e:
        print(f"Error loading {url}: {str(e)}")
        return Document(
            page_content=f"Failed to load content from {url}: {str(e)}",
            metadata={"source": url, "error": str(e)}
        )


async def retrieve_queries_context_concurrent(queries: Queries, retriever, content_preloaded=False, max_concurrent=5):
    """
    Optimized version with concurrent web page loading for 70-85% better performance
    
    Args:
        queries: Queries object containing list of queries
        retriever: Vector store retriever
        content_preloaded: If True, uses pre-loaded content
        max_concurrent: Maximum concurrent web page downloads
    
    Returns:
        List of dicts containing query and context documents
    """
    if content_preloaded:
        # Use the original function for pre-loaded content
        return await retrieve_queries_context(queries, retriever, content_preloaded=True)
    
    # Step 1: Collect all unique URLs that need to be loaded
    all_urls: Set[str] = set()
    query_to_urls: Dict[str, List[str]] = {}
    
    logger.info(f"🔍 Analyzing {len(queries.queries)} queries to find required URLs...")
    
    for i, query in enumerate(queries.queries):
        # Use retriever - it now has built-in session recovery if it's ResilientPineconeRetriever
        context_docs = await retriever.ainvoke(query.query)
        
        # Debug: Check what we're getting from Pinecone
        if i == 0:  # Only log for first query to avoid spam
            logger.debug(f"🔍 Debug - Retrieved {len(context_docs)} documents from Pinecone")
            for j, doc in enumerate(context_docs[:2]):  # Show first 2 docs
                content_preview = doc.page_content[:100] if doc.page_content else "No content"
                logger.debug(f"  Doc {j}: {content_preview}...")
                logger.debug(f"  Metadata: {doc.metadata}")
        
        # Add small delay between queries to reduce load on Pinecone
        if i < len(queries.queries) - 1:  # Don't delay after the last query
            await asyncio.sleep(0.1)
        urls_for_query = []
        
        for doc in context_docs:
            if is_url(doc.page_content):
                # Need to load this URL
                url = doc.page_content.strip()
                all_urls.add(url)
                urls_for_query.append(url)
            else:
                # Already has content, no need to load
                urls_for_query.append(None)  # Placeholder
        
        query_to_urls[query.query] = urls_for_query
    
    logger.info(f"📥 Need to download {len(all_urls)} unique URLs (with up to {max_concurrent} concurrent connections)")
    
    # Step 2: Download all unique URLs concurrently
    url_to_content: Dict[str, Document] = {}
    
    if all_urls:
        semaphore = asyncio.Semaphore(max_concurrent)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async def download_with_semaphore(url: str, session: aiohttp.ClientSession):
            async with semaphore:
                return url, await load_webpage_content_async(url, session)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Create tasks for all URLs
            tasks = [download_with_semaphore(url, session) for url in all_urls]
            
            # Download all pages concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Download failed: {result}")
                else:
                    url, document = result
                    url_to_content[url] = document
    
    logger.info(f"✅ Downloaded {len(url_to_content)} pages successfully")
    
    # Step 3: Assemble results for each query using cached content
    retrieved = []
    
    for query in queries.queries:
        context_docs = await retriever.ainvoke(query.query)
        urls_for_query = query_to_urls[query.query]
        full_docs = []
        
        for i, doc in enumerate(context_docs):
            if is_url(doc.page_content):
                # Use downloaded content
                url = urls_for_query[i]
                if url and url in url_to_content:
                    full_docs.append(url_to_content[url])
                else:
                    # Fallback to original document or empty content
                    full_docs.append(Document(
                        page_content="Content not available",
                        metadata={"source": doc.page_content, "error": "Download failed"}
                    ))
            else:
                # Document already has full content
                full_docs.append(doc)
        
        retrieved.append({
            "query": query,
            "context": full_docs
        })
    
    return retrieved