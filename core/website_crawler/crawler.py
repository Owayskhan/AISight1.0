
from langchain_community.document_loaders import WebBaseLoader
import requests
from xml.etree import ElementTree as ET
from langchain.schema import Document
from urllib.parse import urljoin, urlparse
import re
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
import json
import html2text
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_openai import ChatOpenAI
from core.models.main import ProductInfo
import logging
import asyncio
import aiohttp
from core.utils.error_handling import (
    handle_api_error,
    async_retry,
    ExternalServiceError,
    ValidationError,
    ProcessingError,
    CircuitBreaker
)
from core.utils.rate_limiter import rate_limit, wait_for_rate_limit

logger = logging.getLogger(__name__)

@async_retry(retries=2, delay=1.0, max_delay=10.0)
async def find_sitemap_url_async(website_url: str) -> str:
    """
    Asynchronously find the sitemap URL for a given website with error handling.
    """
    try:
        if not website_url:
            raise ValidationError("Website URL is required")
        
        # Ensure URL has proper scheme
        if not urlparse(website_url).scheme:
            website_url = f"https://{website_url}"
        
        logger.info(f"Searching for sitemap at {website_url}")
        
        # Common sitemap locations (prioritized order - robots.txt first, then common paths)
        sitemap_paths = [
            '/robots.txt',  # Check robots.txt first - often has sitemap URL
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemap-index.xml',
            '/sitemaps.xml',
            '/sitemap/',
            '/sitemap/sitemap.xml',
            '/sitemap/index.xml',
            '/product-sitemap.xml',
            '/en/sitemap.xml',
            '/us/sitemap.xml',
            '/us_en/sitemap.xml',
            '/sitemap.txt',
            '/sitemap.xml.gz'
        ]

        timeout = aiohttp.ClientTimeout(total=15)

        # Headers to appear as legitimate bot
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AISightBot/1.0; +https://github.com/anthropics/aisight)',
            'Accept': 'application/xml,text/xml,application/rss+xml,text/html,*/*',
            'Accept-Language': 'en-US,en;q=0.9'
        }

        async def check_path(session: aiohttp.ClientSession, path: str) -> Optional[str]:
            sitemap_url = urljoin(website_url, path)

            try:
                async with session.get(sitemap_url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()

                        if path == '/robots.txt':
                            for line in content.splitlines():
                                if line.lower().startswith('sitemap:'):
                                    sitemap_from_robots = line.split(':', 1)[1].strip()
                                    logger.info(f"Found sitemap in robots.txt: {sitemap_from_robots}")
                                    return sitemap_from_robots
                        else:
                            try:
                                ET.fromstring(content.encode('utf-8'))
                                logger.debug(f"Valid sitemap found at: {sitemap_url}")
                                return sitemap_url
                            except ET.ParseError:
                                logger.debug(f"Path {path} returned 200 but not valid XML")
                                pass
                return None
            except Exception as e:
                logger.debug(f"Path {path} failed: {type(e).__name__}: {str(e)[:100]}")
                return None

        # Apply rate limiting once for all requests (not per request)
        await wait_for_rate_limit("web_scraping", tokens=len(sitemap_paths))

        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [check_path(session, path) for path in sitemap_paths]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, str) and result:
                    return result
        
        raise ValueError(f"Could not find sitemap for {website_url}")
        
    except Exception as e:
        if isinstance(e, (ValidationError, ValueError)):
            raise
        else:
            raise ExternalServiceError(
                f"Failed to find sitemap: {str(e)}",
                service="web_scraping"
            )


def find_sitemap_url(website_url: str) -> str:
    """
    Synchronous wrapper for find_sitemap_url_async.
    Dynamically find the sitemap URL for a given website.
    """
    try:
        return asyncio.run(find_sitemap_url_async(website_url))
    except Exception as e:
        # Handle the async version's exceptions in sync context
        raise
    # For backward compatibility, fall back to the original synchronous implementation
    # if async version fails
    try:
        # Ensure URL has proper scheme
        if not urlparse(website_url).scheme:
            website_url = f"https://{website_url}"
        
        # Common sitemap locations
        sitemap_paths = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemap-index.xml',
            '/sitemaps.xml',
            '/sitemap/',
            '/sitemap.txt',
            '/sitemap.xml.gz',
            '/robots.txt'
        ]
        
        for path in sitemap_paths:
            sitemap_url = urljoin(website_url, path)
            try:
                response = requests.get(sitemap_url, timeout=10)
                if response.status_code == 200:
                    if path == '/robots.txt':
                        for line in response.text.splitlines():
                            if line.lower().startswith('sitemap:'):
                                return line.split(':', 1)[1].strip()
                    else:
                        try:
                            ET.fromstring(response.content)
                            return sitemap_url
                        except ET.ParseError:
                            continue
            except Exception:
                continue
        
        raise ValueError(f"Could not find sitemap for {website_url}")
    except Exception as e:
        logger.error(f"Error finding sitemap: {e}")
        raise

def load_sitemap_documents(sitemap_url: str):
    sitemap = get_sitemap_urls(sitemap_url)

    sitemap_docs = []
    for url in sitemap:
        doc = Document(
            page_content=url, metadata={"source": url}
        )
        sitemap_docs.append(doc)
    
    return sitemap_docs

async def load_sitemap_documents_parallel(sitemap_url: str, max_concurrent: int = 50):
    """
    Load sitemap documents with parallel processing for better performance
    
    Args:
        sitemap_url: URL of the sitemap
        max_concurrent: Maximum concurrent URL processing
    
    Returns:
        List of Document objects
    """
    import asyncio
    import aiohttp
    from xml.etree import ElementTree as ET
    
    async def get_sitemap_urls_async(url: str, session: aiohttp.ClientSession):
        """Async version of sitemap URL extraction"""
        try:
            async with session.get(url, timeout=10) as response:
                content = await response.read()
                
                # Parse the XML
                root = ET.fromstring(content)
                namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                urls = []
                seen_urls = set()
                
                for url_element in root.findall('.//ns:loc', namespace):
                    url_text = url_element.text.strip() if url_element.text else ""
                    if url_text and url_text not in seen_urls:
                        seen_urls.add(url_text)
                        urls.append(url_text)
                
                logger.info(f"Found {len(urls)} unique URLs in sitemap (deduplicated from {len(root.findall('.//ns:loc', namespace))} total)")
                return urls
        except Exception as e:
            logger.error(f"Error loading sitemap {url}: {str(e)}")
            # Fallback to synchronous method
            return get_sitemap_urls(url)
    
    async def create_document_async(url: str):
        """Async document creation (though this is fast, keeping pattern for consistency)"""
        return Document(
            page_content=url, 
            metadata={"source": url}
        )
    
    # Use aiohttp for async HTTP requests
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Get URLs from sitemap asynchronously
        sitemap_urls = await get_sitemap_urls_async(sitemap_url, session)
        
        # Create semaphore for controlled concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def create_doc_with_semaphore(url):
            async with semaphore:
                return await create_document_async(url)
        
        # Create all documents concurrently
        tasks = [create_doc_with_semaphore(url) for url in sitemap_urls]
        sitemap_docs = await asyncio.gather(*tasks)
        
        return sitemap_docs

@async_retry(retries=2, delay=1.0, max_delay=10.0)
async def extract_product_info_llm(page_content: str, openai_api_key: str) -> ProductInfo:
    """
    Extract product information using LLM with structured output and error handling.
    """
    try:
        if not page_content or not openai_api_key:
            raise ValidationError("Page content and OpenAI API key are required")
            
        logger.info("Extracting product information using LLM")
        from core.config import ModelConfig
        llm = ChatOpenAI(api_key=openai_api_key, model=ModelConfig.BRAND_PROFILING_MODEL, temperature=ModelConfig.DEFAULT_TEMPERATURE)
    
        prompt = f"""
        Analyze the following product page content and extract two pieces of information:
        
        1. Product Description: A brief 1-2 sentence description of what the product is and what it does
        2. Product Type: The category or type of product (e.g., 'sneakers', 'laptop', 'skincare cream', 'dress', 'headphones')
        
        Product Page Content:
        {page_content[:3000]}  # Limit content to avoid token limits
        
        Please provide a concise and accurate analysis.
        """
    
        async def _make_llm_request():
            return await llm.with_structured_output(ProductInfo).ainvoke(prompt)
        
        # Use rate limiting
        await wait_for_rate_limit("openai", tokens=1)
        result = await _make_llm_request()
        
        logger.info(f"Successfully extracted product info: {result.product_type}")
        return result
        
    except Exception as e:
        logger.warning(f"Failed to extract product info with LLM: {str(e)}")
        # Fallback if extraction fails
        return ProductInfo(
            product_description="Product description",
            product_type="product"
        )

@async_retry(retries=2, delay=1.0, max_delay=10.0)
async def load_single_product_document(product_url: str, openai_api_key: str, 
                                      product_description: Optional[str] = None, 
                                      product_type: Optional[str] = None) -> List[Document]:
    """Load a single product page and chunk it using markdown text splitter based on headers with error handling"""
    try:
        if not product_url or not openai_api_key:
            raise ValidationError("Product URL and OpenAI API key are required")
        
        logger.info(f"Loading product page: {product_url}")
        
        # Load page content with rate limiting
        async def _load_page():
            loader = WebBaseLoader(product_url)
            return loader.load()
        
        # Use rate limiting  
        await wait_for_rate_limit("web_scraping", tokens=1)
        docs = await _load_page()
        
        if not docs:
            raise ProcessingError(f"No content loaded from {product_url}", operation="page_loading")
    
    except Exception as e:
        if isinstance(e, (ValidationError, ProcessingError)):
            raise
        else:
            logger.error(f"Failed to load product page: {str(e)}")
            raise ProcessingError(f"Failed to load product page: {str(e)}", operation="page_loading")
    
    try:
        # Extract product information - use provided info or extract with LLM
        html_content = docs[0].page_content
        if product_description and product_type:
            product_info = ProductInfo(
                product_description=product_description,
                product_type=product_type
            )
            logger.info("Using provided product information")
        else:
            logger.info("Extracting product information using LLM")
            product_info = await extract_product_info_llm(html_content, openai_api_key)
        
        # Convert HTML to markdown for better structure recognition
        try:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            markdown_content = h.handle(html_content)
        except Exception as e:
            logger.warning(f"Failed to convert HTML to markdown: {e}")
            markdown_content = html_content
        
        # Define headers to split on (H1 through H6)
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"), 
            ("###", "Header 3"),
            ("####", "Header 4"),
            ("#####", "Header 5"),
            ("######", "Header 6"),
        ]
        
        # Initialize the markdown splitter
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        
        try:
            # Split the markdown content based on headers
            md_header_splits = markdown_splitter.split_text(markdown_content)
            
            # Convert back to Document objects with proper metadata
            chunked_docs = []
            for i, split in enumerate(md_header_splits):
                doc = Document(
                    page_content=split.page_content,
                    metadata={
                        "content_type": "chunked_content",
                        "document_type": "product",
                        "source": product_url,
                        "chunk_index": i,
                        "chunk_type": "markdown_header",
                        "product_description": product_info.product_description,
                        "product_type": product_info.product_type,
                        **split.metadata  # Include header metadata from the splitter
                    }
                )
                chunked_docs.append(doc)
            
            # If no splits were made (no headers found), return the original content as a single chunk
            if not chunked_docs:
                doc = Document(
                    page_content=markdown_content,
                    metadata={
                        "content_type": "full_content",
                        "document_type": "product", 
                        "source": product_url,
                        "chunk_index": 0,
                        "chunk_type": "full_document",
                        "product_description": product_info.product_description,
                        "product_type": product_info.product_type
                    }
                )
                chunked_docs = [doc]
            
            logger.info(f"Successfully processed product page into {len(chunked_docs)} chunks")
            return chunked_docs
        
        except Exception as e:
            logger.warning(f"Markdown splitting failed: {e}, using fallback")
            # Fallback to original content if markdown splitting fails
            doc = Document(
                page_content=html_content,
                metadata={
                    "content_type": "full_content",
                    "document_type": "product",
                    "source": product_url,
                    "chunk_index": 0,
                    "chunk_type": "fallback",
                    "split_error": str(e),
                    "product_description": product_info.product_description,
                    "product_type": product_info.product_type
                }
            )
            return [doc]
            
    except Exception as e:
        if isinstance(e, (ValidationError, ProcessingError)):
            raise
        else:
            logger.error(f"Unexpected error processing product page: {str(e)}")
            raise ProcessingError(
                f"Failed to process product page: {str(e)}",
                operation="product_page_processing"
            )

def get_sitemap_urls(url):
    response = requests.get(url)

    # Parse the XML
    root = ET.fromstring(response.content)

    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = []
    seen_urls = set()  # Track unique URLs

    for url_element in root.findall('.//ns:loc', namespace):
        url_text = url_element.text.strip() if url_element.text else ""
        if url_text and url_text not in seen_urls:
            seen_urls.add(url_text)
            urls.append(url_text)
    
    logger.info(f"Found {len(urls)} unique URLs in sitemap (deduplicated from {len(root.findall('.//ns:loc', namespace))} total)")
    return urls




