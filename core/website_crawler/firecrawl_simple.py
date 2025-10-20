"""
Simplified crawler using Firecrawl "crawl" mode
Much simpler than manual sitemap parsing + URL loading
"""
import os
import logging
from typing import List, Optional
from langchain.schema import Document

logger = logging.getLogger(__name__)


async def load_site_with_firecrawl(
    url: str,
    api_key: Optional[str] = None,
    max_pages: Optional[int] = None
) -> List[Document]:
    """
    Load entire site using Firecrawl's crawl mode

    Args:
        url: The URL to crawl (can be homepage or category page)
        api_key: Firecrawl API key (defaults to env var)
        max_pages: Maximum number of pages to crawl (None = unlimited)

    Returns:
        List of Document objects with page content and metadata

    Example:
        # Load entire Dior bags category
        docs = await load_site_with_firecrawl(
            "https://www.dior.com/en_ae/fashion/womens-fashion/bags"
        )

        print(f"Loaded {len(docs)} pages")
        print(f"First page: {docs[0].metadata['title']}")
    """
    try:
        from langchain_community.document_loaders.firecrawl import FireCrawlLoader
    except ImportError:
        raise ImportError(
            "firecrawl package not installed. Run: pip install firecrawl-py"
        )

    # Get API key
    if not api_key:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError(
                "Firecrawl API key required. Set FIRECRAWL_API_KEY env var or pass api_key parameter"
            )

    logger.info(f"🔥 Using Firecrawl to crawl: {url}")

    # Configure crawl parameters
    params = {
        "crawlerOptions": {
            "excludes": [],
            "includes": [],
            "limit": max_pages if max_pages else 1000,  # Default limit
        },
        "pageOptions": {
            "onlyMainContent": True,  # Extract only main content
            "includeHtml": False,  # Don't need raw HTML
            "includeLinks": False,  # Don't need link extraction
        }
    }

    try:
        # Create loader with crawl mode
        loader = FireCrawlLoader(
            api_key=api_key,
            url=url,
            mode="crawl",  # Key: use crawl mode not scrape
            params=params
        )

        logger.info("📡 Starting Firecrawl crawl...")
        documents = loader.load()

        logger.info(f"✅ Firecrawl loaded {len(documents)} pages")

        # Log sample of what we got
        if documents:
            first_doc = documents[0]
            logger.info(f"Sample page:")
            logger.info(f"  Title: {first_doc.metadata.get('title', 'N/A')}")
            logger.info(f"  URL: {first_doc.metadata.get('source_url', 'N/A')}")
            logger.info(f"  Content length: {len(first_doc.page_content)} chars")

        return documents

    except Exception as e:
        logger.error(f"❌ Firecrawl crawl failed: {type(e).__name__}: {str(e)}")
        raise


def load_site_with_firecrawl_sync(
    url: str,
    api_key: Optional[str] = None,
    max_pages: Optional[int] = None
) -> List[Document]:
    """
    Synchronous wrapper for load_site_with_firecrawl

    Example:
        docs = load_site_with_firecrawl_sync("https://www.dior.com/en_ae/fashion/womens-fashion/bags")
    """
    import asyncio
    return asyncio.run(load_site_with_firecrawl(url, api_key, max_pages))


async def load_specific_category_with_firecrawl(
    base_url: str,
    category_path: str,
    api_key: Optional[str] = None,
    max_pages: Optional[int] = 100
) -> List[Document]:
    """
    Load only a specific category using Firecrawl's includes filter

    Args:
        base_url: Base website URL (e.g., "https://www.dior.com")
        category_path: Category path to include (e.g., "/en_ae/fashion/womens-fashion/bags")
        api_key: Firecrawl API key
        max_pages: Maximum pages to crawl

    Returns:
        List of documents from that category only

    Example:
        # Only load bags category
        docs = await load_specific_category_with_firecrawl(
            "https://www.dior.com",
            "/en_ae/fashion/womens-fashion/bags",
            max_pages=50
        )
    """
    try:
        from langchain_community.document_loaders.firecrawl import FireCrawlLoader
    except ImportError:
        raise ImportError("firecrawl package not installed. Run: pip install firecrawl-py")

    if not api_key:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("Firecrawl API key required")

    # Start URL is the category page
    start_url = f"{base_url.rstrip('/')}{category_path}"

    logger.info(f"🔥 Crawling specific category: {start_url}")

    # Configure to only include URLs matching the category path
    params = {
        "crawlerOptions": {
            "includes": [f"{category_path}*"],  # Only URLs starting with this path
            "excludes": [],
            "limit": max_pages,
        },
        "pageOptions": {
            "onlyMainContent": True,
            "includeHtml": False,
        }
    }

    try:
        loader = FireCrawlLoader(
            api_key=api_key,
            url=start_url,
            mode="crawl",
            params=params
        )

        logger.info(f"📡 Crawling category with filter: {category_path}*")
        documents = loader.load()

        logger.info(f"✅ Loaded {len(documents)} pages from category")
        return documents

    except Exception as e:
        logger.error(f"❌ Category crawl failed: {str(e)}")
        raise


# Convenience function for quick testing
def quick_crawl(url: str, max_pages: int = 50) -> List[Document]:
    """
    Quick helper to crawl a URL

    Example:
        docs = quick_crawl("https://www.dior.com/en_ae/fashion/womens-fashion/bags", max_pages=20)
        print(f"Loaded {len(docs)} pages")
    """
    return load_site_with_firecrawl_sync(url, max_pages=max_pages)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 10

        print(f"🔥 Crawling: {test_url}")
        print(f"Max pages: {max_pages}\n")

        docs = quick_crawl(test_url, max_pages=max_pages)

        print(f"\n✅ Loaded {len(docs)} pages:\n")
        for i, doc in enumerate(docs[:5], 1):
            title = doc.metadata.get('title', 'No title')
            url = doc.metadata.get('source_url', doc.metadata.get('url', 'N/A'))
            content_len = len(doc.page_content)
            print(f"{i}. {title}")
            print(f"   URL: {url}")
            print(f"   Content: {content_len} chars\n")

        if len(docs) > 5:
            print(f"... and {len(docs) - 5} more pages")
    else:
        print("Usage: python firecrawl_simple.py <url> [max_pages]")
        print("\nExamples:")
        print("  python firecrawl_simple.py https://www.dior.com/en_ae/fashion/womens-fashion/bags 20")
        print("  python firecrawl_simple.py https://example.com 50")
