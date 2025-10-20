"""
Simple URL Extractor - Extract all URLs from any given URL (XML sitemap or HTML page)
"""
import aiohttp
import asyncio
from typing import List, Set
from xml.etree import ElementTree as ET
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


async def extract_urls_from_page(url: str, same_domain_only: bool = True) -> List[str]:
    """
    Extract all URLs from a given URL (works with both XML sitemaps and HTML pages)

    Args:
        url: The URL to extract links from (can be sitemap.xml or regular HTML page)
        same_domain_only: If True, only return URLs from the same domain

    Returns:
        List of unique URLs found

    Examples:
        # From XML sitemap
        urls = await extract_urls_from_page("https://example.com/sitemap.xml")

        # From HTML page
        urls = await extract_urls_from_page("https://example.com/products")

        # Get all URLs (including external)
        urls = await extract_urls_from_page("https://example.com", same_domain_only=False)
    """

    # Determine if it's XML or HTML
    is_xml = url.endswith('.xml') or url.endswith('.xml.gz') or 'sitemap' in url.lower()

    if is_xml:
        return await _extract_urls_from_xml(url)
    else:
        return await _extract_urls_from_html(url, same_domain_only)


async def _extract_urls_from_xml(sitemap_url: str) -> List[str]:
    """
    Extract URLs from XML sitemap (handles sitemap indexes recursively)
    """
    urls = []
    seen_urls: Set[str] = set()

    async def _parse_sitemap(url: str, session: aiohttp.ClientSession):
        """Recursively parse sitemap and sub-sitemaps"""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; URLExtractor/1.0)',
                'Accept': 'application/xml,text/xml,*/*'
            }

            async with session.get(url, timeout=timeout, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                    return

                content = await response.read()

                # Parse XML
                root = ET.fromstring(content)
                namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

                # Check if it's a sitemap index (contains <sitemap> tags)
                sitemap_elements = root.findall('.//ns:sitemap/ns:loc', namespace)

                if sitemap_elements:
                    # It's a sitemap index - recursively fetch sub-sitemaps
                    logger.info(f"📑 Found sitemap index with {len(sitemap_elements)} sub-sitemaps")
                    for sitemap_loc in sitemap_elements:
                        sub_sitemap_url = sitemap_loc.text.strip() if sitemap_loc.text else ""
                        if sub_sitemap_url:
                            await _parse_sitemap(sub_sitemap_url, session)
                else:
                    # Regular sitemap - extract <loc> tags
                    for url_element in root.findall('.//ns:loc', namespace):
                        url_text = url_element.text.strip() if url_element.text else ""
                        if url_text and url_text not in seen_urls:
                            seen_urls.add(url_text)
                            urls.append(url_text)

        except ET.ParseError as e:
            logger.error(f"XML parsing error for {url}: {e}")
        except Exception as e:
            logger.error(f"Error fetching sitemap {url}: {e}")

    # Fetch and parse sitemap
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        await _parse_sitemap(sitemap_url, session)

    logger.info(f"✅ Extracted {len(urls)} URLs from XML sitemap")
    return urls


async def _extract_urls_from_html(page_url: str, same_domain_only: bool = True) -> List[str]:
    """
    Extract URLs from HTML page by parsing <a href="..."> tags
    """
    urls: Set[str] = set()

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(page_url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {page_url}: HTTP {response.status}")
                    return []

                html = await response.text()

                # Parse HTML
                soup = BeautifulSoup(html, 'html.parser')

                # Get base domain for filtering
                base_domain = urlparse(page_url).netloc

                # Extract all <a> tags
                for link in soup.find_all('a', href=True):
                    href = link['href']

                    # Convert relative URLs to absolute
                    absolute_url = urljoin(page_url, href)

                    # Parse URL
                    parsed_url = urlparse(absolute_url)

                    # Filter by domain if requested
                    if same_domain_only and parsed_url.netloc != base_domain:
                        continue

                    # Clean URL (remove fragments)
                    clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                    if parsed_url.query:
                        clean_url += f"?{parsed_url.query}"

                    # Skip empty paths or just domain
                    if parsed_url.path and parsed_url.path != '/':
                        urls.add(clean_url)

                logger.info(f"✅ Extracted {len(urls)} URLs from HTML page")
                return sorted(list(urls))

    except Exception as e:
        logger.error(f"Error extracting URLs from HTML {page_url}: {e}")
        return []


def extract_urls_from_page_sync(url: str, same_domain_only: bool = True) -> List[str]:
    """
    Synchronous wrapper for extract_urls_from_page (for use in Jupyter notebooks)

    Args:
        url: The URL to extract links from
        same_domain_only: If True, only return URLs from the same domain

    Returns:
        List of unique URLs found

    Example:
        urls = extract_urls_from_page_sync("https://example.com/sitemap.xml")
        print(f"Found {len(urls)} URLs")
        for url in urls[:10]:
            print(url)
    """
    return asyncio.run(extract_urls_from_page(url, same_domain_only))


# Convenience function for quick testing
def get_urls(url: str) -> List[str]:
    """
    Quick helper: Extract URLs from any page (sitemap or HTML)

    Example:
        urls = get_urls("https://example.com/sitemap.xml")
    """
    return extract_urls_from_page_sync(url, same_domain_only=True)


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        print(f"🔍 Extracting URLs from: {test_url}\n")

        urls = get_urls(test_url)

        print(f"✅ Found {len(urls)} URLs:\n")
        for i, url in enumerate(urls[:20], 1):
            print(f"{i}. {url}")

        if len(urls) > 20:
            print(f"\n... and {len(urls) - 20} more URLs")
    else:
        print("Usage: python url_extractor.py <url>")
        print("\nExamples:")
        print("  python url_extractor.py https://example.com/sitemap.xml")
        print("  python url_extractor.py https://example.com/products")
