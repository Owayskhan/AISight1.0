"""
Tests for pre-loaded content retrieval functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from langchain.schema import Document

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.queries.retriever import retrieve_queries_context, retrieve_queries_context_preloaded
from core.models.main import Queries, QueryItem
from core.website_crawler.crawler_enhanced import is_document_preloaded


class TestPreloadedRetrieval:
    """Test cases for pre-loaded content retrieval."""
    
    @pytest.fixture
    def sample_queries(self):
        """Create sample queries for testing."""
        return Queries(
            queries=[
                QueryItem(
                    query="test query 1",
                    intent="purchase",
                    sub_intent="compare",
                    persona="novice",
                    category="test",
                    expected_brand_relevance="high",
                    locale="en-US",
                    notes="Test query 1"
                ),
                QueryItem(
                    query="test query 2",
                    intent="research",
                    sub_intent="features",
                    persona="enthusiast",
                    category="test",
                    expected_brand_relevance="medium",
                    locale="en-US",
                    notes="Test query 2"
                )
            ]
        )
    
    @pytest.fixture
    def url_documents(self):
        """Create documents containing only URLs."""
        return [
            Document(
                page_content="https://example.com/page1",
                metadata={"source": "https://example.com/page1", "content_type": "url"}
            ),
            Document(
                page_content="https://example.com/page2",
                metadata={"source": "https://example.com/page2", "content_type": "url"}
            )
        ]
    
    @pytest.fixture
    def preloaded_documents(self):
        """Create documents with pre-loaded content."""
        return [
            Document(
                page_content="This is the full content of page 1 with lots of text about products.",
                metadata={"source": "https://example.com/page1", "content_type": "full_content"}
            ),
            Document(
                page_content="This is the full content of page 2 with information about services.",
                metadata={"source": "https://example.com/page2", "content_type": "full_content"}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_retrieve_queries_context_with_urls(self, sample_queries, url_documents):
        """Test retrieval with URL-only documents (traditional behavior)."""
        # Mock retriever
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke.return_value = url_documents
        
        # Mock WebBaseLoader
        with patch('core.queries.retriever.WebBaseLoader') as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load.return_value = [
                Document(
                    page_content="Loaded content from web",
                    metadata={"source": "https://example.com/page1"}
                )
            ]
            mock_loader_class.return_value = mock_loader
            
            # Call function with preloaded=False
            results = await retrieve_queries_context(sample_queries, mock_retriever, preloaded=False)
        
        # Verify results
        assert len(results) == 2
        assert mock_retriever.ainvoke.call_count == 2
        assert mock_loader_class.call_count == 4  # 2 queries * 2 documents each
    
    @pytest.mark.asyncio
    async def test_retrieve_queries_context_preloaded(self, sample_queries, preloaded_documents):
        """Test retrieval with pre-loaded documents."""
        # Mock retriever
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke.return_value = preloaded_documents
        
        # Call function with preloaded=True
        results = await retrieve_queries_context(sample_queries, mock_retriever, preloaded=True)
        
        # Verify results
        assert len(results) == 2
        assert mock_retriever.ainvoke.call_count == 2
        
        # Check that documents are passed through directly
        for i, result in enumerate(results):
            assert result["query"] == sample_queries.queries[i]
            assert result["context"] == preloaded_documents
    
    @pytest.mark.asyncio
    async def test_retrieve_queries_context_preloaded_convenience(self, sample_queries, preloaded_documents):
        """Test the convenience function for pre-loaded retrieval."""
        # Mock retriever
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke.return_value = preloaded_documents
        
        # Call convenience function
        results = await retrieve_queries_context_preloaded(sample_queries, mock_retriever)
        
        # Verify results
        assert len(results) == 2
        assert mock_retriever.ainvoke.call_count == 2
        
        # Check that it's equivalent to calling with preloaded=True
        for i, result in enumerate(results):
            assert result["query"] == sample_queries.queries[i]
            assert result["context"] == preloaded_documents
    
    def test_is_document_preloaded(self, url_documents, preloaded_documents):
        """Test document type detection."""
        # Test URL documents
        for doc in url_documents:
            assert not is_document_preloaded(doc)
        
        # Test pre-loaded documents
        for doc in preloaded_documents:
            assert is_document_preloaded(doc)
        
        # Test edge cases
        # Document with URL-like content but no metadata
        doc_no_metadata = Document(
            page_content="https://example.com/page",
            metadata={}
        )
        assert not is_document_preloaded(doc_no_metadata)
        
        # Document with long content
        doc_long_content = Document(
            page_content="This is a very long document " * 50,
            metadata={}
        )
        assert is_document_preloaded(doc_long_content)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])