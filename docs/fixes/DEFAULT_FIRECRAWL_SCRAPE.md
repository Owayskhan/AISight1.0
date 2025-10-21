# Default: Firecrawl Scrape Mode

## ✅ Changes Made

**Firecrawl is now the default method for loading pages.**

### What This Means:

When you provide a category URL like:
```
https://www.dior.com/en_ae/fashion/womens-fashion/bags/all-the-bags
```

The system will:
1. **Use Firecrawl scrape mode** to load JUST that page ✅
2. **NOT crawl the entire site** ✅
3. **NOT fetch the sitemap** ✅

---

## Priority Order (Updated)

### 1. **Firecrawl Scrape Mode** (DEFAULT) ⭐
- Loads the specific page you provide
- Fast, simple, reliable
- Handles JavaScript
- Rich metadata included

### 2. **XML Sitemap Parser** (if URL ends with .xml)
- Only used if you explicitly provide sitemap.xml URL
- Parses XML and extracts all URLs

### 3. **Crawl4AI** (fallback, disabled by default)
- Only used if Firecrawl fails
- Slower, more complex

---

## Configuration

In [core/config.py](core/config.py):

```python
# Firecrawl is now PRIMARY
class FirecrawlConfig:
    ENABLED = True  # ✅ Default

# Crawl4AI is now FALLBACK
class Crawl4AIConfig:
    ENABLED = False  # ✅ Disabled by default
```

---

## How It Works Now

### Example Request:

```json
POST /analyze
{
  "brand_name": "Dior",
  "brand_url": "https://www.dior.com/en_ae/fashion/womens-fashion/bags/all-the-bags",
  "url_type": "category",
  ...
}
```

### What Happens:

```
1. API receives URL ✅
2. Detects it's NOT sitemap.xml ✅
3. Uses Firecrawl scrape mode ✅
4. Loads JUST that page (not entire site) ✅
5. Returns 1 document with full content ✅
6. Indexes in Pinecone ✅
7. Continues with analysis ✅
```

---

## Logs You'll See:

```
🔥 Using Firecrawl scrape mode to load page (recommended)...
✅ Firecrawl loaded page successfully: 1 document(s)
   Title: Dior Bags for Women
   Content length: 5423 chars
```

---

## Benefits

| Feature | Old (Sitemap) | New (Firecrawl Scrape) |
|---------|--------------|------------------------|
| **Speed** | Slow (many pages) | Fast (1 page) |
| **Complexity** | High | Low |
| **What you get** | Entire site | Just the page you want |
| **JavaScript** | Limited | Full support |
| **Content quality** | Variable | High quality |

---

## FAQ

### Q: Will it still find all products on the page?

**A:** Yes! Firecrawl extracts all content from the page, including product links and information.

### Q: What if I want to crawl the entire site?

**A:** You have two options:

1. **Use sitemap URL** - Provide the sitemap.xml URL:
   ```python
   brand_url = "https://www.dior.com/sitemap.xml"
   ```

2. **Use Firecrawl crawl mode** manually:
   ```python
   from core.website_crawler.firecrawl_simple import load_site_with_firecrawl
   docs = await load_site_with_firecrawl(url, max_pages=100)
   ```

### Q: What if Firecrawl fails?

**A:** The system automatically falls back to:
1. XML parser (if .xml URL)
2. Crawl4AI (if enabled)
3. Legacy methods

### Q: How do I disable Firecrawl?

In [core/config.py](core/config.py):
```python
class FirecrawlConfig:
    ENABLED = False  # Disable Firecrawl
```

### Q: Does this cost money?

**A:** Yes, Firecrawl uses ~1 credit per page scraped. But:
- You're only scraping 1 page (the category page you provide)
- Much faster and more reliable
- Better content quality

---

## Testing

Test with Dior:

```bash
# Your API will now use Firecrawl by default
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "Dior",
    "brand_url": "https://www.dior.com/en_ae/fashion/womens-fashion/bags/all-the-bags",
    "url_type": "category",
    ...
  }'
```

Expected result:
- ✅ Fast response
- ✅ Clean content
- ✅ No "0 URLs found" errors
- ✅ Works with JavaScript-heavy sites

---

## Summary

**Before**: Complex sitemap parsing → slow, error-prone
**Now**: Simple Firecrawl scrape → fast, reliable

**You get**: Just the page you ask for, with high-quality content, ready to index.

🎉 **That's it! Much simpler and more reliable.**
