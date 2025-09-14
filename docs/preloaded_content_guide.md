# Pre-loaded Content Guide

This guide explains how to use the pre-loaded content feature for improved performance when processing product pages.

## Overview

The pre-loaded content feature allows you to load all web page content during the indexing phase, rather than loading pages on-demand during query processing. This can significantly improve performance, especially when processing multiple queries.

## Benefits

1. **Better Performance**: Eliminates repeated web requests during query processing
2. **Offline Processing**: Once content is loaded, no internet connection is needed for retrieval
3. **Consistency**: All queries work with the same snapshot of content
4. **Caching**: Content can be saved and reused across sessions

## Usage

### API Usage

When using the API, simply set `preload_content` to `true` in your request:

```json
{
  "brand_name": "Example Brand",
  "brand_url": "https://example.com",
  "product_category": "Electronics",
  "preload_content": true,
  "max_pages": 50,  // Optional: limit pages for testing
  "api_keys": {
    "openai_api_key": "sk-...",
    "gemini_api_key": "AIza...",
    "perplexity_api_key": "pplx-..."
  }
}
```

### Programmatic Usage

```python
from core.indexer.indexer_enhanced import get_retriever
from core.queries.retriever import retrieve_queries_context_preloaded

# Create retriever with pre-loaded content
retriever = get_retriever(
    sitemap_url="https://example.com/sitemap.xml",
    api_key="your-openai-api-key",
    k=4,
    preload_content=True,
    max_pages=50  # Optional: limit for testing
)

# Use the pre-loaded retriever
results = await retrieve_queries_context_preloaded(queries, retriever)
```

### Using Pre-existing Documents

You can also create a retriever from documents you've already loaded:

```python
from core.indexer.indexer_enhanced import get_retriever_from_documents
from core.website_crawler.crawler_enhanced import load_sitemap_documents

# Load documents with content
documents = load_sitemap_documents(sitemap_url, load_content=True)

# Create retriever from documents
retriever = get_retriever_from_documents(documents, api_key)
```

## Performance Comparison

### Traditional Approach (URL-only)
1. Index URLs from sitemap (fast)
2. For each query:
   - Retrieve relevant URLs
   - Load web pages (slow, requires internet)
   - Process content

### Pre-loaded Approach
1. Load all web pages and index content (slower initial setup)
2. For each query:
   - Retrieve relevant pre-loaded documents (fast)
   - Process content (no web requests needed)

## When to Use Pre-loaded Content

**Use pre-loaded content when:**
- Processing multiple queries against the same website
- Working offline or with unreliable internet
- Need consistent results across queries
- Want to cache content for repeated use

**Use traditional approach when:**
- Processing just a few queries
- Website content changes frequently
- Memory is limited
- Only need to process a small subset of pages

## Advanced Features

### Saving and Loading Vector Stores

```python
from core.indexer.indexer_enhanced import save_vector_store, get_retriever_from_saved_store

# Save vector store
save_vector_store(vector_store, "./saved_stores/brand_name")

# Load and use saved store
retriever = get_retriever_from_saved_store("./saved_stores/brand_name", api_key)
```

### Async Loading

For better performance with large sites:

```python
from core.website_crawler.crawler_enhanced import load_sitemap_documents_async

# Asynchronously load documents
documents = await load_sitemap_documents_async(
    sitemap_url,
    load_content=True,
    max_pages=100
)
```

## Error Handling

The system gracefully handles errors:
- Failed page loads create URL-only documents with error metadata
- Partial failures don't stop the entire process
- Error information is preserved in document metadata

## Best Practices

1. **Start Small**: Use `max_pages` parameter for initial testing
2. **Monitor Memory**: Pre-loading many pages requires more memory
3. **Cache Results**: Save vector stores for frequently accessed brands
4. **Batch Processing**: The enhanced crawler processes URLs in batches to avoid overwhelming servers
5. **Check Metadata**: Use `content_type` metadata to verify if documents are pre-loaded

## Example

See `examples/preloaded_retrieval_example.py` for a complete working example.