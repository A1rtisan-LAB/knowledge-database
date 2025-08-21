"""Comprehensive unit tests for Embeddings service."""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Tuple
import logging

from app.services import embeddings
from app.core.config import Settings


@pytest.mark.unit
class TestEmbeddingService:
    """Comprehensive test suite for embedding generation service functions."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for embedding configuration."""
        settings = Mock(spec=Settings)
        settings.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        settings.embedding_dimension = 384
        settings.embedding_batch_size = 32
        settings.openai_api_key = "test-api-key"
        settings.embedding_provider = "openai"
        settings.embedding_cache_enabled = True
        settings.embedding_cache_ttl = 3600
        return settings
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return Mock(spec=logging.getLogger())
    
    @pytest.fixture
    def mock_knowledge_item(self):
        """Create a mock knowledge item with content."""
        item = Mock()
        item.id = "test-item-123"
        item.title_ko = "테스트 제목"
        item.title_en = "Test Title"
        item.content_ko = "이것은 한국어 테스트 콘텐츠입니다. 여러 문장이 포함되어 있습니다."
        item.content_en = "This is English test content. It contains multiple sentences."
        item.summary_ko = "한국어 요약"
        item.summary_en = "English summary"
        return item
    
    # Test: get_embedding_model
    def test_get_embedding_model_returns_none(self, mock_settings, mock_logger):
        """Test that get_embedding_model returns None in mock implementation."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                model = embeddings.get_embedding_model()
                assert model is None
                mock_logger.info.assert_called_once_with("Mock: Using mock embedding model")
    
    def test_get_embedding_model_multiple_calls(self, mock_settings, mock_logger):
        """Test multiple calls to get_embedding_model."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                # Multiple calls should all return None
                for _ in range(5):
                    model = embeddings.get_embedding_model()
                    assert model is None
                
                assert mock_logger.info.call_count == 5
    
    # Test: chunk_text
    def test_chunk_text_basic(self, mock_settings):
        """Test basic text chunking."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            text = "This is sentence one. This is sentence two. This is sentence three."
            chunks = embeddings.chunk_text(text, max_length=50)
            
            assert len(chunks) >= 1
            assert all(isinstance(chunk, str) for chunk in chunks)
            assert all(len(chunk) <= 100 for chunk in chunks)  # Allow some overflow
    
    def test_chunk_text_empty(self, mock_settings):
        """Test chunking empty text."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            chunks = embeddings.chunk_text("", max_length=50)
            assert chunks == []
    
    def test_chunk_text_none(self, mock_settings):
        """Test chunking None text."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            chunks = embeddings.chunk_text(None, max_length=50)
            assert chunks == []
    
    def test_chunk_text_single_sentence(self, mock_settings):
        """Test chunking single sentence."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            text = "This is a single sentence without any periods"
            chunks = embeddings.chunk_text(text, max_length=100)
            
            assert len(chunks) == 1
            assert chunks[0].strip() == text + "."
    
    def test_chunk_text_long_text(self, mock_settings):
        """Test chunking very long text."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            # Create a long text with many sentences
            sentences = [f"This is sentence number {i}." for i in range(100)]
            long_text = " ".join(sentences)
            
            chunks = embeddings.chunk_text(long_text, max_length=100)
            
            assert len(chunks) > 1
            assert all(len(chunk) <= 150 for chunk in chunks)  # Allow overflow for complete sentences
            
            # Verify all content is preserved (roughly)
            total_chunk_length = sum(len(chunk) for chunk in chunks)
            assert total_chunk_length >= len(long_text) * 0.9  # Allow for some variation
    
    def test_chunk_text_with_newlines(self, mock_settings):
        """Test chunking text with newlines."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
            chunks = embeddings.chunk_text(text, max_length=50)
            
            assert len(chunks) >= 1
            # Check that newlines are handled properly
            for chunk in chunks:
                assert "\n\n" not in chunk  # Double newlines should be replaced
    
    def test_chunk_text_korean(self, mock_settings):
        """Test chunking Korean text."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            text = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
            chunks = embeddings.chunk_text(text, max_length=50)
            
            assert len(chunks) >= 1
            assert all(isinstance(chunk, str) for chunk in chunks)
    
    def test_chunk_text_mixed_language(self, mock_settings):
        """Test chunking mixed language text."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            text = "This is English. 이것은 한국어입니다. Mixed content here."
            chunks = embeddings.chunk_text(text, max_length=50)
            
            assert len(chunks) >= 1
            assert all(isinstance(chunk, str) for chunk in chunks)
    
    def test_chunk_text_various_max_lengths(self, mock_settings):
        """Test chunking with various max lengths."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            text = "This is a test sentence. " * 10
            
            for max_length in [50, 100, 200, 512, 1024]:
                chunks = embeddings.chunk_text(text, max_length=max_length)
                assert all(len(chunk) <= max_length * 1.5 for chunk in chunks)  # Allow overflow
    
    def test_chunk_text_preserves_punctuation(self, mock_settings):
        """Test that chunking preserves punctuation."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            text = "Question? Exclamation! Normal. Colon: items; semicolon."
            chunks = embeddings.chunk_text(text, max_length=100)
            
            # Join chunks and check if special punctuation is preserved
            joined = " ".join(chunks)
            assert "?" in joined or "?." in joined
            assert "!" in joined or "!." in joined
    
    # Test: generate_embeddings
    async def test_generate_embeddings_success(self, mock_settings, mock_logger, mock_knowledge_item):
        """Test successful embedding generation."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                with patch('app.services.embeddings.np.random.randn') as mock_randn:
                    mock_randn.return_value = np.array([0.1] * 384)
                    
                    result = await embeddings.generate_embeddings(mock_knowledge_item)
                    
                    mock_logger.info.assert_called()
                    mock_logger.debug.assert_called()
                    assert mock_randn.called
    
    async def test_generate_embeddings_item_without_content(self, mock_settings, mock_logger):
        """Test embedding generation for item without content attributes."""
        item = Mock(spec=['id'])
        item.id = "test-123"
        
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                result = await embeddings.generate_embeddings(item)
                mock_logger.info.assert_called_once()
    
    async def test_generate_embeddings_korean_only(self, mock_settings, mock_logger):
        """Test embedding generation for Korean content only."""
        item = Mock(spec=['id', 'content_ko'])
        item.id = "test-123"
        item.content_ko = "한국어 콘텐츠입니다. 여러 문장이 있습니다."
        
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                with patch('app.services.embeddings.np.random.randn') as mock_randn:
                    mock_randn.return_value = np.array([0.1] * 384)
                    
                    result = await embeddings.generate_embeddings(item)
                    
                    # Should generate Korean embeddings only
                    debug_calls = [call for call in mock_logger.debug.call_args_list 
                                  if "Korean" in str(call)]
                    assert len(debug_calls) > 0
    
    async def test_generate_embeddings_english_only(self, mock_settings, mock_logger):
        """Test embedding generation for English content only."""
        item = Mock(spec=['id', 'content_en'])
        item.id = "test-123"
        item.content_en = "This is English content. Multiple sentences here."
        
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                with patch('app.services.embeddings.np.random.randn') as mock_randn:
                    mock_randn.return_value = np.array([0.1] * 384)
                    
                    result = await embeddings.generate_embeddings(item)
                    
                    # Should generate English embeddings only
                    debug_calls = [call for call in mock_logger.debug.call_args_list 
                                  if "English" in str(call)]
                    assert len(debug_calls) > 0
    
    async def test_generate_embeddings_long_content(self, mock_settings, mock_logger):
        """Test embedding generation for very long content."""
        item = Mock()
        item.id = "test-123"
        item.content_ko = "한국어 문장. " * 100  # Long Korean content
        item.content_en = "English sentence. " * 100  # Long English content
        
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                with patch('app.services.embeddings.np.random.randn') as mock_randn:
                    mock_randn.return_value = np.array([0.1] * 384)
                    
                    result = await embeddings.generate_embeddings(item)
                    
                    # Should generate multiple embeddings for chunks
                    assert mock_logger.debug.call_count > 2
    
    async def test_generate_embeddings_exception_handling(self, mock_settings, mock_logger):
        """Test exception handling during embedding generation."""
        item = Mock()
        item.id = "test-123"
        item.content_en = "Test content"
        
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                with patch('app.services.embeddings.chunk_text', side_effect=Exception("Chunking failed")):
                    result = await embeddings.generate_embeddings(item)
                    
                    # Should log error
                    mock_logger.error.assert_called_once()
                    assert "Failed to generate embeddings" in mock_logger.error.call_args[0][0]
    
    async def test_generate_embeddings_empty_content(self, mock_settings, mock_logger):
        """Test embedding generation for empty content."""
        item = Mock()
        item.id = "test-123"
        item.content_ko = ""
        item.content_en = ""
        
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                result = await embeddings.generate_embeddings(item)
                
                # Should handle empty content gracefully
                mock_logger.info.assert_called()
                # No debug calls for empty chunks
                assert mock_logger.debug.call_count == 0
    
    # Test: compute_similarity
    def test_compute_similarity_identical_vectors(self, mock_settings):
        """Test similarity computation for identical vectors."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            vec = [0.1, 0.2, 0.3, 0.4, 0.5]
            similarity = embeddings.compute_similarity(vec, vec)
            
            # Identical vectors should have similarity of 1.0
            assert abs(similarity - 1.0) < 0.0001
    
    def test_compute_similarity_orthogonal_vectors(self, mock_settings):
        """Test similarity computation for orthogonal vectors."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            vec1 = [1.0, 0.0, 0.0]
            vec2 = [0.0, 1.0, 0.0]
            
            similarity = embeddings.compute_similarity(vec1, vec2)
            
            # Orthogonal vectors should have similarity of 0
            assert abs(similarity) < 0.0001
    
    def test_compute_similarity_opposite_vectors(self, mock_settings):
        """Test similarity computation for opposite vectors."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            vec1 = [1.0, 1.0, 1.0]
            vec2 = [-1.0, -1.0, -1.0]
            
            similarity = embeddings.compute_similarity(vec1, vec2)
            
            # Opposite vectors should have similarity of -1
            assert abs(similarity + 1.0) < 0.0001
    
    def test_compute_similarity_zero_vector(self, mock_settings):
        """Test similarity computation with zero vector."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            vec1 = [0.0, 0.0, 0.0]
            vec2 = [1.0, 1.0, 1.0]
            
            similarity = embeddings.compute_similarity(vec1, vec2)
            
            # Zero vector should return 0 similarity
            assert similarity == 0.0
    
    def test_compute_similarity_both_zero_vectors(self, mock_settings):
        """Test similarity computation with both zero vectors."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            vec1 = [0.0, 0.0, 0.0]
            vec2 = [0.0, 0.0, 0.0]
            
            similarity = embeddings.compute_similarity(vec1, vec2)
            
            # Both zero vectors should return 0
            assert similarity == 0.0
    
    def test_compute_similarity_high_dimensional(self, mock_settings):
        """Test similarity computation for high-dimensional vectors."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            # Create 384-dimensional vectors (typical embedding size)
            vec1 = np.random.randn(384).tolist()
            vec2 = np.random.randn(384).tolist()
            
            similarity = embeddings.compute_similarity(vec1, vec2)
            
            # Similarity should be between -1 and 1
            assert -1.0 <= similarity <= 1.0
    
    def test_compute_similarity_normalized_vectors(self, mock_settings):
        """Test similarity with pre-normalized vectors."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            # Create normalized vectors
            vec1 = np.array([0.6, 0.8, 0.0])
            vec2 = np.array([0.8, 0.6, 0.0])
            
            similarity = embeddings.compute_similarity(vec1.tolist(), vec2.tolist())
            
            # Should compute correct cosine similarity
            expected = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
            assert abs(similarity - expected) < 0.0001
    
    # Test: find_similar_items
    async def test_find_similar_items_basic(self, mock_settings, mock_logger):
        """Test finding similar items."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                results = await embeddings.find_similar_items(
                    text="test query",
                    language="en",
                    limit=10
                )
                
                assert results == []
                mock_logger.info.assert_called_once()
                assert "Would find similar items" in mock_logger.info.call_args[0][0]
    
    async def test_find_similar_items_korean(self, mock_settings, mock_logger):
        """Test finding similar items with Korean text."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                results = await embeddings.find_similar_items(
                    text="한국어 검색 쿼리",
                    language="ko",
                    limit=5
                )
                
                assert results == []
                assert isinstance(results, list)
                mock_logger.info.assert_called_once()
    
    async def test_find_similar_items_long_text(self, mock_settings, mock_logger):
        """Test finding similar items with long text."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                long_text = "This is a very long query. " * 20
                results = await embeddings.find_similar_items(
                    text=long_text,
                    language="en",
                    limit=20
                )
                
                assert results == []
                # Should truncate in log message
                assert "..." in mock_logger.info.call_args[0][0]
    
    async def test_find_similar_items_empty_text(self, mock_settings, mock_logger):
        """Test finding similar items with empty text."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                results = await embeddings.find_similar_items(
                    text="",
                    language="en"
                )
                
                assert results == []
                mock_logger.info.assert_called_once()
    
    async def test_find_similar_items_various_limits(self, mock_settings, mock_logger):
        """Test finding similar items with various limits."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                for limit in [1, 5, 10, 50, 100]:
                    results = await embeddings.find_similar_items(
                        text="test",
                        limit=limit
                    )
                    assert results == []
                
                assert mock_logger.info.call_count == 5
    
    # Edge cases and performance tests
    async def test_concurrent_embedding_generation(self, mock_settings, mock_logger):
        """Test concurrent embedding generation."""
        import asyncio
        
        items = [Mock(id=f"item-{i}", content_en=f"Content {i}") for i in range(10)]
        
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger', mock_logger):
                with patch('app.services.embeddings.np.random.randn') as mock_randn:
                    mock_randn.return_value = np.array([0.1] * 384)
                    
                    # Generate embeddings concurrently
                    tasks = [embeddings.generate_embeddings(item) for item in items]
                    results = await asyncio.gather(*tasks)
                    
                    assert len(results) == 10
                    assert mock_logger.info.call_count == 10
    
    def test_chunk_text_special_characters(self, mock_settings):
        """Test chunking text with special characters."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            text = "Test with émojis 😀. Unicode ñ characters. Special $ymbols @#%."
            chunks = embeddings.chunk_text(text, max_length=50)
            
            assert len(chunks) >= 1
            # Original content should be preserved
            joined = "".join(chunks).replace(". .", ".")
            assert "😀" in joined or "émojis" in joined
            assert "ñ" in joined
    
    def test_compute_similarity_numerical_stability(self, mock_settings):
        """Test numerical stability of similarity computation."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            # Very small values
            vec1 = [1e-10, 1e-10, 1e-10]
            vec2 = [1e-10, 1e-10, 1e-10]
            similarity = embeddings.compute_similarity(vec1, vec2)
            assert abs(similarity - 1.0) < 0.01 or similarity == 0.0
            
            # Very large values
            vec1 = [1e10, 1e10, 1e10]
            vec2 = [1e10, 1e10, 1e10]
            similarity = embeddings.compute_similarity(vec1, vec2)
            assert abs(similarity - 1.0) < 0.0001
            
            # Mixed magnitudes
            vec1 = [1e-5, 1e5, 1.0]
            vec2 = [1e5, 1e-5, 1.0]
            similarity = embeddings.compute_similarity(vec1, vec2)
            assert -1.0 <= similarity <= 1.0