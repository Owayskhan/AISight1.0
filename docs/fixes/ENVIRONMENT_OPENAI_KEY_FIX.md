# Environment OpenAI Key for Embeddings - Consistency Fix

## 🎯 Problem

The system was using the **user-provided OpenAI API key** for embeddings during both indexing and retrieval. This caused two critical issues:

1. **Inconsistent Embeddings**: If a user indexed with one key and retrieved with another (or no key), the embedding models might differ
2. **Retrieval Failures**: Users without OpenAI keys couldn't retrieve indexed content
3. **0 Documents Retrieved**: Even with the same key, there might be subtle differences in embedding generation

## ✅ Solution

**Use the environment OpenAI API key** for ALL embedding operations (indexing and retrieval) to ensure:
- **Consistency**: Same key = same embeddings = successful similarity search
- **Reliability**: Works even if users don't provide OpenAI keys
- **Cost Control**: You control the embedding costs, not users

---

## 📝 Changes Made

### 1. Category Flow - Indexing ([api/main.py:404-421](api/main.py#L404-L421))

**Before:**
```python
retriever = await get_smart_retriever(
    brand_name=request.brand_name,
    sitemap_url=sitemap_url if sitemap_url != "existing_namespace" else None,
    api_key=request.api_keys.openai_api_key,  # ❌ User key
    ...
)
```

**After:**
```python
# IMPORTANT: Use environment OpenAI key for embeddings to ensure consistency
import os
env_openai_key = os.getenv("OPENAI_API_KEY")
if not env_openai_key:
    raise ValueError("OPENAI_API_KEY environment variable is required for indexing and retrieval")

retriever = await get_smart_retriever(
    brand_name=request.brand_name,
    sitemap_url=sitemap_url if sitemap_url != "existing_namespace" else None,
    api_key=env_openai_key,  # ✅ Environment key
    ...
)
```

### 2. Category Flow - Retrieval ([api/main.py:688-712](api/main.py#L688-L712))

**Before:**
```python
if not content_preloaded:
    from core.indexer.pinecone_indexer import get_pinecone_manager
    pinecone_manager = get_pinecone_manager()
else:
    pinecone_manager = None

retrieved_queries = await retrieve_queries_context_concurrent(
    queries_obj,
    retriever,
    content_preloaded=content_preloaded,
    max_concurrent=max_concurrent_downloads,
    pinecone_manager=pinecone_manager,
    brand_name=request.brand_name if not content_preloaded else None,
    openai_api_key=request.api_keys.openai_api_key if not content_preloaded else None,  # ❌ User key
    k=4
)
```

**After:**
```python
# IMPORTANT: Use environment OpenAI key for embeddings to ensure consistency
import os
if not content_preloaded:
    from core.indexer.pinecone_indexer import get_pinecone_manager
    pinecone_manager = get_pinecone_manager()
    # Use environment key for consistent embeddings
    env_openai_key = os.getenv("OPENAI_API_KEY")
    if not env_openai_key:
        raise ValueError("OPENAI_API_KEY environment variable is required for retrieval")
else:
    pinecone_manager = None
    env_openai_key = None

retrieved_queries = await retrieve_queries_context_concurrent(
    queries_obj,
    retriever,
    content_preloaded=content_preloaded,
    max_concurrent=max_concurrent_downloads,
    pinecone_manager=pinecone_manager,
    brand_name=request.brand_name if not content_preloaded else None,
    openai_api_key=env_openai_key if not content_preloaded else None,  # ✅ Environment key
    k=4
)
```

### 3. Product Flow - Indexing ([api/main.py:322-333](api/main.py#L322-L333))

**Before:**
```python
vector_store = await create_vector_store_optimized(
    product_docs,
    request.api_keys.openai_api_key,  # ❌ User key
    batch_size=request.indexing_batch_size,
    progress_callback=indexing_progress_callback
)
```

**After:**
```python
# IMPORTANT: Use environment OpenAI key for embeddings to ensure consistency
import os
env_openai_key = os.getenv("OPENAI_API_KEY")
if not env_openai_key:
    raise ValueError("OPENAI_API_KEY environment variable is required for product indexing")

vector_store = await create_vector_store_optimized(
    product_docs,
    env_openai_key,  # ✅ Environment key
    batch_size=request.indexing_batch_size,
    progress_callback=indexing_progress_callback
)
```

---

## 🔄 Complete Flow

### Indexing (One Time)
```
1. API Request with brand_url
   ↓
2. Crawl4AI discovers 59 URLs
   ↓
3. WebBaseLoader downloads content for 59 URLs
   ↓
4. Generate embeddings using ENVIRONMENT_OPENAI_KEY  ✅
   ↓
5. Store in Pinecone namespace 'brand-hm'
   ↓
6. Indexed: 59 documents with embeddings from env key
```

### Retrieval (Every Query)
```
1. User sends query: "H&M fragrance collection"
   ↓
2. Generate query embedding using ENVIRONMENT_OPENAI_KEY  ✅
   ↓
3. Search Pinecone with query embedding
   ↓
4. Pinecone compares with stored embeddings (also from env key)  ✅
   ↓
5. ✅ MATCH FOUND! Similar embeddings detected
   ↓
6. Return 4-10 relevant documents
```

### Why This Works

**Same Key = Same Model = Same Embedding Space**

```
Indexing:
  Document: "H&M Eau de Parfum | Floral scent | $29.99"
  → Embedding (env key): [0.23, -0.15, 0.87, ..., 0.42]  ← Stored in Pinecone

Retrieval:
  Query: "H&M fragrance collection"
  → Embedding (env key): [0.25, -0.13, 0.85, ..., 0.40]  ← Generated with same key

Similarity Calculation:
  cosine_similarity([0.23, -0.15, ...], [0.25, -0.13, ...]) = 0.89  ← High match!
  ✅ Document retrieved successfully
```

---

## 🚨 Important: Reindex Required

**All existing namespaces** were indexed with user-provided keys. They need to be reindexed with the environment key:

```json
{
  "force_reindex": true
}
```

This will:
1. Delete old embeddings (generated with user keys)
2. Re-download content
3. Generate new embeddings with environment key
4. Store in Pinecone

After reindexing, queries will successfully retrieve documents!

---

## 🧪 Testing

### Test Case: Reindex and Query

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "H&M",
    "brand_url": "https://www2.hm.com/en_us/beauty/shop-by-product/fragrance.html",
    "url_type": "category",
    "force_reindex": true,
    "product_category": "Fragrances",
    "api_keys": {
      "gemini_api_key": "AIza..."
    }
  }'
```

**Note**: No `openai_api_key` provided by user! System uses environment key.

**Expected Logs:**
```log
✅ Crawl4AI discovered 59 unique URLs
📥 Downloading content for 59 URLs using WebBaseLoader...
✅ Content loading complete: 55 URLs with content extracted
📝 Indexing using environment OPENAI_API_KEY
✅ Successfully indexed 59 documents

📦 Processing query 1/10: H&M fragrance collection...
✅ Retrieved 4 documents  ← Documents found!
📦 Processing query 2/10: sustainable perfumes...
✅ Retrieved 6 documents  ← Documents found!
```

---

## 📊 Benefits

### 1. Consistency
- ✅ **Same embeddings** for indexing and retrieval
- ✅ **Reliable similarity search** (documents actually match queries)
- ✅ **No more 0 documents** due to embedding mismatch

### 2. User Experience
- ✅ **Users don't need OpenAI keys** for category flow
- ✅ **Simpler API** - one less required field
- ✅ **Faster onboarding** - fewer API keys to manage

### 3. Cost Control
- ✅ **You control embedding costs** (predictable expenses)
- ✅ **Centralized billing** (one OpenAI account)
- ✅ **Rate limit management** (your key, your limits)

### 4. Reliability
- ✅ **No key conflicts** (always use the right key)
- ✅ **No permission issues** (your key has access)
- ✅ **Consistent performance** (same model, same behavior)

---

## 🔑 Required Environment Variable

**Must be set in environment:**

```bash
export OPENAI_API_KEY="sk-..."
```

**Or in `.env` file:**
```
OPENAI_API_KEY=sk-...
```

**Validation:**
- System checks for `OPENAI_API_KEY` at indexing and retrieval
- Raises clear error if not set: `"OPENAI_API_KEY environment variable is required"`

---

## 📈 Impact on API

### API Keys Field

**Before:**
```json
{
  "api_keys": {
    "openai_api_key": "sk-...",  // Required for embeddings
    "gemini_api_key": "AIza...",  // Optional
    "perplexity_api_key": "pplx-..."  // Optional
  }
}
```

**After:**
```json
{
  "api_keys": {
    // openai_api_key: NOT REQUIRED for embeddings anymore!
    // Still needed for: query generation, brand profiling, citation analysis
    // But can be omitted if using other LLMs
    "gemini_api_key": "AIza...",
    "perplexity_api_key": "pplx-..."
  }
}
```

### User-Provided OpenAI Key

**Still used for (if provided):**
- Query generation (can use Gemini instead)
- Brand profiling (can use Gemini/Perplexity instead)
- Citation analysis (required if no other LLM)

**NOT used for:**
- ❌ Embedding generation during indexing
- ❌ Embedding generation during retrieval

---

## 🎯 Summary

### Problem
User-provided OpenAI keys caused inconsistent embeddings → 0 documents retrieved

### Solution
Use environment OpenAI key for ALL embeddings → consistent vector space → successful retrieval

### Action Required
1. Set `OPENAI_API_KEY` in environment
2. Reindex all existing namespaces with `force_reindex: true`
3. Test retrieval - should now return 4-10 documents per query

### Result
- ✅ Consistent embeddings
- ✅ Successful document retrieval
- ✅ Simpler API (fewer required user keys)
- ✅ Better cost control

---

**This fix ensures that embeddings are always generated with the same key, enabling reliable similarity search and document retrieval!** 🎉
