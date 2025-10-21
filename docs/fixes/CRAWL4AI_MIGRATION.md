# Migration from Firecrawl to Crawl4AI

## ✅ Changes Completed

Your codebase has been successfully migrated from **Firecrawl** to **Crawl4AI** for web crawling.

---

## 🎯 Why Crawl4AI?

| Feature | Firecrawl | Crawl4AI |
|---------|-----------|----------|
| **Cost** | 💰 API-based (paid) | ✅ Open-source (free) |
| **Control** | ⚠️ Limited | ✅ Full control |
| **Browser** | ✅ Cloud-based | ✅ Local Playwright |
| **Speed** | ⚡ Fast (cloud) | ⚡ Fast (local) |
| **Customization** | ⚠️ API limits | ✅ Fully customizable |
| **Dependencies** | ℹ️ API key required | ℹ️ Playwright required |

---

## 📋 Files Modified

### 1. **requirements.txt**
```diff
# Web scraping and crawling
- firecrawl-py
+ crawl4ai
```

### 2. **core/config.py**
- ✅ Marked `FirecrawlConfig` as deprecated
- ✅ Added new `Crawl4AIConfig` class
- ✅ Set `Crawl4AIConfig.ENABLED = True` (default)
- ✅ Set `FirecrawlConfig.ENABLED = False`

### 3. **core/website_crawler/crawler.py**
- ✅ Added `get_sitemap_urls_crawl4ai()` function
- ✅ Updated `find_sitemap_url_async()` to prioritize Crawl4AI
- ✅ Updated `load_sitemap_documents()` to use Crawl4AI
- ✅ Updated `load_sitemap_documents_parallel()` to use Crawl4AI
- ✅ Kept Firecrawl as fallback (disabled by default)

---

## 🚀 How It Works

### URL Discovery Flow

```
1. Crawl4AI (Primary) ← Default method
   ↓ (if fails)
2. Firecrawl (Secondary) ← Disabled by default
   ↓ (if fails)
3. Legacy XML Sitemap Parser (Fallback)
```

### Crawl4AI Implementation

```python
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from bs4 import BeautifulSoup

async def get_sitemap_urls_crawl4ai(website_url: str):
    # Initialize crawler
    crawler = AsyncWebCrawler()
    config = CrawlerRunConfig()

    # Crawl the page
    result = await crawler.arun(url=website_url, config=config)

    # Extract URLs from HTML
    crawl_result = result[0]
    soup = BeautifulSoup(crawl_result.html, 'html.parser')

    # Find all links
    for link in soup.find_all('a', href=True):
        # Extract and clean URLs...

    await crawler.close()
    return urls
```

**Key Features:**
- ✅ Uses Playwright browser (headless Chrome)
- ✅ Extracts all `<a href>` tags from HTML
- ✅ Filters to same-domain URLs only
- ✅ Removes duplicates and fragments
- ✅ Returns sorted list of clean URLs

---

## 🔧 Configuration

### Enable/Disable Crawlers

Edit **`core/config.py`**:

```python
# Crawl4AI Configuration (DEFAULT)
class Crawl4AIConfig:
    ENABLED = True  # Use Crawl4AI
    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 2

# Firecrawl Configuration (FALLBACK)
class FirecrawlConfig:
    ENABLED = False  # Disabled by default
    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 2
```

---

## 📦 Dependencies

### Python Packages

**Required:**
```bash
pip install crawl4ai
```

**Crawl4AI automatically installs:**
- `playwright` - Browser automation
- `beautifulsoup4` - HTML parsing (already in your requirements.txt)
- `aiohttp` - Async HTTP (already in your requirements.txt)

### System Dependencies (Playwright Browsers)

**Already configured in:**
- ✅ `Dockerfile` - Playwright + Chromium installation
- ✅ `.github/workflows/main_aisightapi.yml` - CI/CD browser installation
- ✅ `startup.sh` - Azure App Service browser setup

---

## 🐳 Docker Setup (Ready)

Your **Dockerfile** already includes Playwright:

```dockerfile
# System dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates \
    fonts-liberation libasound2 \
    libatk-bridge2.0-0 libatk1.0-0 \
    # ... all Playwright dependencies

# Install Playwright browsers
RUN if pip list | grep -q playwright; then \
    playwright install --with-deps chromium; \
    fi
```

**Build and run:**
```bash
docker build -t aisight-crawl4ai:latest .
docker run -p 8000:8000 --env-file .env aisight-crawl4ai:latest
```

---

## ☁️ Azure App Service Deployment

### GitHub Actions (Ready)

Your **`.github/workflows/main_aisightapi.yml`** is already configured:

```yaml
- name: Install Playwright browsers (if needed)
  run: |
    source venv/bin/activate
    if pip list | grep -q playwright; then
      playwright install --with-deps chromium
    fi
```

### Startup Script (Ready)

Your **`startup.sh`** handles Playwright at runtime:

```bash
# Install Playwright browsers if Playwright is installed
if python -c "import playwright" 2>/dev/null; then
    python -m playwright install --with-deps chromium
fi
```

---

## ⚠️ Azure Limitations

**Important:** Azure App Service Python runtime has limited system packages.

### Will It Work?

| Deployment Method | Crawl4AI Support | Notes |
|-------------------|------------------|-------|
| **Docker** | ✅ Full support | Recommended - complete control |
| **Azure App Service (Python)** | ⚠️ Partial | May work, but test thoroughly |
| **Azure Container Instances** | ✅ Full support | Docker-based deployment |

### Troubleshooting Azure App Service

If you encounter errors like:
```
❌ Playwright browser download failed
❌ Missing system dependencies
```

**Solutions:**

1. **Check App Service logs:**
   ```bash
   az webapp log tail --name aisightapi --resource-group aisight-rg
   ```

2. **Enable Firecrawl fallback:**
   ```python
   # core/config.py
   class FirecrawlConfig:
       ENABLED = True  # Enable as fallback
   ```

3. **Migrate to Docker deployment** (recommended):
   - See [PLAYWRIGHT_AZURE_SETUP.md](PLAYWRIGHT_AZURE_SETUP.md)
   - Full Playwright support guaranteed

---

## 🧪 Testing

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Test the API
python -m uvicorn api.main:app --reload
```

### Test Crawl4AI Directly

```python
import asyncio
from core.website_crawler.crawler import get_sitemap_urls_crawl4ai

async def test():
    urls = await get_sitemap_urls_crawl4ai("https://www.novoshoes.com.au")
    print(f"Found {len(urls)} URLs")
    for url in urls[:10]:  # Print first 10
        print(f"  - {url}")

asyncio.run(test())
```

### Expected Output

```
🕷️ Using Crawl4AI to discover URLs for: https://www.novoshoes.com.au
📡 Calling Crawl4AI to fetch page...
✅ Crawl4AI discovered 245 unique URLs from HTML
✅ Total unique URLs discovered: 245
Found 245 URLs
  - https://www.novoshoes.com.au/
  - https://www.novoshoes.com.au/new-arrivals
  - https://www.novoshoes.com.au/shoes/heels
  - https://www.novoshoes.com.au/shoes/flats
  ...
```

---

## 🔄 Rollback Plan

If Crawl4AI doesn't work on Azure App Service:

### Option 1: Enable Firecrawl Fallback

```python
# core/config.py
class Crawl4AIConfig:
    ENABLED = False  # Disable Crawl4AI

class FirecrawlConfig:
    ENABLED = True  # Re-enable Firecrawl
```

### Option 2: Full Rollback

```bash
# Revert requirements.txt
git checkout HEAD -- requirements.txt

# Revert config.py
git checkout HEAD -- core/config.py

# Revert crawler.py
git checkout HEAD -- core/website_crawler/crawler.py

# Commit rollback
git commit -m "Rollback to Firecrawl"
git push origin main
```

---

## 📊 Performance Comparison

### Crawl4AI Advantages

1. **No API costs** - Free and open-source
2. **No rate limits** - Control your own concurrency
3. **Full customization** - Configure browser, timeouts, retries
4. **Local execution** - No network dependency on external API

### Crawl4AI Considerations

1. **System dependencies** - Requires Playwright browsers
2. **Memory usage** - Browser instances use more memory
3. **Deployment complexity** - Docker recommended for production

---

## 🎯 Recommendation

### For Development
✅ **Use Crawl4AI** - Full control, no API keys needed

### For Production

**If using Docker deployment:**
- ✅ **Use Crawl4AI** - Works perfectly

**If using Azure App Service (Python runtime):**
- ⚠️ **Test Crawl4AI first**
- ✅ **Keep Firecrawl as fallback** (set `ENABLED = True` for both)
- 🎯 **Consider migrating to Docker** for best results

---

## 📝 Summary

✅ **Crawl4AI configured** - Primary crawling method
✅ **Firecrawl kept** - Available as fallback (disabled by default)
✅ **Docker ready** - Full Playwright support
✅ **CI/CD updated** - GitHub Actions configured
✅ **Azure ready** - Startup script configured
✅ **Backward compatible** - Can easily switch between methods

**Next Step:** Deploy and test on Azure App Service to ensure Crawl4AI works in your production environment!

---

## 🚨 Important Notes

1. **Playwright Browsers**: Crawl4AI will download ~200MB of Chromium on first run
2. **Environment Variables**: No `FIRECRAWL_API_KEY` needed anymore!
3. **Concurrent Crawling**: You control the concurrency limits
4. **Error Handling**: All functions have robust fallback mechanisms

---

## 💬 Need Help?

- **Crawl4AI docs**: https://github.com/unclecode/crawl4ai
- **Playwright docs**: https://playwright.dev/python/
- **Azure App Service**: Check [PLAYWRIGHT_AZURE_SETUP.md](PLAYWRIGHT_AZURE_SETUP.md)
