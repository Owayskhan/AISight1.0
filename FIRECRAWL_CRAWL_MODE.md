# Firecrawl Crawl Mode - Simplified Site Indexing

## Why Use Firecrawl Crawl Mode?

**Old approach** (complex):
```
1. Find sitemap URL → 2. Parse XML → 3. Extract URLs → 4. Load each URL → 5. Extract content → 6. Index
```

**New approach** (simple):
```
1. Firecrawl crawl → 2. Index
```

---

## Benefits

| Feature | Manual Sitemap | Firecrawl Crawl |
|---------|---------------|-----------------|
| **Steps** | 6 steps | 1 step |
| **Code complexity** | High | Low |
| **JavaScript support** | No | Yes |
| **Content extraction** | Manual | Automatic |
| **Metadata** | Minimal | Rich (titles, descriptions, etc.) |
| **Error handling** | Complex | Built-in |

---

## Quick Start

### 1. Simple Usage

```python
from core.website_crawler.firecrawl_simple import quick_crawl

# Crawl entire category
docs = quick_crawl("https://www.dior.com/en_ae/fashion/womens-fashion/bags", max_pages=50)

print(f"Loaded {len(docs)} pages")
```

### 2. With Options

```python
from core.website_crawler.firecrawl_simple import load_site_with_firecrawl_sync

docs = load_site_with_firecrawl_sync(
    url="https://www.dior.com/en_ae/fashion/womens-fashion/bags",
    max_pages=100
)

# Each document has rich metadata
for doc in docs[:3]:
    print(f"Title: {doc.metadata['title']}")
    print(f"URL: {doc.metadata['source_url']}")
    print(f"Content: {len(doc.page_content)} chars")
    print()
```

### 3. Async Version

```python
from core.website_crawler.firecrawl_simple import load_site_with_firecrawl

docs = await load_site_with_firecrawl(
    url="https://www.dior.com/en_ae/fashion/womens-fashion/bags",
    max_pages=50
)
```

---

## Integration with Your API

The crawler now **automatically uses Firecrawl crawl mode** as the first priority:

### Priority Order:

1. **Firecrawl crawl mode** (if URL is not XML) ⭐ **RECOMMENDED**
2. **XML parser** (if URL is sitemap.xml)
3. **Crawl4AI + WebBaseLoader** (fallback)

### Example API Request:

```json
POST /analyze
{
  "brand_name": "Dior",
  "brand_url": "https://www.dior.com/en_ae/fashion/womens-fashion/bags/all-the-bags",
  "url_type": "category",
  ...
}
```

**What happens:**
1. API gets the URL
2. Detects it's not XML
3. Uses **Firecrawl crawl mode** ✅
4. Loads all pages with content automatically
5. Indexes in Pinecone
6. Continues with analysis

---

## Output Format

Each document contains:

```python
Document(
    page_content="<markdown content of the page>",
    metadata={
        'title': 'Page Title',
        'url': 'https://example.com/page',
        'source_url': 'https://example.com/page',
        'description': 'Page description',
        'language': 'en',
        'status_code': 200,
        'content_type': 'text/html; charset=utf-8',
        # ... and more
    }
)
```

---

## Configuration

### Enable/Disable Firecrawl

In `core/config.py`:

```python
class FirecrawlConfig:
    ENABLED = True  # Set to False to disable
```

### Set API Key

```bash
export FIRECRAWL_API_KEY="your-api-key-here"
```

Or in `.env`:
```
FIRECRAWL_API_KEY=your-api-key-here
```

---

## Advanced: Category-Specific Crawling

Only crawl specific category paths:

```python
from core.website_crawler.firecrawl_simple import load_specific_category_with_firecrawl

# Only crawl bags category
docs = await load_specific_category_with_firecrawl(
    base_url="https://www.dior.com",
    category_path="/en_ae/fashion/womens-fashion/bags",
    max_pages=50
)

print(f"Loaded {len(docs)} pages from bags category only")
```

---

## Command Line Usage

```bash
# Crawl a URL from command line
python core/website_crawler/firecrawl_simple.py "https://www.dior.com/en_ae/fashion/womens-fashion/bags" 20

# Output:
# 🔥 Crawling: https://www.dior.com/en_ae/fashion/womens-fashion/bags
# Max pages: 20
#
# ✅ Loaded 20 pages:
#
# 1. Dior Bags for Women
#    URL: https://www.dior.com/en_ae/fashion/womens-fashion/bags/all-the-bags
#    Content: 5423 chars
# ...
```

---

## Comparison: Manual vs Firecrawl Crawl

### Manual Approach (Old)

```python
# 1. Find sitemap
sitemap_url = await find_sitemap_url(website_url)

# 2. Parse XML
urls = await parse_xml_sitemap(sitemap_url)

# 3. Load each URL
documents = []
for url in urls:
    content = await load_url_content(url)
    documents.append(content)

# 4. Clean and extract
cleaned_docs = [extract_content(doc) for doc in documents]

# Total: ~100+ lines of code, multiple error points
```

### Firecrawl Crawl (New)

```python
# 1. Load everything
documents = await load_site_with_firecrawl(website_url)

# Total: 1 line of code, built-in error handling
```

---

## Cost Considerations

- **Firecrawl**: ~1 credit per page
- **Manual**: Free but complex and slower

**Recommendation**: Use Firecrawl crawl mode for:
- Production use cases
- Complex sites with JavaScript
- When you need reliable content extraction

Use manual XML parsing for:
- Simple static sites
- When you already have sitemap URL
- Testing/development

---

## Troubleshooting

### Firecrawl returns 0 documents

```python
# Check if Firecrawl is enabled
from core.config import FirecrawlConfig
print(f"Firecrawl enabled: {FirecrawlConfig.ENABLED}")

# Check API key
import os
print(f"API key set: {bool(os.getenv('FIRECRAWL_API_KEY'))}")
```

### Want to use XML parser instead

```python
# If URL ends with .xml, it automatically uses XML parser
docs = await load_sitemap_documents_parallel("https://example.com/sitemap.xml")
```

### Want to disable Firecrawl

In `core/config.py`:
```python
class FirecrawlConfig:
    ENABLED = False
```

---

## Summary

**Use Firecrawl crawl mode when:**
- ✅ You want simple, reliable crawling
- ✅ Site has JavaScript-rendered content
- ✅ You want rich metadata
- ✅ You're okay with API costs

**Use XML parsing when:**
- ✅ URL is explicitly sitemap.xml
- ✅ You want free solution
- ✅ Site has well-structured sitemaps

**The system automatically picks the best method for you!**
