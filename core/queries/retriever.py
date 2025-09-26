
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
        # Note: Using session timeout which is set to 15s total
        async with session.get(url) as response:
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


class RobustSessionManager:
    """
    Robust session manager with automatic retry, fallback, and progressive concurrency reduction
    """
    
    def __init__(self, max_concurrent: int = 50):
        self.max_concurrent = max_concurrent
        self.retry_attempts = 3
        self.base_delay = 1.0
        
    async def download_urls_with_retry(self, urls: Set[str]) -> Dict[str, Document]:
        """
        Download URLs with comprehensive retry logic and progressive fallback
        """
        url_to_content = {}
        remaining_urls = set(urls)
        
        # Strategy 1: High concurrency with optimized settings
        if remaining_urls:
            logger.info(f"🚀 Strategy 1: High concurrency ({self.max_concurrent} connections)")
            success_count = await self._try_download_strategy(
                remaining_urls, url_to_content, 
                concurrent=self.max_concurrent,
                timeout_config=(15, 5, 10),
                keepalive=True
            )
            remaining_urls = {url for url in remaining_urls if url not in url_to_content}
            logger.info(f"   ✅ Downloaded {success_count} URLs, {len(remaining_urls)} remaining")
        
        # Strategy 2: Medium concurrency with longer timeouts
        if remaining_urls and len(remaining_urls) > 0:
            logger.info(f"🔄 Strategy 2: Medium concurrency ({self.max_concurrent // 2} connections)")
            success_count = await self._try_download_strategy(
                remaining_urls, url_to_content,
                concurrent=self.max_concurrent // 2,
                timeout_config=(30, 10, 15),
                keepalive=False
            )
            remaining_urls = {url for url in remaining_urls if url not in url_to_content}
            logger.info(f"   ✅ Downloaded {success_count} URLs, {len(remaining_urls)} remaining")
        
        # Strategy 3: Low concurrency, one-by-one with maximum timeouts
        if remaining_urls and len(remaining_urls) > 0:
            logger.info(f"🐌 Strategy 3: Sequential downloads ({len(remaining_urls)} URLs)")
            success_count = await self._try_download_strategy(
                remaining_urls, url_to_content,
                concurrent=5,
                timeout_config=(60, 20, 30),
                keepalive=False,
                use_individual_sessions=True
            )
            remaining_urls = {url for url in remaining_urls if url not in url_to_content}
            logger.info(f"   ✅ Downloaded {success_count} URLs, {len(remaining_urls)} remaining")
        
        # Strategy 4: Create placeholder documents for failed URLs
        if remaining_urls:
            logger.warning(f"⚠️ Creating placeholders for {len(remaining_urls)} failed URLs")
            for url in remaining_urls:
                url_to_content[url] = Document(
                    page_content=f"Content unavailable from {url}",
                    metadata={"source": url, "error": "All download strategies failed"}
                )
        
        return url_to_content
    
    async def _try_download_strategy(self, urls: Set[str], url_to_content: Dict[str, Document], 
                                   concurrent: int, timeout_config: tuple, keepalive: bool, 
                                   use_individual_sessions: bool = False) -> int:
        """
        Try a specific download strategy
        """
        total_timeout, connect_timeout, sock_read_timeout = timeout_config
        success_count = 0
        
        try:
            if use_individual_sessions:
                # Use individual sessions for maximum isolation
                success_count = await self._download_with_individual_sessions(
                    urls, url_to_content, concurrent, timeout_config
                )
            else:
                # Use shared session with connection pooling
                success_count = await self._download_with_shared_session(
                    urls, url_to_content, concurrent, timeout_config, keepalive
                )
        except Exception as e:
            logger.error(f"Strategy failed with error: {str(e)}")
            
        return success_count
    
    async def _download_with_shared_session(self, urls: Set[str], url_to_content: Dict[str, Document],
                                          concurrent: int, timeout_config: tuple, keepalive: bool) -> int:
        """
        Download using a shared session with connection pooling
        """
        total_timeout, connect_timeout, sock_read_timeout = timeout_config
        semaphore = asyncio.Semaphore(concurrent)
        success_count = 0
        
        timeout = aiohttp.ClientTimeout(
            total=total_timeout, 
            connect=connect_timeout, 
            sock_read=sock_read_timeout
        )
        
        connector = aiohttp.TCPConnector(
            limit=concurrent,
            limit_per_host=min(8, concurrent // 3),
            ttl_dns_cache=300,
            keepalive_timeout=30 if keepalive else 0,
            enable_cleanup_closed=True,
            force_close=not keepalive,
            use_dns_cache=True
        )
        
        async def download_with_semaphore(url: str, session: aiohttp.ClientSession):
            async with semaphore:
                try:
                    result = await load_webpage_content_async(url, session)
                    return url, result, True
                except Exception as e:
                    logger.debug(f"Failed to download {url}: {str(e)}")
                    return url, Document(
                        page_content=f"Failed to load content from {url}: {str(e)}",
                        metadata={"source": url, "error": str(e)}
                    ), False
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            tasks = [download_with_semaphore(url, session) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.debug(f"Task exception: {result}")
                else:
                    url, document, success = result
                    url_to_content[url] = document
                    if success:
                        success_count += 1
        
        return success_count
    
    async def _download_with_individual_sessions(self, urls: Set[str], url_to_content: Dict[str, Document],
                                               concurrent: int, timeout_config: tuple) -> int:
        """
        Download using individual sessions for maximum isolation
        """
        total_timeout, connect_timeout, sock_read_timeout = timeout_config
        semaphore = asyncio.Semaphore(concurrent)
        success_count = 0
        
        async def download_individual(url: str):
            async with semaphore:
                timeout = aiohttp.ClientTimeout(
                    total=total_timeout,
                    connect=connect_timeout,
                    sock_read=sock_read_timeout
                )
                
                try:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        result = await load_webpage_content_async(url, session)
                        return url, result, True
                except Exception as e:
                    logger.debug(f"Individual session failed for {url}: {str(e)}")
                    return url, Document(
                        page_content=f"Failed to load content from {url}: {str(e)}",
                        metadata={"source": url, "error": str(e)}
                    ), False
        
        tasks = [download_individual(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.debug(f"Individual task exception: {result}")
            else:
                url, document, success = result
                url_to_content[url] = document
                if success:
                    success_count += 1
        
        return success_count


async def retrieve_queries_context_concurrent(queries: Queries, retriever, content_preloaded=False, max_concurrent=5):
    """
    Ultra-robust version with comprehensive session management and progressive fallback strategies
    
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
    
    logger.info(f"🔍 Starting robust parallel retrieval for {len(queries.queries)} queries...")
    vector_start_time = asyncio.get_event_loop().time()
    
    # Step 1: Execute all vector store queries in parallel with controlled batching
    all_urls: Set[str] = set()
    query_contexts: Dict[str, List] = {}  # Cache vector store results
    
    # Batch queries to avoid overwhelming Pinecone
    from core.config import BatchConfig
    batch_size = BatchConfig.VECTOR_QUERY_BATCH_SIZE
    query_batches = [queries.queries[i:i + batch_size] for i in range(0, len(queries.queries), batch_size)]
    
    logger.info(f"🚀 Executing vector store queries in {len(query_batches)} parallel batches of up to {batch_size}")
    
    async def process_query_batch(batch, batch_idx):
        """Process a batch of queries concurrently"""
        logger.info(f"📦 Processing vector batch {batch_idx + 1}/{len(query_batches)} ({len(batch)} queries)")
        
        # Execute all queries in this batch concurrently
        batch_tasks = [retriever.ainvoke(query.query) for query in batch]
        batch_results = await asyncio.gather(*batch_tasks)
        
        # Process results and collect URLs
        batch_urls = set()
        for query, context_docs in zip(batch, batch_results):
            query_contexts[query.query] = context_docs  # Cache for later use
            
            for doc in context_docs:
                if is_url(doc.page_content):
                    url = doc.page_content.strip()
                    batch_urls.add(url)
                    all_urls.add(url)
        
        logger.info(f"✅ Batch {batch_idx + 1} completed: {len(batch)} queries → {len(batch_urls)} unique URLs")
        return batch_urls
    
    # Process all batches concurrently
    batch_tasks = [process_query_batch(batch, i) for i, batch in enumerate(query_batches)]
    await asyncio.gather(*batch_tasks)
    
    vector_duration = asyncio.get_event_loop().time() - vector_start_time
    logger.info(f"⚡ Vector store queries completed in {vector_duration:.2f}s ({len(queries.queries)/vector_duration:.1f} queries/sec)")
    
    logger.info(f"📥 Need to download {len(all_urls)} unique URLs")
    
    # Step 2: Download all unique URLs using robust session manager
    download_start_time = asyncio.get_event_loop().time()
    
    if all_urls:
        session_manager = RobustSessionManager(max_concurrent=max_concurrent)
        url_to_content = await session_manager.download_urls_with_retry(all_urls)
    else:
        url_to_content = {}
    
    download_duration = asyncio.get_event_loop().time() - download_start_time
    success_count = len([doc for doc in url_to_content.values() if "error" not in doc.metadata])
    logger.info(f"✅ Downloaded {success_count}/{len(all_urls)} pages successfully in {download_duration:.2f}s")
    
    # Step 3: Assemble results using cached vector results
    logger.info("🔗 Assembling final results using cached vector store data...")
    assembly_start_time = asyncio.get_event_loop().time()
    
    retrieved = []
    
    for query in queries.queries:
        # Use cached results instead of calling retriever.ainvoke() again!
        context_docs = query_contexts[query.query]
        full_docs = []
        
        for doc in context_docs:
            if is_url(doc.page_content):
                # Use downloaded content
                url = doc.page_content.strip()
                if url in url_to_content:
                    full_docs.append(url_to_content[url])
                else:
                    # Fallback to placeholder
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
    
    assembly_duration = asyncio.get_event_loop().time() - assembly_start_time
    logger.info(f"🔗 Assembly completed in {assembly_duration:.2f}s")
    
    return retrieved