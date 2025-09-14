from langchain_community.document_loaders import WebBaseLoader
import requests
from xml.etree import ElementTree as ET
from langchain.schema import Document
from urllib.parse import urljoin, urlparse
from typing import List, Optional
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

def find_sitemap_url(website_url: str) -> str:
    """
    Dynamically find the sitemap URL for a given website.
    Tries common sitemap locations in order.
    """
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
        '/robots.txt'  # Check robots.txt for sitemap reference
    ]
    
    for path in sitemap_paths:
        sitemap_url = urljoin(website_url, path)
        try:
            response = requests.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                # Check if it's robots.txt
                if path == '/robots.txt':
                    # Parse robots.txt for sitemap URL
                    for line in response.text.splitlines():
                        if line.lower().startswith('sitemap:'):
                            return line.split(':', 1)[1].strip()
                else:
                    # Check if it's valid XML
                    try:
                        ET.fromstring(response.content)
                        return sitemap_url
                    except ET.ParseError:
                        continue
        except Exception:
            continue
    
    # If no sitemap found, raise exception
    raise ValueError(f"Could not find sitemap for {website_url}")

def load_sitemap_documents(sitemap_url: str, load_content: bool = False, max_pages: Optional[int] = None) -> List[Document]:
    """
    Load documents from sitemap URLs.
    
    Args:
        sitemap_url: URL of the sitemap
        load_content: If True, loads full page content. If False, just stores URLs (default behavior)
        max_pages: Maximum number of pages to load (useful for testing)
    
    Returns:
        List of Document objects
    """
    sitemap_urls = get_sitemap_urls(sitemap_url)
    
    if max_pages:
        sitemap_urls = sitemap_urls[:max_pages]
    
    if load_content:
        return load_sitemap_documents_with_content(sitemap_urls)
    else:
        # Original behavior - just store URLs
        sitemap_docs = []
        for url in sitemap_urls:
            doc = Document(
                page_content=url, 
                metadata={"source": url, "content_type": "url"}
            )
            sitemap_docs.append(doc)
        return sitemap_docs

def load_sitemap_documents_with_content(urls: List[str]) -> List[Document]:
    """
    Load full content from URLs using WebBaseLoader.
    
    Args:
        urls: List of URLs to load
    
    Returns:
        List of Document objects with full content
    """
    sitemap_docs = []
    
    # Process URLs in batches to avoid overwhelming the server
    batch_size = 10
    for i in range(0, len(urls), batch_size):
        batch_urls = urls[i:i + batch_size]
        
        try:
            # Use WebBaseLoader to load multiple URLs at once
            loader = WebBaseLoader(batch_urls)
            docs = loader.load()
            
            # Update metadata to indicate content is loaded
            for doc in docs:
                doc.metadata["content_type"] = "full_content"
            
            sitemap_docs.extend(docs)
            
            logger.info(f"Loaded {len(docs)} pages from batch {i//batch_size + 1}")
            
        except Exception as e:
            logger.error(f"Error loading batch {i//batch_size + 1}: {str(e)}")
            # Fall back to URL-only documents for failed pages
            for url in batch_urls:
                doc = Document(
                    page_content=url,
                    metadata={"source": url, "content_type": "url", "error": str(e)}
                )
                sitemap_docs.append(doc)
    
    return sitemap_docs

async def load_sitemap_documents_async(sitemap_url: str, load_content: bool = False, max_pages: Optional[int] = None) -> List[Document]:
    """
    Asynchronously load documents from sitemap URLs.
    
    Args:
        sitemap_url: URL of the sitemap
        load_content: If True, loads full page content. If False, just stores URLs
        max_pages: Maximum number of pages to load
    
    Returns:
        List of Document objects
    """
    sitemap_urls = get_sitemap_urls(sitemap_url)
    
    if max_pages:
        sitemap_urls = sitemap_urls[:max_pages]
    
    if load_content:
        return await load_sitemap_documents_with_content_async(sitemap_urls)
    else:
        # Original behavior - just store URLs
        sitemap_docs = []
        for url in sitemap_urls:
            doc = Document(
                page_content=url, 
                metadata={"source": url, "content_type": "url"}
            )
            sitemap_docs.append(doc)
        return sitemap_docs

async def load_sitemap_documents_with_content_async(urls: List[str]) -> List[Document]:
    """
    Asynchronously load full content from URLs.
    
    Args:
        urls: List of URLs to load
    
    Returns:
        List of Document objects with full content
    """
    sitemap_docs = []
    
    async with aiohttp.ClientSession() as session:
        # Process URLs in batches
        batch_size = 10
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            
            tasks = []
            for url in batch_urls:
                tasks.append(fetch_url_content(session, url))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, result in zip(batch_urls, results):
                if isinstance(result, Exception):
                    # Create URL-only document for failed pages
                    doc = Document(
                        page_content=url,
                        metadata={"source": url, "content_type": "url", "error": str(result)}
                    )
                else:
                    # Create document with full content
                    doc = Document(
                        page_content=result,
                        metadata={"source": url, "content_type": "full_content"}
                    )
                sitemap_docs.append(doc)
            
            logger.info(f"Loaded batch {i//batch_size + 1} of {(len(urls) + batch_size - 1) // batch_size}")
    
    return sitemap_docs

async def fetch_url_content(session: aiohttp.ClientSession, url: str) -> str:
    """
    Fetch content from a single URL.
    
    Args:
        session: aiohttp client session
        url: URL to fetch
    
    Returns:
        Page content as string
    """
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            return await response.text()
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        raise

def get_sitemap_urls(url: str) -> List[str]:
    """
    Extract URLs from a sitemap.
    
    Args:
        url: Sitemap URL
    
    Returns:
        List of URLs found in the sitemap
    """
    response = requests.get(url)

    # Parse the XML
    root = ET.fromstring(response.content)

    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = []

    for url_element in root.findall('.//ns:loc', namespace):
        urls.append(url_element.text)
    
    return urls

def is_document_preloaded(doc: Document) -> bool:
    """
    Check if a document contains pre-loaded content or just a URL.
    
    Args:
        doc: Document to check
    
    Returns:
        True if document contains full content, False if it's just a URL
    """
    # Check metadata first
    if doc.metadata.get("content_type") == "full_content":
        return True
    
    # Fallback: check if page_content looks like a URL
    content = doc.page_content.strip()
    if content.startswith(("http://", "https://")) and " " not in content and len(content) < 200:
        return False
    
    return True