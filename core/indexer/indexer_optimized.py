import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from core.website_crawler.crawler import load_sitemap_documents, load_sitemap_documents_parallel
from core.indexer.pinecone_indexer import get_pinecone_manager, namespace_exists, get_brand_namespace_stats
from typing import List, Optional
from langchain.schema import Document
import asyncio
import logging

logger = logging.getLogger(__name__)


async def create_vector_store_optimized(
    sitemap_docs: List[Document], 
    api_key: str,
    batch_size: int = 100,
    progress_callback: Optional[callable] = None
) -> FAISS:
    """
    Create vector store with optimized batch processing
    
    Args:
        sitemap_docs: List of documents to embed
        api_key: OpenAI API key
        batch_size: Number of documents to embed in each batch
        progress_callback: Optional callback for progress updates
    """
    if not sitemap_docs:
        raise ValueError("No documents to index")
    
    from core.config import ModelConfig
    embeddings = OpenAIEmbeddings(model=ModelConfig.EMBEDDING_MODEL, api_key=api_key)
    
    # Get embedding dimensions by embedding a sample
    logger.info("Getting embedding dimensions...")
    sample_embedding = await embeddings.aembed_query("hello world")
    embedding_dim = len(sample_embedding)
    
    # Create FAISS index
    index = faiss.IndexFlatL2(embedding_dim)
    
    # Initialize vector store
    vector_store = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )
    
    # Process documents in batches
    total_docs = len(sitemap_docs)
    logger.info(f"Processing {total_docs} documents in batches of {batch_size}...")
    
    from uuid import uuid4
    
    for i in range(0, total_docs, batch_size):
        batch = sitemap_docs[i:i + batch_size]
        batch_uuids = [str(uuid4()) for _ in batch]
        
        # Progress update
        current_batch = i // batch_size + 1
        total_batches = (total_docs + batch_size - 1) // batch_size
        
        logger.info(f"Processing batch {current_batch}/{total_batches} ({len(batch)} documents)")
        
        if progress_callback:
            progress_callback(
                current=i,
                total=total_docs,
                message=f"Indexing batch {current_batch}/{total_batches}"
            )
        
        # Add documents to vector store (this internally batches the embedding calls)
        await vector_store.aadd_documents(documents=batch, ids=batch_uuids)
        
        # Small delay between batches to avoid rate limiting
        if i + batch_size < total_docs:
            await asyncio.sleep(0.1)
    
    logger.info(f"✅ Successfully indexed {total_docs} documents")
    
    if progress_callback:
        progress_callback(
            current=total_docs,
            total=total_docs,
            message="Indexing completed"
        )
    
    return vector_store



# Pinecone-based functions for persistent vector storage

async def get_smart_retriever(
    brand_name: str,
    sitemap_url: str,
    api_key: str,
    k: int = 4,
    batch_size: int = 100,
    use_pinecone: bool = True,
    force_reindex: bool = False,
    use_parallel_sitemap: bool = True,
    progress_callback: Optional[callable] = None
):
    """
    Smart retriever that uses Pinecone for persistent storage of brand sitemaps
    
    Args:
        brand_name: Brand name for namespace identification
        sitemap_url: URL of the sitemap
        api_key: OpenAI API key
        k: Number of documents to retrieve
        batch_size: Batch size for embedding
        use_pinecone: Whether to use Pinecone (required for sitemaps, default True)
        force_reindex: Force re-indexing even if namespace exists
        use_parallel_sitemap: Use parallel sitemap loading
        progress_callback: Optional callback for progress updates
    """
    if not use_pinecone:
        raise ValueError("Pinecone is required for this system. Please set use_pinecone=True or configure Pinecone API key.")
    
    try:
        # Check if brand namespace already exists
        if progress_callback:
            progress_callback(
                current=0,
                total=100,
                message="Checking existing brand index..."
            )
        
        namespace_stats = await get_brand_namespace_stats(brand_name)
        logger.info(f"Namespace stats for '{brand_name}': {namespace_stats}")
        
        if namespace_stats['exists'] and namespace_stats['vector_count'] > 0 and not force_reindex:
            # Use existing Pinecone namespace
            logger.info(f"✅ Found existing index for '{brand_name}' with {namespace_stats['vector_count']} vectors")
            logger.info("🚀 Skipping indexing - using cached vectors (major time savings!)")
            
            if progress_callback:
                progress_callback(
                    current=100,
                    total=100,
                    message="Using existing brand index"
                )
            
            # Get retriever from existing namespace
            pinecone_manager = get_pinecone_manager()
            return await pinecone_manager.get_retriever(
                brand_name=brand_name,
                openai_api_key=api_key,
                k=k
            )
        
        else:
            # Need to index documents
            if force_reindex and namespace_stats['exists']:
                logger.info(f"🔄 Force re-indexing requested for '{brand_name}'")
            else:
                logger.info(f"📥 Creating new index for '{brand_name}'")
            
            if progress_callback:
                progress_callback(
                    current=10,
                    total=100,
                    message="Loading sitemap documents..."
                )
            
            # Load documents (URLs only, content loaded during retrieval)
            if use_parallel_sitemap:
                logger.info("Loading sitemap documents with parallel processing...")
                sitemap_docs = await load_sitemap_documents_parallel(sitemap_url)
            else:
                logger.info("Loading sitemap documents with sequential processing...")
                sitemap_docs = load_sitemap_documents(sitemap_url)
            
            logger.info(f"Loaded {len(sitemap_docs)} unique URLs from sitemap")
            
            if progress_callback:
                progress_callback(
                    current=30,
                    total=100,
                    message=f"Creating Pinecone index for {len(sitemap_docs)} documents..."
                )
            
            # Create Pinecone vector store
            pinecone_manager = get_pinecone_manager()
            
            # Wrap progress callback to adjust scale
            def pinecone_progress_callback(current, total, message):
                if progress_callback:
                    # Scale progress from 30-95%
                    scaled_current = 30 + int((current / total) * 65)
                    progress_callback(scaled_current, 100, message)
            
            vector_store = await pinecone_manager.create_vector_store(
                brand_name=brand_name,
                documents=sitemap_docs,
                openai_api_key=api_key,
                batch_size=batch_size,
                progress_callback=pinecone_progress_callback
            )
            
            if progress_callback:
                progress_callback(
                    current=100,
                    total=100,
                    message="Pinecone indexing completed"
                )
            
            return vector_store.as_retriever(search_type="similarity", search_kwargs={"k": k})
    
    except Exception as e:
        logger.error(f"❌ Pinecone indexing failed for '{brand_name}': {str(e)}")
        raise RuntimeError(f"Failed to create Pinecone index for brand '{brand_name}': {str(e)}")


async def check_brand_index_status(brand_name: str) -> dict:
    """
    Check the indexing status for a brand
    
    Args:
        brand_name: Brand name to check
        
    Returns:
        Dictionary with status information
    """
    try:
        stats = await get_brand_namespace_stats(brand_name)
        
        return {
            "brand_name": brand_name,
            "namespace": stats.get("namespace"),
            "indexed": stats.get("exists", False),
            "vector_count": stats.get("vector_count", 0),
            "status": "indexed" if stats.get("exists") else "not_indexed",
            "error": stats.get("error")
        }
    
    except Exception as e:
        return {
            "brand_name": brand_name,
            "indexed": False,
            "vector_count": 0,
            "status": "error",
            "error": str(e)
        }