import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
import os
from langchain_openai import OpenAIEmbeddings
from core.website_crawler.crawler import load_sitemap_documents
from core.website_crawler.crawler_enhanced import load_sitemap_documents as load_sitemap_documents_enhanced
from typing import List, Optional
from langchain.schema import Document
import logging

logger = logging.getLogger(__name__)

def create_vector_store(sitemap_docs: List[Document], api_key: str, embeddings_model: str = "text-embedding-3-small"):
    """
    Create a FAISS vector store from documents.
    
    Args:
        sitemap_docs: List of Document objects
        api_key: OpenAI API key
        embeddings_model: OpenAI embeddings model to use
    
    Returns:
        FAISS vector store
    """
    embeddings = OpenAIEmbeddings(model=embeddings_model, api_key=api_key)

    # Create index
    index = faiss.IndexFlatL2(len(embeddings.embed_query("hello world")))

    sitemap_vector_store = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )

    from uuid import uuid4

    uuids = [str(uuid4()) for _ in range(len(sitemap_docs))]

    sitemap_vector_store.add_documents(documents=sitemap_docs, ids=uuids)

    return sitemap_vector_store

def get_retriever(sitemap_url: str, api_key: str, k: int = 4, preload_content: bool = False, max_pages: Optional[int] = None):
    """
    Get a retriever for sitemap documents.
    
    Args:
        sitemap_url: URL of the sitemap
        api_key: OpenAI API key
        k: Number of documents to retrieve
        preload_content: If True, loads full page content during indexing
        max_pages: Maximum number of pages to load (useful for testing)
    
    Returns:
        Retriever configured for similarity search
    """
    if preload_content:
        logger.info(f"Loading sitemap with full content from {sitemap_url}")
        sitemap_docs = load_sitemap_documents_enhanced(sitemap_url, load_content=True, max_pages=max_pages)
        logger.info(f"Loaded {len(sitemap_docs)} documents with content")
    else:
        logger.info(f"Loading sitemap URLs from {sitemap_url}")
        sitemap_docs = load_sitemap_documents(sitemap_url)
        logger.info(f"Loaded {len(sitemap_docs)} URL documents")
    
    sitemap_vector_store = create_vector_store(sitemap_docs, api_key)
    return sitemap_vector_store.as_retriever(search_type="similarity", search_kwargs={"k": k})

def get_retriever_from_documents(documents: List[Document], api_key: str, k: int = 4):
    """
    Create a retriever from pre-existing documents.
    
    Args:
        documents: List of Document objects (can be pre-loaded with content)
        api_key: OpenAI API key
        k: Number of documents to retrieve
    
    Returns:
        Retriever configured for similarity search
    """
    logger.info(f"Creating retriever from {len(documents)} documents")
    sitemap_vector_store = create_vector_store(documents, api_key)
    return sitemap_vector_store.as_retriever(search_type="similarity", search_kwargs={"k": k})

def save_vector_store(vector_store: FAISS, path: str):
    """
    Save a FAISS vector store to disk.
    
    Args:
        vector_store: FAISS vector store to save
        path: Directory path to save the vector store
    """
    os.makedirs(path, exist_ok=True)
    vector_store.save_local(path)
    logger.info(f"Vector store saved to {path}")

def load_vector_store(path: str, api_key: str, embeddings_model: str = "text-embedding-3-small") -> FAISS:
    """
    Load a FAISS vector store from disk.
    
    Args:
        path: Directory path containing the saved vector store
        api_key: OpenAI API key
        embeddings_model: OpenAI embeddings model to use
    
    Returns:
        Loaded FAISS vector store
    """
    embeddings = OpenAIEmbeddings(model=embeddings_model, api_key=api_key)
    vector_store = FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
    logger.info(f"Vector store loaded from {path}")
    return vector_store

def get_retriever_from_saved_store(path: str, api_key: str, k: int = 4):
    """
    Get a retriever from a saved vector store.
    
    Args:
        path: Directory path containing the saved vector store
        api_key: OpenAI API key
        k: Number of documents to retrieve
    
    Returns:
        Retriever configured for similarity search
    """
    vector_store = load_vector_store(path, api_key)
    return vector_store.as_retriever(search_type="similarity", search_kwargs={"k": k})