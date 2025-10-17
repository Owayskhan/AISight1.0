"""
Configuration constants for the conversions-digital citation analysis API.

This file contains all hardcoded values that were previously scattered throughout
the codebase, providing a centralized location for configuration management.
"""

# Model Configuration
class ModelConfig:
    """AI Model configurations"""
    # OpenAI Models
    EMBEDDING_MODEL = "text-embedding-3-small"
    GPT_4_MODEL = "gpt-4"
    GPT_4O_MINI_MODEL = "gpt-4o-mini"
    
    # Model parameters
    EMBEDDING_DIMENSIONS = 1536
    DEFAULT_TEMPERATURE = 0
    
    # Model selection for different tasks
    QUERY_GENERATION_MODEL = GPT_4O_MINI_MODEL  # Fast and cost-effective for parallel generation
    BRAND_PROFILING_MODEL = GPT_4O_MINI_MODEL  # Cost-effective for simple tasks
    CITATION_ANALYSIS_MODEL = GPT_4O_MINI_MODEL  # Structured output tasks


# Timeout Configuration
class TimeoutConfig:
    """Timeout settings for various operations"""
    HTTP_REQUEST_TIMEOUT = 10.0  # seconds
    PINECONE_OPERATION_TIMEOUT = 30.0  # seconds
    WEB_SCRAPING_TIMEOUT = 10.0  # seconds
    LLM_REQUEST_TIMEOUT = 60.0  # seconds
    

# Batch Processing Configuration
class BatchConfig:
    """Batch processing and concurrency limits"""
    DEFAULT_INDEXING_BATCH_SIZE = 500
    MIN_INDEXING_BATCH_SIZE = 10
    MAX_INDEXING_BATCH_SIZE = 1000
    
    DEFAULT_QUERY_BATCH_SIZE = 30
    MIN_QUERY_BATCH_SIZE = 6
    MAX_QUERY_BATCH_SIZE = 100
    
    # Concurrency limits
    MAX_CONCURRENT_DOWNLOADS = 5
    MAX_CONCURRENT_SITEMAP_PROCESSING = 50
    MAX_CONCURRENT_QUERIES = 20
    MAX_CONCURRENT_CONTEXT_DOWNLOADS = 25   # Conservative for maximum stability
    VECTOR_QUERY_BATCH_SIZE = 15  # Batch size for parallel vector store queries
    
    # API-specific concurrency limits for LLM calls
    MAX_CONCURRENT_OPENAI_REQUESTS = 50    # Conservative limit for OpenAI (500/min rate limit)
    MAX_CONCURRENT_GEMINI_REQUESTS = 15    # Conservative limit for Gemini (60/min rate limit)
    MAX_CONCURRENT_PERPLEXITY_REQUESTS = 8 # Conservative limit for Perplexity (varies by tier)

    # Perplexity tier-specific rate limits (requests per minute)
    # Tier 0: 50 req/min, Tier 1+: higher limits
    # Set via environment variable: PERPLEXITY_RPM (default: 50 for tier 0)
    PERPLEXITY_RPM = 50  # Can be overridden via env var
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0  # seconds
    RETRY_EXPONENTIAL_BASE = 2.0


# Delay Configuration
class DelayConfig:
    """Delay settings for rate limiting and performance optimization"""
    BATCH_PROCESSING_DELAY = 0.1  # seconds between batches
    LARGE_DATASET_DELAY = 0.3  # seconds for datasets >= 1000 items
    PINECONE_QUERY_DELAY = 0.1  # seconds between Pinecone queries
    SESSION_RECOVERY_DELAY = 2.0  # seconds before retry on session closure
    

# Pinecone Configuration
class PineconeConfig:
    """Pinecone vector database settings"""
    DEFAULT_INDEX_NAME = "citation-analysis"
    DEFAULT_METRIC = "cosine"
    DEFAULT_CLOUD = "aws"
    DEFAULT_REGION = "us-east-1"
    
    # Namespace configuration
    NAMESPACE_PREFIX = "brand-"
    
    # Connection settings (optimized for concurrent async operations)
    MAX_KEEPALIVE_CONNECTIONS = 10  # Allow connection reuse for better performance
    MAX_CONNECTIONS = 20  # Support concurrent queries without blocking
    KEEPALIVE_EXPIRY = 300.0  # Keep connections alive for 5 minutes
    

# API Server Configuration
class ServerConfig:
    """FastAPI server configuration"""
    DEFAULT_HOST = "0.0.0.0"
    DEFAULT_PORT = 8000
    API_TITLE = "Citation Count API"
    API_VERSION = "1.0.0"
    

# Query Generation Configuration
class QueryConfig:
    """Query generation and intent classification settings"""
    # Intent types
    INTENT_TYPES = [
        "navigational",
        "informational", 
        "commercial",
        "transactional",
        "awareness",
        "consideration"
    ]
    
    # Free plan allowed intents
    FREE_PLAN_INTENTS = ["informational", "awareness"]
    
    # Personas
    PERSONAS = [
        "novice",
        "enthusiast", 
        "pro",
        "budget_shopper",
        "eco_conscious",
        "gift_buyer"
    ]
    

# Content Processing Configuration
class ContentConfig:
    """Content processing and chunking settings"""
    MAX_CONTENT_PREVIEW_LENGTH = 100  # characters for debug logging
    MAX_URL_LENGTH = 500  # characters for URL validation
    
    # Markdown header levels for document chunking
    MARKDOWN_HEADERS = [
        ("#", "Header 1"),
        ("##", "Header 2"), 
        ("###", "Header 3"),
        ("####", "Header 4"),
        ("#####", "Header 5"),
        ("######", "Header 6"),
    ]
    
    # Content limits for LLM processing
    MAX_PRODUCT_CONTENT_LENGTH = 3000  # characters


# Logging Configuration
class LoggingConfig:
    """Logging configuration"""
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DEFAULT_LOG_LEVEL = "INFO"
    

# Dataset Size Thresholds
class DatasetConfig:
    """Thresholds for different dataset processing strategies"""
    LARGE_DATASET_THRESHOLD = 1000  # documents
    SMALL_BATCH_DELAY_THRESHOLD = 1000  # documents
    

# Validation Limits
class ValidationConfig:
    """Input validation limits"""
    MIN_BRAND_NAME_LENGTH = 1
    MAX_BRAND_NAME_LENGTH = 100
    
    MIN_PRODUCT_CATEGORY_LENGTH = 1
    MAX_PRODUCT_CATEGORY_LENGTH = 100
    
    # URL validation
    MAX_URL_LENGTH = 2048
    VALID_URL_SCHEMES = ["http", "https"]


# Firecrawl Configuration (Deprecated)
class FirecrawlConfig:
    """Firecrawl API configuration for website crawling (DEPRECATED - use Crawl4AI)"""
    DEFAULT_TIMEOUT = 30.0  # seconds
    MAX_RETRIES = 2
    MAP_TIMEOUT = 60.0  # seconds for map operation (can take longer)

    # Enable/disable Firecrawl (fallback to traditional sitemap discovery if disabled)
    ENABLED = False  # Set to False to use Crawl4AI (default)


# Crawl4AI Configuration
class Crawl4AIConfig:
    """Crawl4AI configuration for website crawling"""
    DEFAULT_TIMEOUT = 30.0  # seconds
    MAX_RETRIES = 2

    # Enable/disable Crawl4AI
    ENABLED = True  # Set to True to use Crawl4AI (default method)


# Export all config classes for easy importing
__all__ = [
    'ModelConfig',
    'TimeoutConfig',
    'BatchConfig',
    'DelayConfig',
    'PineconeConfig',
    'ServerConfig',
    'QueryConfig',
    'ContentConfig',
    'LoggingConfig',
    'DatasetConfig',
    'ValidationConfig',
    'FirecrawlConfig',
    'Crawl4AIConfig'
]