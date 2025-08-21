"""Comprehensive tests for service layers."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List
import json
import numpy as np
from uuid import uuid4

from app.services import opensearch, redis, embeddings, search
from app.core.config import Settings
from app.models.knowledge_item import KnowledgeItem, ContentType, ContentStatus


@pytest.mark.asyncio
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
        settings.opensearch_number_of_shards = 1
        settings.opensearch_number_of_replicas = 0
        return settings
    
    @pytest.fixture
    def mock_opensearch_client(self):
        """Create mock OpenSearch client."""
        client = Mock()
        client.indices = Mock()
        client.indices.exists = AsyncMock(return_value=True)
        client.indices.create = AsyncMock()
        client.indices.delete = AsyncMock()
        client.index = AsyncMock()
        client.search = AsyncMock()
        client.delete = AsyncMock()
        client.bulk = AsyncMock()
        return client
    
    async def test_init_opensearch(self, mock_settings):
        """Test initializing OpenSearch."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.logger') as mock_logger:
                await opensearch.init_opensearch()
                mock_logger.info.assert_called()
    
    async def test_create_index(self, mock_settings, mock_opensearch_client):
        """Test creating OpenSearch index."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.get_opensearch_client', return_value=mock_opensearch_client):
                index_name = "test_knowledge"
                
                # Index doesn't exist
                mock_opensearch_client.indices.exists.return_value = False
                
                await opensearch.create_index(index_name)
                
                mock_opensearch_client.indices.create.assert_called_once()
                call_args = mock_opensearch_client.indices.create.call_args
                assert call_args[1]['index'] == index_name
                assert 'body' in call_args[1]
    
    async def test_index_knowledge_item(self, mock_settings, mock_opensearch_client):
        """Test indexing a knowledge item."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.get_opensearch_client', return_value=mock_opensearch_client):
                mock_item = Mock(spec=KnowledgeItem)
                mock_item.id = uuid4()
                mock_item.title_en = "Test Title"
                mock_item.title_ko = "테스트 제목"
                mock_item.content_en = "Test content"
                mock_item.content_ko = "테스트 내용"
                mock_item.type = ContentType.GUIDE
                mock_item.status = ContentStatus.PUBLISHED
                mock_item.tags = ["test", "opensearch"]
                mock_item.category_id = uuid4()
                mock_item.created_at = datetime.now()
                mock_item.updated_at = datetime.now()
                mock_item.view_count = 0
                mock_item.helpful_count = 0
                mock_item.metadata = {}
                mock_item.embedding = [0.1] * 768  # Mock embedding
                
                await opensearch.index_knowledge_item(mock_item)
                
                mock_opensearch_client.index.assert_called_once()
                call_args = mock_opensearch_client.index.call_args
                assert str(mock_item.id) in str(call_args)
    
    async def test_search_knowledge(self, mock_settings, mock_opensearch_client):
        """Test searching knowledge items."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.get_opensearch_client', return_value=mock_opensearch_client):
                # Mock search response
                mock_opensearch_client.search.return_value = {
                    "hits": {
                        "total": {"value": 2},
                        "hits": [
                            {
                                "_id": str(uuid4()),
                                "_score": 1.5,
                                "_source": {
                                    "title_en": "Result 1",
                                    "content_en": "Content 1"
                                }
                            },
                            {
                                "_id": str(uuid4()),
                                "_score": 1.2,
                                "_source": {
                                    "title_en": "Result 2",
                                    "content_en": "Content 2"
                                }
                            }
                        ]
                    },
                    "took": 15
                }
                
                result = await opensearch.search_knowledge(
                    query="test query",
                    language="en",
                    filters={"type": "guide"},
                    page=1,
                    limit=10
                )
                
                assert result["total"] == 2
                assert len(result["results"]) == 2
                assert result["took"] == 15
                mock_opensearch_client.search.assert_called_once()
    
    async def test_delete_from_index(self, mock_settings, mock_opensearch_client):
        """Test deleting item from index."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.get_opensearch_client', return_value=mock_opensearch_client):
                item_id = str(uuid4())
                
                await opensearch.delete_from_index(item_id)
                
                mock_opensearch_client.delete.assert_called_once()
                call_args = mock_opensearch_client.delete.call_args
                assert item_id in str(call_args)
    
    async def test_bulk_index(self, mock_settings, mock_opensearch_client):
        """Test bulk indexing items."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.get_opensearch_client', return_value=mock_opensearch_client):
                items = []
                for i in range(5):
                    mock_item = Mock(spec=KnowledgeItem)
                    mock_item.id = uuid4()
                    mock_item.title_en = f"Item {i}"
                    mock_item.content_en = f"Content {i}"
                    mock_item.type = ContentType.GUIDE
                    mock_item.status = ContentStatus.PUBLISHED
                    items.append(mock_item)
                
                mock_opensearch_client.bulk.return_value = {
                    "errors": False,
                    "items": [{"index": {"status": 201}} for _ in items]
                }
                
                result = await opensearch.bulk_index_items(items)
                
                assert result["errors"] is False
                mock_opensearch_client.bulk.assert_called_once()
    
    async def test_search_with_aggregations(self, mock_settings, mock_opensearch_client):
        """Test search with aggregations."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.get_opensearch_client', return_value=mock_opensearch_client):
                mock_opensearch_client.search.return_value = {
                    "hits": {"total": {"value": 10}, "hits": []},
                    "aggregations": {
                        "categories": {
                            "buckets": [
                                {"key": "cat1", "doc_count": 5},
                                {"key": "cat2", "doc_count": 3}
                            ]
                        },
                        "types": {
                            "buckets": [
                                {"key": "guide", "doc_count": 8},
                                {"key": "faq", "doc_count": 2}
                            ]
                        }
                    }
                }
                
                result = await opensearch.search_with_aggregations(
                    query="test",
                    aggs=["categories", "types"]
                )
                
                assert "aggregations" in result
                assert "categories" in result["aggregations"]
                assert len(result["aggregations"]["categories"]["buckets"]) == 2
    
    async def test_update_document(self, mock_settings, mock_opensearch_client):
        """Test updating a document in OpenSearch."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.get_opensearch_client', return_value=mock_opensearch_client):
                doc_id = str(uuid4())
                updates = {
                    "title_en": "Updated Title",
                    "updated_at": datetime.now().isoformat()
                }
                
                mock_opensearch_client.update = AsyncMock(return_value={"result": "updated"})
                
                await opensearch.update_document(doc_id, updates)
                
                mock_opensearch_client.update.assert_called_once()
    
    async def test_search_error_handling(self, mock_settings, mock_opensearch_client):
        """Test error handling in search."""
        with patch('app.services.opensearch.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.get_opensearch_client', return_value=mock_opensearch_client):
                mock_opensearch_client.search.side_effect = Exception("Connection error")
                
                with patch('app.services.opensearch.logger') as mock_logger:
                    result = await opensearch.search_knowledge("test")
                    
                    # Should handle error gracefully
                    assert result["results"] == []
                    assert result["total"] == 0
                    mock_logger.error.assert_called()


@pytest.mark.asyncio
class TestRedisService:
    """Test Redis service functions."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.redis_host = "localhost"
        settings.redis_port = 6379
        settings.redis_db = 0
        settings.redis_password = None
        settings.cache_ttl = 3600
        return settings
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        client = AsyncMock()
        client.get = AsyncMock()
        client.set = AsyncMock()
        client.delete = AsyncMock()
        client.exists = AsyncMock()
        client.expire = AsyncMock()
        client.incr = AsyncMock()
        client.decr = AsyncMock()
        client.hget = AsyncMock()
        client.hset = AsyncMock()
        client.hdel = AsyncMock()
        client.zadd = AsyncMock()
        client.zrange = AsyncMock()
        client.zrem = AsyncMock()
        return client
    
    async def test_cache_set(self, mock_settings, mock_redis_client):
        """Test setting cache value."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                key = "test_key"
                value = {"data": "test data"}
                
                await redis.cache_set(key, value, ttl=3600)
                
                mock_redis_client.set.assert_called_once()
                call_args = mock_redis_client.set.call_args
                assert key in str(call_args)
                assert json.dumps(value) in str(call_args)
    
    async def test_cache_get(self, mock_settings, mock_redis_client):
        """Test getting cache value."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                key = "test_key"
                cached_value = json.dumps({"data": "cached data"})
                mock_redis_client.get.return_value = cached_value
                
                result = await redis.cache_get(key)
                
                assert result == {"data": "cached data"}
                mock_redis_client.get.assert_called_once_with(key)
    
    async def test_cache_delete(self, mock_settings, mock_redis_client):
        """Test deleting cache value."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                key = "test_key"
                
                await redis.cache_delete(key)
                
                mock_redis_client.delete.assert_called_once_with(key)
    
    async def test_cache_exists(self, mock_settings, mock_redis_client):
        """Test checking if cache key exists."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                key = "test_key"
                mock_redis_client.exists.return_value = 1
                
                result = await redis.cache_exists(key)
                
                assert result is True
                mock_redis_client.exists.assert_called_once_with(key)
    
    async def test_rate_limit_check(self, mock_settings, mock_redis_client):
        """Test rate limiting functionality."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                user_id = "user123"
                endpoint = "/api/v1/search"
                limit = 10
                window = 60
                
                # First request - under limit
                mock_redis_client.incr.return_value = 1
                
                is_allowed = await redis.check_rate_limit(
                    user_id, endpoint, limit, window
                )
                
                assert is_allowed is True
                mock_redis_client.incr.assert_called()
                mock_redis_client.expire.assert_called()
    
    async def test_rate_limit_exceeded(self, mock_settings, mock_redis_client):
        """Test rate limit exceeded."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                user_id = "user123"
                endpoint = "/api/v1/search"
                limit = 10
                window = 60
                
                # Request count exceeds limit
                mock_redis_client.incr.return_value = 11
                
                is_allowed = await redis.check_rate_limit(
                    user_id, endpoint, limit, window
                )
                
                assert is_allowed is False
    
    async def test_cache_pattern_delete(self, mock_settings, mock_redis_client):
        """Test deleting cache keys by pattern."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                pattern = "search:*"
                mock_redis_client.keys = AsyncMock(return_value=[
                    b"search:query1",
                    b"search:query2"
                ])
                
                await redis.cache_delete_pattern(pattern)
                
                mock_redis_client.keys.assert_called_once_with(pattern)
                assert mock_redis_client.delete.call_count == 2
    
    async def test_cache_increment(self, mock_settings, mock_redis_client):
        """Test incrementing cache value."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                key = "counter:views"
                mock_redis_client.incr.return_value = 5
                
                result = await redis.cache_increment(key)
                
                assert result == 5
                mock_redis_client.incr.assert_called_once_with(key)
    
    async def test_cache_hash_operations(self, mock_settings, mock_redis_client):
        """Test hash operations in cache."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                hash_key = "user:123"
                field = "last_search"
                value = "python tutorial"
                
                # Test hset
                await redis.cache_hset(hash_key, field, value)
                mock_redis_client.hset.assert_called_once_with(hash_key, field, value)
                
                # Test hget
                mock_redis_client.hget.return_value = value
                result = await redis.cache_hget(hash_key, field)
                assert result == value
                
                # Test hdel
                await redis.cache_hdel(hash_key, field)
                mock_redis_client.hdel.assert_called_once_with(hash_key, field)
    
    async def test_cache_sorted_set_operations(self, mock_settings, mock_redis_client):
        """Test sorted set operations for rankings."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                key = "popular:searches"
                
                # Add to sorted set
                await redis.cache_zadd(key, {"python": 10, "async": 8})
                mock_redis_client.zadd.assert_called_once()
                
                # Get top items
                mock_redis_client.zrange.return_value = [b"python", b"async"]
                result = await redis.cache_zrange(key, 0, 10, withscores=False)
                assert result == [b"python", b"async"]


@pytest.mark.asyncio
class TestEmbeddingsService:
    """Test embeddings service functions."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.openai_api_key = "test-api-key"
        settings.embedding_model = "text-embedding-ada-002"
        settings.embedding_dimension = 1536
        settings.max_embedding_batch_size = 100
        return settings
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create mock OpenAI client."""
        client = Mock()
        client.embeddings = Mock()
        client.embeddings.create = AsyncMock()
        return client
    
    async def test_generate_embeddings(self, mock_settings, mock_openai_client):
        """Test generating embeddings for text."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.get_openai_client', return_value=mock_openai_client):
                text = "This is a test text for embedding generation"
                mock_embedding = [0.1] * 1536
                
                mock_openai_client.embeddings.create.return_value = Mock(
                    data=[Mock(embedding=mock_embedding)]
                )
                
                result = await embeddings.generate_embeddings(text)
                
                assert len(result) == 1536
                assert result == mock_embedding
                mock_openai_client.embeddings.create.assert_called_once()
    
    async def test_generate_batch_embeddings(self, mock_settings, mock_openai_client):
        """Test generating embeddings for multiple texts."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.get_openai_client', return_value=mock_openai_client):
                texts = ["Text 1", "Text 2", "Text 3"]
                mock_embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]
                
                mock_openai_client.embeddings.create.return_value = Mock(
                    data=[Mock(embedding=emb) for emb in mock_embeddings]
                )
                
                result = await embeddings.generate_batch_embeddings(texts)
                
                assert len(result) == 3
                assert len(result[0]) == 1536
                mock_openai_client.embeddings.create.assert_called_once()
    
    async def test_generate_embeddings_with_cache(self, mock_settings):
        """Test embedding generation with caching."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.redis.cache_get', new_callable=AsyncMock) as mock_cache_get:
                with patch('app.services.redis.cache_set', new_callable=AsyncMock) as mock_cache_set:
                    text = "Cached text"
                    cached_embedding = [0.5] * 1536
                    
                    # Cache hit
                    mock_cache_get.return_value = cached_embedding
                    
                    result = await embeddings.generate_embeddings_with_cache(text)
                    
                    assert result == cached_embedding
                    mock_cache_get.assert_called_once()
                    mock_cache_set.assert_not_called()
    
    async def test_calculate_similarity(self, mock_settings):
        """Test calculating cosine similarity between embeddings."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            embedding1 = np.array([1.0, 0.0, 0.0])
            embedding2 = np.array([0.0, 1.0, 0.0])
            embedding3 = np.array([1.0, 0.0, 0.0])
            
            # Perpendicular vectors
            similarity1 = embeddings.calculate_similarity(embedding1, embedding2)
            assert similarity1 == pytest.approx(0.0, abs=0.01)
            
            # Identical vectors
            similarity2 = embeddings.calculate_similarity(embedding1, embedding3)
            assert similarity2 == pytest.approx(1.0, abs=0.01)
    
    async def test_find_similar_items(self, mock_settings):
        """Test finding similar items by embedding."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            query_embedding = [0.5] * 1536
            
            items = [
                {"id": "1", "embedding": [0.4] * 1536},
                {"id": "2", "embedding": [0.6] * 1536},
                {"id": "3", "embedding": [0.1] * 1536}
            ]
            
            result = embeddings.find_similar_items(
                query_embedding, items, top_k=2
            )
            
            assert len(result) == 2
            # Items should be sorted by similarity
            assert result[0]["id"] in ["1", "2"]  # Most similar
    
    async def test_embedding_error_handling(self, mock_settings, mock_openai_client):
        """Test error handling in embedding generation."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            with patch('app.services.embeddings.get_openai_client', return_value=mock_openai_client):
                mock_openai_client.embeddings.create.side_effect = Exception("API Error")
                
                with patch('app.services.embeddings.logger') as mock_logger:
                    result = await embeddings.generate_embeddings("test")
                    
                    # Should return None or empty on error
                    assert result is None or result == []
                    mock_logger.error.assert_called()
    
    async def test_text_preprocessing(self, mock_settings):
        """Test text preprocessing before embedding."""
        with patch('app.services.embeddings.get_settings', return_value=mock_settings):
            # Test removing extra whitespace
            text = "  This   has    extra   spaces  "
            processed = embeddings.preprocess_text(text)
            assert processed == "This has extra spaces"
            
            # Test removing special characters
            text = "Text with @#$% special chars!!!"
            processed = embeddings.preprocess_text(text)
            assert "@#$%" not in processed
            
            # Test truncation for long text
            long_text = "a" * 10000
            processed = embeddings.preprocess_text(long_text, max_length=1000)
            assert len(processed) <= 1000


@pytest.mark.asyncio
class TestSearchService:
    """Test search service integration."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.search_default_limit = 20
        settings.search_max_limit = 100
        settings.search_timeout = 5000
        return settings
    
    async def test_hybrid_search(self, mock_settings):
        """Test hybrid search combining keyword and semantic search."""
        with patch('app.services.search.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.search_knowledge', new_callable=AsyncMock) as mock_keyword:
                with patch('app.services.embeddings.generate_embeddings', new_callable=AsyncMock) as mock_embed:
                    mock_keyword.return_value = {
                        "results": [{"id": "1", "score": 0.8}],
                        "total": 1
                    }
                    mock_embed.return_value = [0.5] * 1536
                    
                    result = await search.hybrid_search(
                        query="test",
                        semantic_weight=0.5
                    )
                    
                    assert "results" in result
                    mock_keyword.assert_called_once()
                    mock_embed.assert_called_once()
    
    async def test_search_suggestions(self, mock_settings):
        """Test generating search suggestions."""
        with patch('app.services.search.get_settings', return_value=mock_settings):
            with patch('app.services.opensearch.get_suggestions', new_callable=AsyncMock) as mock_suggest:
                mock_suggest.return_value = [
                    "python tutorial",
                    "python async",
                    "python web"
                ]
                
                result = await search.get_search_suggestions("pyth")
                
                assert len(result) == 3
                assert all("pyth" in s.lower() for s in result)
    
    async def test_log_search_query(self, mock_settings):
        """Test logging search queries."""
        with patch('app.services.search.get_settings', return_value=mock_settings):
            with patch('app.services.search.save_search_query', new_callable=AsyncMock) as mock_save:
                query_data = {
                    "query": "test search",
                    "user_id": "user123",
                    "results_count": 5,
                    "took_ms": 100
                }
                
                await search.log_search_query(**query_data)
                
                mock_save.assert_called_once_with(query_data)
    
    async def test_get_trending_searches(self, mock_settings):
        """Test getting trending search terms."""
        with patch('app.services.search.get_settings', return_value=mock_settings):
            with patch('app.services.redis.cache_zrange', new_callable=AsyncMock) as mock_zrange:
                mock_zrange.return_value = [
                    (b"python", 100),
                    (b"async", 80),
                    (b"fastapi", 60)
                ]
                
                result = await search.get_trending_searches(limit=3)
                
                assert len(result) == 3
                assert result[0]["term"] == "python"
                assert result[0]["count"] == 100