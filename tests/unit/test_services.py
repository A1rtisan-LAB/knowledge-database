"""Unit tests for service layers."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from app.services import opensearch, redis, embeddings
from app.core.config import Settings


@pytest.mark.unit
class TestOpenSearchService:
    """Test OpenSearch service functions."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.opensearch_host = "localhost"
        settings.opensearch_port = 9200
        settings.opensearch_username = "admin"
        settings.opensearch_password = "admin"
        settings.opensearch_use_ssl = False
        settings.opensearch_verify_certs = False
        settings.opensearch_index_prefix = "test"
        return settings
    
    async def test_init_opensearch(self, mock_settings):
        """Test initializing OpenSearch."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.logger') as mock_logger:
                await opensearch.init_opensearch()
                mock_logger.info.assert_called_once()
        
    async def test_index_knowledge_item(self, mock_settings):
        """Test indexing a knowledge item."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.logger') as mock_logger:
                mock_item = Mock()
                mock_item.id = "123"
                await opensearch.index_knowledge_item(mock_item)
                mock_logger.info.assert_called_once()
        
    async def test_search_knowledge(self, mock_settings):
        """Test searching knowledge items."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.logger') as mock_logger:
                result = await opensearch.search_knowledge(
                    query="test query",
                    language="en",
                    organization_id="org123"
                )
                
                assert result['query'] == "test query"
                assert result['total'] == 0
                assert result['items'] == []
                mock_logger.info.assert_called_once()
        
    async def test_delete_from_index(self, mock_settings):
        """Test deleting from index."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.logger') as mock_logger:
                await opensearch.delete_from_index("item123")
                mock_logger.info.assert_called_once_with(
                    "Mock: Would delete knowledge item from index: item123"
                )
        
    async def test_get_opensearch_client(self, mock_settings):
        """Test getting OpenSearch client."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            client = opensearch.get_opensearch_client()
            assert client is None  # Mock implementation returns None


@pytest.mark.unit
class TestRedisService:
    """Test Redis caching service functions."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.redis_host = "localhost"
        settings.redis_port = 6379
        settings.redis_db = 0
        settings.redis_password = None
        settings.redis_cache_ttl = 3600
        settings.redis_url = "redis://localhost:6379/0"
        return settings
    
    @pytest.fixture
    async def mock_redis_client(self):
        """Create mock Redis client."""
        mock_client = AsyncMock()
        return mock_client
    
    async def test_init_redis(self, mock_settings, mock_redis_client):
        """Test initializing Redis."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                mock_redis_client.ping = AsyncMock()
                with patch('app.services.redis.logger') as mock_logger:
                    await redis.init_redis()
                    mock_redis_client.ping.assert_called_once()
                    mock_logger.info.assert_called_once_with("Redis connection established")
        
    async def test_get_redis_client(self, mock_settings):
        """Test getting Redis client."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.ConnectionPool') as mock_pool:
                with patch('app.services.redis.redis.Redis') as mock_redis:
                    # Reset global state
                    redis.redis_client = None
                    redis.redis_pool = None
                    
                    client = await redis.get_redis_client()
                    assert client is not None
                    mock_pool.from_url.assert_called_once()
        
    async def test_close_redis(self, mock_settings, mock_redis_client):
        """Test closing Redis connection."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            redis.redis_client = mock_redis_client
            redis.redis_pool = Mock()
            redis.redis_pool.disconnect = AsyncMock()
            
            await redis.close_redis()
            redis.redis_pool.disconnect.assert_called_once()
        
    async def test_init_redis_connection_error(self, mock_settings):
        """Test Redis initialization with connection error."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', side_effect=Exception("Connection failed")):
                with patch('app.services.redis.logger') as mock_logger:
                    await redis.init_redis()
                    mock_logger.error.assert_called_once()


@pytest.mark.unit
class TestEmbeddingService:
    """Test embedding generation service functions."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        settings.embedding_dimension = 384
        settings.embedding_batch_size = 32
        return settings
    
    def test_chunk_text(self, mock_settings):
        """Test text chunking."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            text = "This is sentence one. This is sentence two. This is sentence three."
            chunks = embeddings.chunk_text(text, max_length=50)
            
            assert len(chunks) >= 1
            assert all(len(chunk) <= 100 for chunk in chunks)
        
    def test_chunk_text_empty(self, mock_settings):
        """Test chunking empty text."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            chunks = embeddings.chunk_text("", max_length=50)
            assert chunks == []
        
    async def test_generate_embeddings(self, mock_settings):
        """Test generating embeddings for an item."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger') as mock_logger:
                mock_item = Mock()
                mock_item.id = "123"
                mock_item.content_ko = "Korean content"
                mock_item.content_en = "English content"
                
                result = await embeddings.generate_embeddings(mock_item)
                mock_logger.info.assert_called()
                assert result is not None
        
    def test_get_embedding_model(self, mock_settings):
        """Test getting embedding model."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.logger') as mock_logger:
                model = embeddings.get_embedding_model()
                assert model is None  # Mock implementation returns None
                mock_logger.info.assert_called_with("Mock: Using mock embedding model")
        
    def test_chunk_text_long(self, mock_settings):
        """Test chunking long text."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            long_text = "This is a long sentence. " * 100
            chunks = embeddings.chunk_text(long_text, max_length=100)
            
            assert len(chunks) > 1
            for chunk in chunks:
                assert len(chunk) <= 150  # Allow some overflow for complete sentences