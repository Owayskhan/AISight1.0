# Removed Dependencies

This document lists dependencies that were removed after refactoring to eliminate website crawling and vector indexing.

## Removed in Refactoring (2025-01-20)

### Vector Indexing/Storage
- ❌ `langchain-pinecone` - No longer doing Pinecone vector indexing
- ❌ `pinecone` - No longer using Pinecone client
- ❌ `faiss-cpu` - No longer doing FAISS in-memory vector indexing

### Web Crawling
- ❌ `crawl4ai` - No longer crawling entire websites
- ❌ `playwright` - Was dependency of crawl4ai

## Still Required

### Core API
- ✅ `fastapi` - API framework
- ✅ `uvicorn[standard]` - ASGI server
- ✅ `pydantic>=2.0.0` - Data validation
- ✅ `typing-extensions>=4.5.0` - Type hints support

### LangChain & LLMs
- ✅ `langchain` - Core LangChain library
- ✅ `langchain-openai` - OpenAI integration (GPT-4o-mini)
- ✅ `langchain-google-genai` - Gemini integration
- ✅ `langchain-perplexity` - Perplexity integration
- ✅ `langchain_tavily` - Tavily search integration
- ✅ `langchain-community` - Community integrations (WebBaseLoader)
- ✅ `langchain-text-splitters` - Text chunking utilities
- ✅ `openai` - OpenAI Python client
- ✅ `google-generativeai` - Google AI client

### Web Utilities
- ✅ `requests` - HTTP library
- ✅ `aiohttp` - Async HTTP
- ✅ `beautifulsoup4` - HTML parsing
- ✅ `html2text` - HTML to text conversion
- ✅ `lxml` - XML/HTML parser

### Research & Data
- ✅ `tavily-python` - Tavily search API

### Azure
- ✅ `azure-messaging-webpubsubservice` - Real-time updates

### Utilities
- ✅ `python-dotenv` - Environment variable management

## Migration Notes

If you need to restore the old functionality with crawling/indexing:
1. Re-add the removed dependencies to requirements.txt
2. Restore the old version of `api/main.py` (lines 278-750 before refactoring)
3. Remove `core/queries/context_builder.py`
4. The old code is available in git history before this refactor commit
