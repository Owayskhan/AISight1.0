
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

# ============================================
# Crawl4AI-based sitemap discovery (Primary Method)
# ============================================

async def get_sitemap_urls_crawl4ai(website_url: str) -> List[str]:
    """
    Use Crawl4AI to discover all URLs on a website.
    This is the primary method for sitemap discovery.

    Args:
        website_url: Base website URL to crawl

    Returns:
        List of discovered URLs

    Raises:
        ImportError: If crawl4ai is not installed
        Exception: If crawling fails
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse

        logger.info(f"🕷️ Using Crawl4AI to discover URLs for: {website_url}")

        # Initialize the crawler
        crawler = AsyncWebCrawler()

        # Configure the crawler
        config = CrawlerRunConfig()

        logger.info("📡 Calling Crawl4AI to fetch page...")

        # Crawl the website
        result = await crawler.arun(url=website_url, config=config)

        # Extract URLs from the HTML content
        sitemap_urls = set()  # Use set to avoid duplicates

        # Get the first result (crawl4ai returns a container)
        if result and len(result) > 0:
            crawl_result = result[0]

            # Parse HTML to extract all links
            if hasattr(crawl_result, 'html') and crawl_result.html:
                soup = BeautifulSoup(crawl_result.html, 'html.parser')

                # Extract all anchor tags
                for link in soup.find_all('a', href=True):
                    href = link['href']

                    # Convert relative URLs to absolute
                    absolute_url = urljoin(website_url, href)

                    # Only include URLs from the same domain
                    parsed_base = urlparse(website_url)
                    parsed_url = urlparse(absolute_url)

                    if parsed_url.netloc == parsed_base.netloc:
                        # Clean the URL (remove fragments)
                        clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                        if parsed_url.query:
                            clean_url += f"?{parsed_url.query}"

                        sitemap_urls.add(clean_url)

                logger.info(f"✅ Crawl4AI discovered {len(sitemap_urls)} unique URLs from HTML")
            else:
                logger.warning("⚠️ No HTML content found in crawl result")
        else:
            logger.error("❌ Crawl4AI returned no results")
            raise Exception("Crawl4AI returned empty result")

        # Convert set to sorted list
        sitemap_urls_list = sorted(list(sitemap_urls))

        logger.info(f"✅ Total unique URLs discovered: {len(sitemap_urls_list)}")

        # Close the crawler
        await crawler.close()

        return sitemap_urls_list

    except ImportError as e:
        logger.error(f"❌ Crawl4AI package not installed: {e}")
        raise ValueError("crawl4ai package is required but not installed. Run: pip install crawl4ai")
    except Exception as e:
        logger.error(f"❌ Crawl4AI discovery failed: {type(e).__name__}: {str(e)}")
        raise


# ============================================
# Firecrawl-based sitemap discovery (Deprecated - kept for fallback)
# ============================================

async def get_sitemap_urls_firecrawl(website_url: str) -> List[str]:
    """
    Use Firecrawl API to discover all URLs on a website.
    This is the primary method for sitemap discovery.

    Args:
        website_url: Base website URL to crawl

    Returns:
        List of discovered URLs

    Raises:
        ValueError: If FIRECRAWL_API_KEY is not set
        Exception: If Firecrawl API call fails
    """
    try:
        from firecrawl import FirecrawlApp
        import os
        from core.config import FirecrawlConfig

        logger.info(f"🔥 Using Firecrawl to discover URLs for: {website_url}")

        # Get API key from environment
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY not found in environment variables")

        # Initialize Firecrawl app
        app = FirecrawlApp(api_key=api_key)

        # Use map() to discover all URLs on the website
        logger.info("📡 Calling Firecrawl map() API...")
        result = app.map(website_url)

        # Extract URLs from result
        sitemap_urls = []
        if hasattr(result, 'links'):
            for link in result.links:
                if hasattr(link, 'url'):
                    sitemap_urls.append(link.url)
                else:
                    sitemap_urls.append(str(link))
        else:
            # Fallback: try to parse result as list
            sitemap_urls = [str(url) for url in result] if isinstance(result, list) else []

        logger.info(f"✅ Firecrawl discovered {len(sitemap_urls)} URLs")

        return sitemap_urls

    except ImportError as e:
        logger.error(f"❌ Firecrawl package not installed: {e}")
        raise ValueError("firecrawl-py package is required but not installed. Run: pip install firecrawl-py")
    except Exception as e:
        logger.error(f"❌ Firecrawl discovery failed: {type(e).__name__}: {str(e)}")
        raise


# ============================================
# Legacy sitemap discovery functions (Fallback)
# ============================================

@async_retry(retries=2, delay=1.0, max_delay=10.0)
async def _find_sitemap_url_async_legacy(website_url: str) -> str:
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


async def find_sitemap_url_async(website_url: str) -> str:
    """
    Find sitemap URL with Crawl4AI as primary method, Firecrawl as secondary, legacy as final fallback.
    This is the main entry point for sitemap discovery.
    """
    from core.config import Crawl4AIConfig, FirecrawlConfig

    # Try Crawl4AI first if enabled
    if Crawl4AIConfig.ENABLED:
        try:
            urls = await get_sitemap_urls_crawl4ai(website_url)
            if urls:
                logger.info(f"✅ Crawl4AI found {len(urls)} URLs, returning base URL as signal")
                # For compatibility with existing code expecting a sitemap URL,
                # we return the base website URL since Crawl4AI already gave us all URLs
                return website_url  # Signal that we used Crawl4AI successfully
        except Exception as e:
            logger.warning(f"⚠️ Crawl4AI failed ({type(e).__name__}), trying Firecrawl...")

    # Try Firecrawl as secondary method if enabled
    if FirecrawlConfig.ENABLED:
        try:
            urls = await get_sitemap_urls_firecrawl(website_url)
            if urls:
                logger.info(f"✅ Firecrawl found {len(urls)} URLs, returning base URL as signal")
                return website_url  # Signal that we used Firecrawl successfully
        except Exception as e:
            logger.warning(f"⚠️ Firecrawl failed ({type(e).__name__}), falling back to legacy sitemap discovery")

    # Fallback to legacy method
    logger.info("📋 Using legacy sitemap discovery...")
    return await _find_sitemap_url_async_legacy(website_url)


def find_sitemap_url(website_url: str) -> str:
    """
    Synchronous wrapper for find_sitemap_url_async.
    Dynamically find the sitemap URL for a given website.
    """
    return asyncio.run(find_sitemap_url_async(website_url))


def _find_sitemap_url_legacy(website_url: str) -> str:
    """
    LEGACY: Synchronous sitemap discovery (fallback only).
    """
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

async def load_sitemap_documents(website_url: str):
    """
    Load sitemap documents sequentially.
    Uses Crawl4AI for URL discovery, then LangChain WebBaseLoader for content extraction.

    Args:
        website_url: Base website URL or sitemap URL

    Returns:
        List of Document objects with actual page content
    """
    from core.config import Crawl4AIConfig, FirecrawlConfig

    # Try Crawl4AI first if enabled
    if Crawl4AIConfig.ENABLED:
        try:
            sitemap = await get_sitemap_urls_crawl4ai(website_url)
            logger.info(f"✅ Crawl4AI: Downloading content for {len(sitemap)} URLs using WebBaseLoader...")

            sitemap_docs = []
            for idx, url in enumerate(sitemap):
                logger.info(f"📥 Downloading {idx + 1}/{len(sitemap)}: {url}")

                try:
                    # Use LangChain's WebBaseLoader for content extraction
                    # WebBaseLoader.load() is synchronous, so run it in executor
                    loop = asyncio.get_event_loop()
                    loader = WebBaseLoader(url)
                    documents = await loop.run_in_executor(None, loader.load)

                    if documents and len(documents) > 0:
                        content = documents[0].page_content

                        # Validation: Ensure content is meaningful
                        if content and len(content.strip()) > 100:
                            doc = Document(
                                page_content=content,  # ✅ Actual page content!
                                metadata={
                                    "source": url,
                                    "method": "webbaseloader",
                                    "content_type": "extracted_content"
                                }
                            )
                        else:
                            logger.warning(f"⚠️ Content too short from {url} ({len(content.strip()) if content else 0} chars)")
                            doc = Document(
                                page_content=url,
                                metadata={
                                    "source": url,
                                    "method": "webbaseloader",
                                    "content_type": "url_only",
                                    "extraction_failed": True,
                                    "reason": "content_too_short"
                                }
                            )
                    else:
                        # Fallback: store URL if content extraction failed
                        logger.warning(f"⚠️ No content extracted from {url}, storing URL only")
                        doc = Document(
                            page_content=url,
                            metadata={
                                "source": url,
                                "method": "webbaseloader",
                                "content_type": "url_only",
                                "extraction_failed": True
                            }
                        )
                except Exception as e:
                    logger.warning(f"⚠️ Failed to download {url}: {str(e)[:100]}")
                    doc = Document(
                        page_content=url,
                        metadata={
                            "source": url,
                            "method": "webbaseloader",
                            "content_type": "url_only",
                            "error": str(e)[:200]
                        }
                    )

                sitemap_docs.append(doc)

            # Log statistics
            successful = sum(1 for doc in sitemap_docs if doc.metadata.get("content_type") == "extracted_content")
            failed = len(sitemap_docs) - successful

            logger.info(f"✅ Content loading complete:")
            logger.info(f"   - {successful} URLs with content extracted")
            logger.info(f"   - {failed} URLs failed (stored as URL only)")

            return sitemap_docs

        except Exception as e:
            logger.warning(f"⚠️ Crawl4AI + WebBaseLoader failed, trying Firecrawl: {e}")

    # Try Firecrawl as secondary method if enabled
    if FirecrawlConfig.ENABLED:
        try:
            sitemap = await get_sitemap_urls_firecrawl(website_url)
            logger.info(f"✅ Firecrawl: Creating {len(sitemap)} documents")

            sitemap_docs = []
            for url in sitemap:
                doc = Document(
                    page_content=url, metadata={"source": url, "method": "firecrawl"}
                )
                sitemap_docs.append(doc)

            return sitemap_docs

        except Exception as e:
            logger.warning(f"⚠️ Firecrawl failed, falling back to legacy XML sitemap parsing: {e}")

    # Fallback to legacy method
    logger.info("📋 Using legacy XML sitemap parsing...")
    sitemap = _get_sitemap_urls_legacy(website_url)

    sitemap_docs = []
    for url in sitemap:
        doc = Document(
            page_content=url, metadata={"source": url, "method": "legacy"}
        )
        sitemap_docs.append(doc)

    return sitemap_docs

async def load_url_content_crawl4ai(url: str) -> str:
    """
    Use Crawl4AI to download and extract the content from a single URL.

    Args:
        url: URL to download

    Returns:
        Extracted text content from the page
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

        crawler = AsyncWebCrawler()
        config = CrawlerRunConfig()

        # Crawl the URL
        result = await crawler.arun(url=url, config=config)

        # Extract content
        if result and len(result) > 0:
            crawl_result = result[0]

            # Use markdown content if available, otherwise use extracted_content
            if hasattr(crawl_result, 'markdown') and crawl_result.markdown:
                content = crawl_result.markdown
            elif hasattr(crawl_result, 'extracted_content') and crawl_result.extracted_content:
                content = crawl_result.extracted_content
            elif hasattr(crawl_result, 'html') and crawl_result.html:
                # Fallback: extract text from HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(crawl_result.html, 'html.parser')
                content = soup.get_text(separator='\n', strip=True)
            else:
                content = ""

            await crawler.close()
            return content
        else:
            await crawler.close()
            return ""

    except Exception as e:
        logger.warning(f"⚠️ Crawl4AI failed to load content from {url}: {str(e)[:100]}")
        return ""


async def load_sitemap_documents_parallel(website_url: str, max_concurrent: int = 50):
    """
    Load sitemap documents with parallel processing.
    Uses Crawl4AI for URL discovery, then LangChain WebBaseLoader for content extraction.

    Args:
        website_url: Base website URL or sitemap URL
        max_concurrent: Maximum concurrent URL processing

    Returns:
        List of Document objects with actual page content
    """
    from core.config import Crawl4AIConfig, FirecrawlConfig

    # Try Crawl4AI first if enabled
    if Crawl4AIConfig.ENABLED:
        try:
            logger.info(f"🕷️ Using Crawl4AI for URL discovery...")
            sitemap_urls = await get_sitemap_urls_crawl4ai(website_url)

            logger.info(f"📥 Downloading content for {len(sitemap_urls)} URLs using WebBaseLoader...")

            # Create semaphore for controlled concurrency
            semaphore = asyncio.Semaphore(max_concurrent)

            async def download_url_content(url: str) -> Document:
                """Download content for a single URL using WebBaseLoader with semaphore control"""
                async with semaphore:
                    try:
                        # Use LangChain's WebBaseLoader for reliable content extraction
                        # WebBaseLoader.load() is synchronous, so run it in executor
                        loop = asyncio.get_event_loop()
                        loader = WebBaseLoader(url)
                        documents = await loop.run_in_executor(None, loader.load)

                        if documents and len(documents) > 0:
                            # Return the document with actual content
                            content = documents[0].page_content

                            # Validation: Ensure content is meaningful (not just empty or the URL itself)
                            if content and len(content.strip()) > 100:
                                return Document(
                                    page_content=content,  # ✅ Actual page content!
                                    metadata={
                                        "source": url,
                                        "method": "webbaseloader",
                                        "content_type": "extracted_content"
                                    }
                                )
                            else:
                                logger.warning(f"⚠️ Content too short from {url} ({len(content.strip()) if content else 0} chars), storing URL only")
                                return Document(
                                    page_content=url,
                                    metadata={
                                        "source": url,
                                        "method": "webbaseloader",
                                        "content_type": "url_only",
                                        "extraction_failed": True,
                                        "reason": "content_too_short"
                                    }
                                )
                        else:
                            # Fallback: store URL if content extraction failed
                            logger.warning(f"⚠️ No content extracted from {url}, storing URL only")
                            return Document(
                                page_content=url,
                                metadata={
                                    "source": url,
                                    "method": "webbaseloader",
                                    "content_type": "url_only",
                                    "extraction_failed": True
                                }
                            )
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to download {url}: {str(e)[:100]}")
                        # Return URL as fallback
                        return Document(
                            page_content=url,
                            metadata={
                                "source": url,
                                "method": "webbaseloader",
                                "content_type": "url_only",
                                "error": str(e)[:200]
                            }
                        )

            # Download all URLs in parallel with controlled concurrency
            tasks = [download_url_content(url) for url in sitemap_urls]
            sitemap_docs = await asyncio.gather(*tasks)

            # Log statistics
            successful = sum(1 for doc in sitemap_docs if not doc.metadata.get("extraction_failed") and doc.metadata.get("content_type") == "extracted_content")
            failed = len(sitemap_docs) - successful

            logger.info(f"✅ Content loading complete:")
            logger.info(f"   - {successful} URLs with content extracted")
            logger.info(f"   - {failed} URLs failed (stored as URL only)")
            logger.info(f"   - Total: {len(sitemap_docs)} documents created")

            return sitemap_docs

        except Exception as e:
            logger.warning(f"⚠️ Crawl4AI + WebBaseLoader failed, trying Firecrawl: {e}")

    # Try Firecrawl as secondary method if enabled
    if FirecrawlConfig.ENABLED:
        try:
            logger.info(f"🔥 Using Firecrawl for parallel document loading...")
            sitemap_urls = await get_sitemap_urls_firecrawl(website_url)

            sitemap_docs = []
            for url in sitemap_urls:
                doc = Document(
                    page_content=url,
                    metadata={"source": url, "method": "firecrawl"}
                )
                sitemap_docs.append(doc)

            logger.info(f"✅ Firecrawl parallel loading: {len(sitemap_docs)} documents created")
            return sitemap_docs

        except Exception as e:
            logger.warning(f"⚠️ Firecrawl failed, falling back to legacy parallel XML parsing: {e}")

    # Fallback to legacy parallel method
    logger.info("📋 Using legacy parallel XML sitemap parsing...")
    # Note: asyncio and aiohttp already imported at module level
    from xml.etree import ElementTree as ET

    async def _get_sitemap_urls_async_legacy(url: str, session: aiohttp.ClientSession):
        """LEGACY: Async version of sitemap URL extraction"""
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
            return _get_sitemap_urls_legacy(url)
    
    async def create_document_async(url: str):
        """Async document creation (though this is fast, keeping pattern for consistency)"""
        return Document(
            page_content=url, 
            metadata={"source": url}
        )
    
    # Use aiohttp for async HTTP requests
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Get URLs from sitemap asynchronously (legacy method)
        sitemap_urls = await _get_sitemap_urls_async_legacy(website_url, session)
        
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

def _get_sitemap_urls_legacy(url):
    """
    LEGACY: Parse sitemap XML to extract URLs (synchronous fallback method).
    Only used when Firecrawl fails or is disabled.
    """
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


# Maintain backward compatibility
get_sitemap_urls = _get_sitemap_urls_legacy  # Alias for legacy code




