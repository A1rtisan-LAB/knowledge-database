"""Comprehensive unit tests for Redis caching service."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Optional, Any
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
import structlog

from app.services import redis as redis_service
from app.core.config import Settings


@pytest.mark.unit
class TestRedisService:
    """Comprehensive test suite for Redis caching service functions."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for Redis configuration."""
        settings = Mock(spec=Settings)
        settings.redis_host = "localhost"
        settings.redis_port = 6379
        settings.redis_db = 0
        settings.redis_password = "test_password"
        settings.redis_url = "redis://:test_password@localhost:6379/0"
        settings.redis_cache_ttl = 3600
        settings.redis_max_connections = 50
        settings.redis_connection_timeout = 10
        settings.redis_socket_keepalive = True
        settings.redis_socket_keepalive_options = {}
        return settings
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return Mock(spec=structlog.get_logger())
    
    @pytest.fixture
    async def mock_redis_client(self):
        """Create mock Redis client."""
        mock_client = AsyncMock(spec=redis.Redis)
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.get = AsyncMock(return_value=None)
        mock_client.setex = AsyncMock(return_value=True)
        mock_client.delete = AsyncMock(return_value=1)
        mock_client.scan_iter = AsyncMock()
        mock_client.close = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def mock_connection_pool(self):
        """Create mock connection pool."""
        mock_pool = Mock(spec=ConnectionPool)
        mock_pool.disconnect = AsyncMock()
        return mock_pool
    
    def setup_method(self):
        """Reset global state before each test."""
        redis_service.redis_client = None
        redis_service.redis_pool = None
    
    def teardown_method(self):
        """Clean up after each test."""
        redis_service.redis_client = None
        redis_service.redis_pool = None
    
    # Test: get_redis_client
    async def test_get_redis_client_first_call(self, mock_settings):
        """Test getting Redis client for the first time."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.ConnectionPool') as mock_pool_class:
                with patch('app.services.redis.redis.Redis') as mock_redis_class:
                    mock_pool = Mock()
                    mock_pool_class.from_url.return_value = mock_pool
                    mock_client = AsyncMock()
                    mock_redis_class.return_value = mock_client
                    
                    client = await redis_service.get_redis_client()
                    
                    assert client is not None
                    assert client == mock_client
                    mock_pool_class.from_url.assert_called_once_with(
                        mock_settings.redis_url,
                        max_connections=50,
                        decode_responses=True
                    )
                    mock_redis_class.assert_called_once_with(connection_pool=mock_pool)
    
    async def test_get_redis_client_subsequent_calls(self, mock_settings, mock_redis_client):
        """Test getting Redis client on subsequent calls (should reuse existing)."""
        redis_service.redis_client = mock_redis_client
        redis_service.redis_pool = Mock()
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.ConnectionPool') as mock_pool_class:
                with patch('app.services.redis.redis.Redis') as mock_redis_class:
                    client = await redis_service.get_redis_client()
                    
                    assert client == mock_redis_client
                    # Should not create new connection
                    mock_pool_class.from_url.assert_not_called()
                    mock_redis_class.assert_not_called()
    
    async def test_get_redis_client_with_different_settings(self, mock_settings):
        """Test get_redis_client with various configuration settings."""
        mock_settings.redis_url = "redis://different-host:6380/1"
        mock_settings.redis_max_connections = 100
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.ConnectionPool') as mock_pool_class:
                with patch('app.services.redis.redis.Redis') as mock_redis_class:
                    mock_pool = Mock()
                    mock_pool_class.from_url.return_value = mock_pool
                    
                    client = await redis_service.get_redis_client()
                    
                    mock_pool_class.from_url.assert_called_once_with(
                        "redis://different-host:6380/1",
                        max_connections=50,  # Uses hardcoded value
                        decode_responses=True
                    )
    
    # Test: init_redis
    async def test_init_redis_success(self, mock_settings, mock_redis_client, mock_logger):
        """Test successful Redis initialization."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    await redis_service.init_redis()
                    
                    mock_redis_client.ping.assert_called_once()
                    mock_logger.info.assert_called_once_with("Redis connection established")
    
    async def test_init_redis_connection_failure(self, mock_settings, mock_logger):
        """Test Redis initialization with connection failure."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', side_effect=Exception("Connection refused")):
                with patch('app.services.redis.logger', mock_logger):
                    # Should not raise exception
                    await redis_service.init_redis()
                    
                    mock_logger.error.assert_called_once()
                    assert "Failed to connect to Redis" in mock_logger.error.call_args[0][0]
    
    async def test_init_redis_ping_failure(self, mock_settings, mock_redis_client, mock_logger):
        """Test Redis initialization when ping fails."""
        mock_redis_client.ping.side_effect = Exception("Ping failed")
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    await redis_service.init_redis()
                    
                    mock_logger.error.assert_called_once()
                    assert "Failed to connect to Redis" in mock_logger.error.call_args[0][0]
    
    # Test: close_redis
    async def test_close_redis_with_active_connection(self, mock_settings, mock_redis_client, mock_connection_pool):
        """Test closing Redis with active connection."""
        redis_service.redis_client = mock_redis_client
        redis_service.redis_pool = mock_connection_pool
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            await redis_service.close_redis()
            
            mock_redis_client.close.assert_called_once()
            mock_connection_pool.disconnect.assert_called_once()
            assert redis_service.redis_client is None
            assert redis_service.redis_pool is None
    
    async def test_close_redis_without_connection(self, mock_settings):
        """Test closing Redis when no connection exists."""
        redis_service.redis_client = None
        redis_service.redis_pool = None
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            # Should not raise exception
            await redis_service.close_redis()
            
            assert redis_service.redis_client is None
            assert redis_service.redis_pool is None
    
    async def test_close_redis_partial_state(self, mock_settings, mock_redis_client):
        """Test closing Redis with only client or only pool."""
        # Only client exists
        redis_service.redis_client = mock_redis_client
        redis_service.redis_pool = None
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            await redis_service.close_redis()
            mock_redis_client.close.assert_called_once()
        
        # Only pool exists
        redis_service.redis_client = None
        redis_service.redis_pool = Mock()
        redis_service.redis_pool.disconnect = AsyncMock()
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            await redis_service.close_redis()
            redis_service.redis_pool.disconnect.assert_called_once()
    
    # Test: cache_get
    async def test_cache_get_success(self, mock_settings, mock_redis_client, mock_logger):
        """Test successful cache retrieval."""
        test_data = {"key": "value", "number": 42}
        mock_redis_client.get.return_value = json.dumps(test_data)
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    result = await redis_service.cache_get("test_key")
                    
                    assert result == test_data
                    mock_redis_client.get.assert_called_once_with("test_key")
    
    async def test_cache_get_miss(self, mock_settings, mock_redis_client, mock_logger):
        """Test cache miss (key not found)."""
        mock_redis_client.get.return_value = None
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    result = await redis_service.cache_get("missing_key")
                    
                    assert result is None
                    mock_redis_client.get.assert_called_once_with("missing_key")
    
    async def test_cache_get_json_decode_error(self, mock_settings, mock_redis_client, mock_logger):
        """Test cache get with invalid JSON."""
        mock_redis_client.get.return_value = "invalid json {"
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    result = await redis_service.cache_get("bad_json_key")
                    
                    assert result is None
                    mock_logger.error.assert_called_once()
                    assert "Cache get error" in mock_logger.error.call_args[0][0]
    
    async def test_cache_get_connection_error(self, mock_settings, mock_logger):
        """Test cache get with connection error."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', side_effect=Exception("Connection lost")):
                with patch('app.services.redis.logger', mock_logger):
                    result = await redis_service.cache_get("test_key")
                    
                    assert result is None
                    mock_logger.error.assert_called_once()
                    assert "Cache get error" in mock_logger.error.call_args[0][0]
    
    async def test_cache_get_various_data_types(self, mock_settings, mock_redis_client):
        """Test cache get with various data types."""
        test_cases = [
            {"type": "string", "value": "test"},
            {"type": "number", "value": 42},
            {"type": "float", "value": 3.14},
            {"type": "boolean", "value": True},
            {"type": "null", "value": None},
            {"type": "array", "value": [1, 2, 3]},
            {"type": "nested", "value": {"a": {"b": {"c": 1}}}},
        ]
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                for test_case in test_cases:
                    mock_redis_client.get.return_value = json.dumps(test_case["value"])
                    result = await redis_service.cache_get(f"key_{test_case['type']}")
                    assert result == test_case["value"]
    
    # Test: cache_set
    async def test_cache_set_success(self, mock_settings, mock_redis_client, mock_logger):
        """Test successful cache set."""
        test_data = {"key": "value", "number": 42}
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    result = await redis_service.cache_set("test_key", test_data)
                    
                    assert result is True
                    mock_redis_client.setex.assert_called_once_with(
                        "test_key",
                        3600,  # Default TTL
                        json.dumps(test_data)
                    )
    
    async def test_cache_set_with_custom_ttl(self, mock_settings, mock_redis_client):
        """Test cache set with custom TTL."""
        test_data = {"data": "test"}
        custom_ttl = 7200
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                result = await redis_service.cache_set("test_key", test_data, ttl=custom_ttl)
                
                assert result is True
                mock_redis_client.setex.assert_called_once_with(
                    "test_key",
                    custom_ttl,
                    json.dumps(test_data)
                )
    
    async def test_cache_set_with_none_ttl(self, mock_settings, mock_redis_client):
        """Test cache set with None TTL (uses default)."""
        test_data = {"data": "test"}
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                result = await redis_service.cache_set("test_key", test_data, ttl=None)
                
                assert result is True
                mock_redis_client.setex.assert_called_once_with(
                    "test_key",
                    mock_settings.redis_cache_ttl,
                    json.dumps(test_data)
                )
    
    async def test_cache_set_json_encode_error(self, mock_settings, mock_redis_client, mock_logger):
        """Test cache set with non-serializable data."""
        # Create a non-serializable object
        class NonSerializable:
            pass
        
        test_data = {"obj": NonSerializable()}
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    result = await redis_service.cache_set("test_key", test_data)
                    
                    assert result is False
                    mock_logger.error.assert_called_once()
                    assert "Cache set error" in mock_logger.error.call_args[0][0]
    
    async def test_cache_set_connection_error(self, mock_settings, mock_logger):
        """Test cache set with connection error."""
        test_data = {"data": "test"}
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', side_effect=Exception("Connection lost")):
                with patch('app.services.redis.logger', mock_logger):
                    result = await redis_service.cache_set("test_key", test_data)
                    
                    assert result is False
                    mock_logger.error.assert_called_once()
    
    async def test_cache_set_various_data_types(self, mock_settings, mock_redis_client):
        """Test cache set with various data types."""
        test_cases = [
            "simple string",
            123,
            3.14159,
            True,
            False,
            None,
            [],
            [1, 2, 3],
            {"nested": {"data": [1, 2, 3]}},
            {"unicode": "한글 테스트 émojis 😀"},
        ]
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                for i, test_data in enumerate(test_cases):
                    result = await redis_service.cache_set(f"key_{i}", test_data)
                    assert result is True
                    mock_redis_client.setex.assert_called()
    
    # Test: cache_delete
    async def test_cache_delete_success(self, mock_settings, mock_redis_client, mock_logger):
        """Test successful cache deletion."""
        mock_redis_client.delete.return_value = 1
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    result = await redis_service.cache_delete("test_key")
                    
                    assert result is True
                    mock_redis_client.delete.assert_called_once_with("test_key")
    
    async def test_cache_delete_key_not_found(self, mock_settings, mock_redis_client):
        """Test cache delete when key doesn't exist."""
        mock_redis_client.delete.return_value = 0
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                result = await redis_service.cache_delete("missing_key")
                
                assert result is True  # Still returns True
                mock_redis_client.delete.assert_called_once_with("missing_key")
    
    async def test_cache_delete_connection_error(self, mock_settings, mock_logger):
        """Test cache delete with connection error."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', side_effect=Exception("Connection lost")):
                with patch('app.services.redis.logger', mock_logger):
                    result = await redis_service.cache_delete("test_key")
                    
                    assert result is False
                    mock_logger.error.assert_called_once()
                    assert "Cache delete error" in mock_logger.error.call_args[0][0]
    
    async def test_cache_delete_batch(self, mock_settings, mock_redis_client):
        """Test batch deletion of multiple keys."""
        keys = [f"key_{i}" for i in range(10)]
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                for key in keys:
                    result = await redis_service.cache_delete(key)
                    assert result is True
                
                assert mock_redis_client.delete.call_count == 10
    
    # Test: cache_invalidate_pattern
    async def test_cache_invalidate_pattern_success(self, mock_settings, mock_redis_client, mock_logger):
        """Test successful pattern-based cache invalidation."""
        # Mock scan_iter to return async generator
        async def mock_scan():
            keys = ["knowledge:1", "knowledge:2", "knowledge:3"]
            for key in keys:
                yield key
        
        mock_redis_client.scan_iter.return_value = mock_scan()
        mock_redis_client.delete.return_value = 3
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    deleted_count = await redis_service.cache_invalidate_pattern("knowledge:*")
                    
                    assert deleted_count == 3
                    mock_redis_client.scan_iter.assert_called_once_with(match="knowledge:*")
                    mock_redis_client.delete.assert_called_once()
                    mock_logger.info.assert_called_once()
                    assert "Invalidated 3 cache keys" in mock_logger.info.call_args[0][0]
    
    async def test_cache_invalidate_pattern_no_matches(self, mock_settings, mock_redis_client, mock_logger):
        """Test pattern invalidation with no matching keys."""
        async def mock_scan():
            return
            yield  # Empty generator
        
        mock_redis_client.scan_iter.return_value = mock_scan()
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    deleted_count = await redis_service.cache_invalidate_pattern("nonexistent:*")
                    
                    assert deleted_count == 0
                    mock_redis_client.delete.assert_not_called()
    
    async def test_cache_invalidate_pattern_large_result(self, mock_settings, mock_redis_client, mock_logger):
        """Test pattern invalidation with many matching keys."""
        async def mock_scan():
            for i in range(1000):
                yield f"cache:item:{i}"
        
        mock_redis_client.scan_iter.return_value = mock_scan()
        mock_redis_client.delete.return_value = 1000
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    deleted_count = await redis_service.cache_invalidate_pattern("cache:item:*")
                    
                    assert deleted_count == 1000
                    mock_logger.info.assert_called_once()
                    assert "Invalidated 1000 cache keys" in mock_logger.info.call_args[0][0]
    
    async def test_cache_invalidate_pattern_connection_error(self, mock_settings, mock_logger):
        """Test pattern invalidation with connection error."""
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', side_effect=Exception("Connection lost")):
                with patch('app.services.redis.logger', mock_logger):
                    deleted_count = await redis_service.cache_invalidate_pattern("test:*")
                    
                    assert deleted_count == 0
                    mock_logger.error.assert_called_once()
                    assert "Cache invalidation error" in mock_logger.error.call_args[0][0]
    
    async def test_cache_invalidate_pattern_scan_error(self, mock_settings, mock_redis_client, mock_logger):
        """Test pattern invalidation when scan fails."""
        async def mock_scan():
            raise Exception("Scan failed")
            yield  # Won't reach here
        
        mock_redis_client.scan_iter.return_value = mock_scan()
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    deleted_count = await redis_service.cache_invalidate_pattern("test:*")
                    
                    assert deleted_count == 0
                    mock_logger.error.assert_called_once()
    
    async def test_cache_invalidate_various_patterns(self, mock_settings, mock_redis_client, mock_logger):
        """Test various cache invalidation patterns."""
        patterns = [
            "user:*",
            "session:*:data",
            "cache:v1:*",
            "*:temp",
            "prefix*suffix",
        ]
        
        async def mock_scan():
            yield "matched_key"
        
        mock_redis_client.scan_iter.return_value = mock_scan()
        mock_redis_client.delete.return_value = 1
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                with patch('app.services.redis.logger', mock_logger):
                    for pattern in patterns:
                        deleted_count = await redis_service.cache_invalidate_pattern(pattern)
                        assert deleted_count == 1
    
    # Integration and edge cases
    async def test_concurrent_cache_operations(self, mock_settings, mock_redis_client):
        """Test concurrent cache operations."""
        import asyncio
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                # Concurrent reads
                read_tasks = [redis_service.cache_get(f"key_{i}") for i in range(10)]
                read_results = await asyncio.gather(*read_tasks)
                assert len(read_results) == 10
                
                # Concurrent writes
                write_tasks = [
                    redis_service.cache_set(f"key_{i}", {"value": i}) 
                    for i in range(10)
                ]
                write_results = await asyncio.gather(*write_tasks)
                assert all(result is True for result in write_results)
                
                # Concurrent deletes
                delete_tasks = [redis_service.cache_delete(f"key_{i}") for i in range(10)]
                delete_results = await asyncio.gather(*delete_tasks)
                assert all(result is True for result in delete_results)
    
    async def test_cache_operations_with_special_keys(self, mock_settings, mock_redis_client):
        """Test cache operations with special characters in keys."""
        special_keys = [
            "key:with:colons",
            "key-with-dashes",
            "key_with_underscores",
            "key.with.dots",
            "key/with/slashes",
            "key\\with\\backslashes",
            "key with spaces",
            "한글키",
            "key#with#hashes",
        ]
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                for key in special_keys:
                    # Test all operations with special keys
                    await redis_service.cache_set(key, {"test": "data"})
                    await redis_service.cache_get(key)
                    await redis_service.cache_delete(key)
                
                assert mock_redis_client.setex.call_count == len(special_keys)
                assert mock_redis_client.get.call_count == len(special_keys)
                assert mock_redis_client.delete.call_count == len(special_keys)
    
    async def test_cache_with_large_values(self, mock_settings, mock_redis_client):
        """Test caching large values."""
        # Create a large object (simulating large cached data)
        large_data = {
            "items": [{"id": i, "data": "x" * 1000} for i in range(100)]
        }
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                result = await redis_service.cache_set("large_key", large_data)
                assert result is True
                
                # Verify serialized data was passed
                call_args = mock_redis_client.setex.call_args
                serialized_data = call_args[0][2]
                assert len(serialized_data) > 100000  # Should be large
    
    async def test_cache_ttl_boundaries(self, mock_settings, mock_redis_client):
        """Test cache with various TTL values."""
        ttl_values = [0, 1, 60, 3600, 86400, 2147483647]  # Max 32-bit int
        
        with patch('app.services.redis.get_settings', return_value=mock_settings):
            with patch('app.services.redis.get_redis_client', return_value=mock_redis_client):
                for ttl in ttl_values:
                    result = await redis_service.cache_set("test_key", {"data": "test"}, ttl=ttl)
                    assert result is True
                    
                    call_args = mock_redis_client.setex.call_args
                    assert call_args[0][1] == ttl