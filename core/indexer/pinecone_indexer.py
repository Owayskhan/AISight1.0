import os
import logging
from typing import List, Optional, Dict, Any
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
import asyncio
from uuid import uuid4
from core.utils.brand_sanitizer import sanitize_brand_name, validate_namespace
from dotenv import load_dotenv


async def retry_async(func, max_retries=3, delay=1.0):
    """Simple retry wrapper for async functions"""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Retry {attempt + 1}/{max_retries} failed: {str(e)}")
            await asyncio.sleep(delay * (attempt + 1))


class ResilientPineconeRetriever:
    """Wrapper around Pinecone retriever that can handle session closures"""
    
    def __init__(self, manager, brand_name, openai_api_key, k=4, search_type="similarity"):
        self.manager = manager
        self.brand_name = brand_name
        self.openai_api_key = openai_api_key
        self.k = k
        self.search_type = search_type
        self._retriever = None
        self._vector_store = None
    
    async def _get_retriever(self):
        """Get or create the underlying retriever with caching"""
        if self._retriever is None or self._vector_store is None:
            # Manually create the retriever to avoid recursion
            namespace = sanitize_brand_name(self.brand_name)
            
            if not self.manager._index:
                await self.manager.initialize_index()
            
            embeddings = self.manager.get_embeddings(self.openai_api_key)
            
            # Cache the vector store to avoid recreating it every time
            self._vector_store = PineconeVectorStore(
                index=self.manager._index,
                embedding=embeddings,
                namespace=namespace
            )
            
            self._retriever = self._vector_store.as_retriever(
                search_type=self.search_type,
                search_kwargs={"k": self.k}
            )
        return self._retriever
    
    async def ainvoke(self, query):
        """Invoke retriever with automatic session recovery"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                retriever = await self._get_retriever()
                return await retriever.ainvoke(query)
            except Exception as e:
                if "Session is closed" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Session closed during retrieval, recreating retriever (attempt {attempt + 1}/{max_retries})")
                    # Reset both the manager and local retriever/vector store
                    self.manager._reset_connection()
                    self._retriever = None
                    self._vector_store = None
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                else:
                    raise

load_dotenv(override=True)
logger = logging.getLogger(__name__)


class PineconeIndexManager:
    """Manages Pinecone index and namespace operations for brand-specific vector storage"""
    
    def __init__(self, api_key: Optional[str] = None, index_name: Optional[str] = None):
        """
        Initialize Pinecone index manager
        
        Args:
            api_key: Pinecone API key (defaults to env var)
            index_name: Pinecone index name (defaults to env var)
        """
        from core.config import ModelConfig, PineconeConfig
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.index_name = index_name or os.getenv("PINECONE_INDEX_NAME", PineconeConfig.DEFAULT_INDEX_NAME)
        self.embedding_model = ModelConfig.EMBEDDING_MODEL
        self.embedding_dim = ModelConfig.EMBEDDING_DIMENSIONS
        
        if not self.api_key:
            raise ValueError("Pinecone API key is required. Set PINECONE_API_KEY environment variable.")
        
        self._pc = None
        self._index = None
        self._embeddings = None
        self._initialized = False
    
    def _get_pinecone_client(self):
        """Get or create Pinecone client - create fresh each time to avoid session issues"""
        # Instead of caching, create a fresh client each time to avoid session issues
        # This is less efficient but more reliable with async operations
        import httpx
        from core.config import TimeoutConfig, PineconeConfig
        return Pinecone(
            api_key=self.api_key,
            # Disable connection pooling entirely to avoid session issues
            httpx_client=httpx.Client(
                timeout=TimeoutConfig.PINECONE_OPERATION_TIMEOUT,
                limits=httpx.Limits(
                    max_keepalive_connections=PineconeConfig.MAX_KEEPALIVE_CONNECTIONS,   # Disable keep-alive
                    max_connections=PineconeConfig.MAX_CONNECTIONS,             # Single connection
                    keepalive_expiry=PineconeConfig.KEEPALIVE_EXPIRY          # No keep-alive
                )
            )
        )
    
    def _reset_connection(self):
        """Reset Pinecone connection - useful when session is closed"""
        self._pc = None
        self._index = None
        self._initialized = False
    
    async def initialize_index(self) -> None:
        """Initialize or create Pinecone index if it doesn't exist"""
        if self._initialized:
            return
            
        try:
            # Run synchronous Pinecone operations in thread pool
            loop = asyncio.get_event_loop()
            
            # Check if index exists with retry
            async def check_indexes():
                return await loop.run_in_executor(
                    None, lambda: [index.name for index in self._get_pinecone_client().list_indexes()]
                )
            existing_indexes = await retry_async(check_indexes)
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating new Pinecone index: {self.index_name}")
                
                # Create index with serverless spec (recommended for new projects)
                await loop.run_in_executor(
                    None, 
                    lambda: self._get_pinecone_client().create_index(
                        name=self.index_name,
                        dimension=self.embedding_dim,
                        metric="cosine",
                        spec=ServerlessSpec(
                            cloud=PineconeConfig.DEFAULT_CLOUD,
                            region=PineconeConfig.DEFAULT_REGION
                        )
                    )
                )
                
                # Wait for index to be ready
                logger.info("Waiting for index to be ready...")
                await asyncio.sleep(10)  # Use async sleep instead of blocking sleep
            
            # Connect to index with retry
            async def connect_index():
                return await loop.run_in_executor(
                    None, lambda: self._get_pinecone_client().Index(self.index_name)
                )
            self._index = await retry_async(connect_index)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index: {str(e)}")
            self._initialized = False
            # Reset connection on failure
            if "Session is closed" in str(e):
                self._reset_connection()
            raise
    
    def get_embeddings(self, openai_api_key: str) -> OpenAIEmbeddings:
        """Get or create OpenAI embeddings instance"""
        if not self._embeddings:
            self._embeddings = OpenAIEmbeddings(
                model=self.embedding_model,
                api_key=openai_api_key
            )
        return self._embeddings
    
    async def namespace_exists(self, brand_name: str) -> bool:
        """
        Check if a namespace exists for the given brand
        
        Args:
            brand_name: Original brand name
            
        Returns:
            True if namespace exists, False otherwise
        """
        try:
            if not self._index:
                await self.initialize_index()
            
            namespace = sanitize_brand_name(brand_name)
            
            # Query namespace to check if it has any vectors
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                None, lambda: self._index.describe_index_stats()
            )
            namespaces = stats.get('namespaces', {})
            
            # Check if namespace exists and has vectors
            return namespace in namespaces and namespaces[namespace]['vector_count'] > 0
            
        except Exception as e:
            logger.error(f"Error checking namespace existence for {brand_name}: {str(e)}")
            return False
    
    async def get_namespace_stats(self, brand_name: str) -> Dict[str, Any]:
        """
        Get statistics for a brand's namespace
        
        Args:
            brand_name: Original brand name
            
        Returns:
            Dictionary with namespace statistics
        """
        try:
            if not self._index:
                await self.initialize_index()
            
            namespace = sanitize_brand_name(brand_name)
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                None, lambda: self._index.describe_index_stats()
            )
            namespaces = stats.get('namespaces', {})
            
            if namespace in namespaces:
                return {
                    'namespace': namespace,
                    'vector_count': namespaces[namespace]['vector_count'],
                    'exists': True
                }
            else:
                return {
                    'namespace': namespace,
                    'vector_count': 0,
                    'exists': False
                }
                
        except Exception as e:
            logger.error(f"Error getting namespace stats for {brand_name}: {str(e)}")
            return {'namespace': sanitize_brand_name(brand_name), 'vector_count': 0, 'exists': False, 'error': str(e)}
    
    async def create_vector_store(
        self,
        brand_name: str,
        documents: List[Document],
        openai_api_key: str,
        batch_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> PineconeVectorStore:
        """
        Create or update a Pinecone vector store for a brand
        
        Args:
            brand_name: Original brand name
            documents: List of documents to index
            openai_api_key: OpenAI API key for embeddings
            batch_size: Batch size for embedding operations
            progress_callback: Optional progress callback
            
        Returns:
            PineconeVectorStore instance
        """
        if not documents:
            raise ValueError("No documents to index")
        
        try:
            if not self._index:
                await self.initialize_index()
            
            namespace = sanitize_brand_name(brand_name)
            logger.info(f"Creating vector store for brand '{brand_name}' in namespace '{namespace}'")
            
            # Get embeddings instance
            embeddings = self.get_embeddings(openai_api_key)
            
            # Create vector store with namespace
            vector_store = PineconeVectorStore(
                index=self._index,
                embedding=embeddings,
                namespace=namespace
            )
            
            # Process documents in batches
            total_docs = len(documents)
            logger.info(f"Indexing {total_docs} documents in batches of {batch_size}")
            
            for i in range(0, total_docs, batch_size):
                batch = documents[i:i + batch_size]
                batch_uuids = [str(uuid4()) for _ in batch]
                
                # Progress update
                current_batch = i // batch_size + 1
                total_batches = (total_docs + batch_size - 1) // batch_size
                
                logger.info(f"Processing batch {current_batch}/{total_batches} ({len(batch)} documents)")
                
                if progress_callback:
                    progress_callback(
                        current=i,
                        total=total_docs,
                        message=f"Indexing to Pinecone batch {current_batch}/{total_batches}"
                    )
                
                # Add documents to vector store with retry logic for session recovery
                max_retries = 3
                batch_success = False
                
                for attempt in range(max_retries):
                    try:
                        await vector_store.aadd_documents(documents=batch, ids=batch_uuids)
                        batch_success = True
                        break
                    except Exception as e:
                        if "Session is closed" in str(e) and attempt < max_retries - 1:
                            logger.warning(f"Session closed during indexing batch {current_batch}, recreating vector store (attempt {attempt + 1}/{max_retries})")
                            
                            # Reset connection and recreate vector store
                            self._reset_connection()
                            await self.initialize_index()
                            
                            # Recreate vector store with fresh connection
                            embeddings = self.get_embeddings(openai_api_key)
                            vector_store = PineconeVectorStore(
                                index=self._index,
                                embedding=embeddings,
                                namespace=namespace
                            )
                            
                            # Wait before retry with exponential backoff
                            await asyncio.sleep(2.0 * (attempt + 1))
                            continue
                        else:
                            logger.error(f"Failed to index batch {current_batch} after {attempt + 1} attempts: {str(e)}")
                            raise
                
                if not batch_success:
                    raise RuntimeError(f"Failed to index batch {current_batch} after {max_retries} attempts")
                
                # Adaptive delay between batches - longer delays for larger datasets
                if i + batch_size < total_docs:
                    delay = 0.1 if total_docs < 1000 else 0.3
                    await asyncio.sleep(delay)
            
            logger.info(f"✅ Successfully indexed {total_docs} documents to namespace '{namespace}'")
            
            if progress_callback:
                progress_callback(
                    current=total_docs,
                    total=total_docs,
                    message="Pinecone indexing completed"
                )
            
            return vector_store
            
        except Exception as e:
            logger.error(f"Failed to create vector store for {brand_name}: {str(e)}")
            raise
    
    async def get_retriever(
        self,
        brand_name: str,
        openai_api_key: str,
        k: int = 4,
        search_type: str = "similarity"
    ):
        """
        Get a retriever for an existing brand namespace
        
        Args:
            brand_name: Original brand name
            openai_api_key: OpenAI API key for embeddings
            k: Number of documents to retrieve
            search_type: Type of search to perform
            
        Returns:
            Retriever instance
        """
        try:
            if not self._index:
                await self.initialize_index()
            
            namespace = sanitize_brand_name(brand_name)
            
            # Verify namespace exists
            if not await self.namespace_exists(brand_name):
                raise ValueError(f"Namespace for brand '{brand_name}' does not exist")
            
            # Get embeddings instance
            embeddings = self.get_embeddings(openai_api_key)
            
            # Create vector store with existing namespace
            vector_store = PineconeVectorStore(
                index=self._index,
                embedding=embeddings,
                namespace=namespace
            )
            
            logger.info(f"Retrieved vector store for brand '{brand_name}' from namespace '{namespace}'")
            
            # Return resilient retriever wrapper instead of direct retriever
            return ResilientPineconeRetriever(
                manager=self,
                brand_name=brand_name,
                openai_api_key=openai_api_key,
                k=k,
                search_type=search_type
            )
            
        except Exception as e:
            logger.error(f"Failed to get retriever for {brand_name}: {str(e)}")
            # Reset connection and retry once if session is closed
            if "Session is closed" in str(e):
                logger.info("Attempting to reset Pinecone connection and retry...")
                self._reset_connection()
                try:
                    # Retry once after resetting connection
                    await self.initialize_index()
                    
                    namespace = sanitize_brand_name(brand_name)
                    embeddings = self.get_embeddings(openai_api_key)
                    
                    vector_store = PineconeVectorStore(
                        index=self._index,
                        embedding=embeddings,
                        namespace=namespace
                    )
                    
                    return vector_store.as_retriever(
                        search_type=search_type,
                        search_kwargs={"k": k}
                    )
                except Exception as retry_e:
                    logger.error(f"Retry also failed: {str(retry_e)}")
                    raise retry_e
            raise
    
    async def delete_namespace(self, brand_name: str) -> bool:
        """
        Delete all vectors in a brand's namespace
        
        Args:
            brand_name: Original brand name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._index:
                await self.initialize_index()
            
            namespace = sanitize_brand_name(brand_name)
            
            # Delete all vectors in the namespace
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self._index.delete(delete_all=True, namespace=namespace)
            )
            
            logger.info(f"Deleted namespace '{namespace}' for brand '{brand_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete namespace for {brand_name}: {str(e)}")
            return False


# Create fresh instance per request to avoid shared state issues
def get_pinecone_manager() -> PineconeIndexManager:
    """
    Create a new Pinecone manager instance per request.

    Note: We intentionally create fresh instances instead of using a singleton
    to avoid race conditions in concurrent async operations. Each request gets
    its own isolated manager instance, eliminating shared mutable state issues.
    """
    return PineconeIndexManager()


async def namespace_exists(brand_name: str) -> bool:
    """Convenience function to check if namespace exists"""
    manager = get_pinecone_manager()
    return await manager.namespace_exists(brand_name)


async def get_brand_namespace_stats(brand_name: str) -> Dict[str, Any]:
    """Convenience function to get namespace statistics"""
    manager = get_pinecone_manager()
    return await manager.get_namespace_stats(brand_name)