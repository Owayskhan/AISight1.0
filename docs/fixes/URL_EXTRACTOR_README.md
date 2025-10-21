# Simple URL Extractor

Extract all URLs from any given URL (works with XML sitemaps and HTML pages)

## Quick Start

### 1. Simple Usage (One-liner)

```python
from core.website_crawler.url_extractor import get_urls

# Extract URLs from any page
urls = get_urls("https://www.dior.com/sitemap.xml")
print(f"Found {len(urls)} URLs")
```

### 2. Command Line

```bash
python core/website_crawler/url_extractor.py https://www.dior.com/sitemap.xml
```

### 3. Jupyter Notebook

Open [url_extraction_example.ipynb](url_extraction_example.ipynb) for interactive examples.

---

## API Reference

### `get_urls(url: str) -> List[str]`

**Quick helper to extract URLs from any page**

```python
urls = get_urls("https://example.com/sitemap.xml")
```

- Automatically detects XML sitemaps vs HTML pages
- Returns only same-domain URLs
- Handles sitemap indexes (recursive)

---

### `extract_urls_from_page_sync(url: str, same_domain_only: bool = True) -> List[str]`

**Full-featured URL extraction with options**

```python
# Get all URLs (including external)
all_urls = extract_urls_from_page_sync(
    "https://example.com",
    same_domain_only=False
)
```

**Parameters:**
- `url`: The URL to extract links from
- `same_domain_only`: If True, only return URLs from same domain (default: True)

---

### `async extract_urls_from_page(url: str, same_domain_only: bool = True) -> List[str]`

**Async version for use in async code**

```python
import asyncio

async def main():
    urls = await extract_urls_from_page("https://example.com")
    print(urls)

asyncio.run(main())
```

---

## Examples

### Extract from XML Sitemap

```python
from core.website_crawler.url_extractor import get_urls

# Automatically detects and parses XML
urls = get_urls("https://www.dior.com/sitemap.xml")
print(f"Found {len(urls)} product URLs")
```

### Extract from HTML Page

```python
# Works with any HTML page
urls = get_urls("https://www.dior.com/en_ae/fashion/womens-fashion/bags")
print(f"Found {len(urls)} links on page")
```

### Filter Results

```python
all_urls = get_urls("https://www.dior.com/sitemap.xml")

# Filter for specific patterns
bag_urls = [url for url in all_urls if '/bags/' in url]
product_urls = [url for url in all_urls if '/product/' in url]

print(f"Bag URLs: {len(bag_urls)}")
print(f"Product URLs: {len(product_urls)}")
```

### Include External Links

```python
from core.website_crawler.url_extractor import extract_urls_from_page_sync

# Get all links including external
all_links = extract_urls_from_page_sync(
    "https://example.com",
    same_domain_only=False
)

# Separate internal vs external
internal = [url for url in all_links if 'example.com' in url]
external = [url for url in all_links if 'example.com' not in url]
```

---

## How It Works

### XML Sitemaps
- Detects URLs ending with `.xml`, `.xml.gz`, or containing `sitemap`
- Parses XML and extracts all `<loc>` tags
- Handles sitemap indexes (recursively fetches sub-sitemaps)
- Works with: `sitemap.xml`, `sitemap_index.xml`, `product-sitemap.xml`, etc.

### HTML Pages
- Parses HTML and extracts all `<a href="...">` tags
- Converts relative URLs to absolute URLs
- Filters by domain (optional)
- Removes fragments and duplicates

---

## Integration with Your API

The URL extractor is now automatically used in your API when processing sitemaps:

```python
# In your API, this now works correctly with Dior:
POST /analyze
{
  "brand_name": "Dior",
  "brand_url": "https://www.dior.com/en_ae/fashion/womens-fashion/bags/all-the-bags",
  ...
}
```

**What happens:**
1. API discovers sitemap: `https://www.dior.com/sitemap.xml`
2. Detects it's XML ✅
3. Parses XML and extracts all URLs ✅
4. Continues with normal processing ✅

**No more "0 URLs discovered" errors!**

---

## Testing

Run the test script:

```bash
python test_xml_sitemap.py
```

Or test manually:

```bash
# Test with Dior sitemap
python core/website_crawler/url_extractor.py https://www.dior.com/sitemap.xml

# Test with any URL
python core/website_crawler/url_extractor.py YOUR_URL_HERE
```

---

## Troubleshooting

### No URLs Found
- Check if the URL is accessible (try in browser)
- For XML sitemaps, verify it's valid XML
- Check logs for parsing errors

### Only Getting Few URLs
- If using `same_domain_only=True`, it filters external links
- Set `same_domain_only=False` to get all links

### Timeout Errors
- Some sites may block automated requests
- Try with different User-Agent headers
- Check if site requires authentication

---

## Summary

**Three ways to extract URLs:**

1. **Quick**: `get_urls("https://example.com")`
2. **With options**: `extract_urls_from_page_sync(url, same_domain_only=False)`
3. **Async**: `await extract_urls_from_page(url)`

Works with:
- ✅ XML sitemaps (`sitemap.xml`)
- ✅ Sitemap indexes (recursive)
- ✅ HTML pages (any URL)
- ✅ Both same-domain and external links
