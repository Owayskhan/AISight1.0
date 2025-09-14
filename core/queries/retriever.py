
from core.models.main import Queries
from langchain_community.document_loaders import WebBaseLoader
import os
from dotenv import load_dotenv
load_dotenv(override=True)

async def retrieve_queries_context(queries: Queries, retriever, content_preloaded=False):
    """
    Retrieve context for queries either by loading web pages on-demand or using pre-loaded content.
    
    Args:
        queries: Queries object containing list of queries
        retriever: Vector store retriever
        content_preloaded: If True, checks documents for full content or loads as needed
    
    Returns:
        List of dicts containing query and context documents
    """
    retrieved = []
    for query in queries.queries:
        context = await retriever.ainvoke(query.query)
        
        if content_preloaded:
            # Check if documents already have full content
            full_docs = []
            for doc in context:
                if doc.metadata.get("content_type") == "full_content":
                    # Document already has full page content
                    full_docs.append(doc)
                else:
                    # Document contains URL, need to load content
                    loader = WebBaseLoader(doc.page_content)
                    loaded = loader.load()
                    full_docs.extend(loaded)
        else:
            # Legacy behavior: documents contain URLs, need to load web pages
            loaded_pages = [doc.page_content for doc in context]
            loaders = [WebBaseLoader(page) for page in loaded_pages]
            full_docs = []
            for loader in loaders:
                docs = loader.load()
                full_docs.extend(docs)
        
        retrieved.append({
            "query": query,
            "context": full_docs
        })

    return retrieved

async def retrieve_queries_context_preloaded(queries: Queries, retriever):
    """
    Convenience function for retrieving context from pre-loaded documents.
    This is equivalent to calling retrieve_queries_context with content_preloaded=True.
    
    Args:
        queries: Queries object containing list of queries
        retriever: Vector store retriever with pre-loaded documents
    
    Returns:
        List of dicts containing query and context documents
    """
    return await retrieve_queries_context(queries, retriever, content_preloaded=True)