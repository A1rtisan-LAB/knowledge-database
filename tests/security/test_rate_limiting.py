"""Tests for enhanced rate limiting."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, HTTPException
from starlette.datastructures import Headers
from app.middleware.rate_limit import RateLimitMiddleware


class TestRateLimiting:
    """Test rate limiting middleware."""
    
    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI app."""
        return Mock()
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.method = "GET"
        request.headers = Headers({})
        return request
    
    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next function."""
        async def call_next(request):
            response = Mock()
            response.headers = {}
            return response
        return call_next
    
    @pytest.mark.asyncio
    async def test_rate_limit_allows_requests_within_limit(self, mock_app, mock_request, mock_call_next):
        """Test that requests within limit are allowed."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=5,
            period=60,
            use_redis=False  # Use in-memory for testing
        )
        
        # Make 5 requests (within limit)
        for _ in range(5):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response is not None
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
    
    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excess_requests(self, mock_app, mock_request, mock_call_next):
        """Test that requests exceeding limit are blocked."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=3,
            period=60,
            use_redis=False
        )
        
        # Make 3 requests (at limit)
        for _ in range(3):
            await middleware.dispatch(mock_request, mock_call_next)
        
        # 4th request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_burst_rate_limiting(self, mock_app, mock_request, mock_call_next):
        """Test burst rate limiting."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=100,
            period=60,
            burst_requests=2,
            burst_period=1,
            use_redis=False
        )
        
        # Make 2 burst requests (at limit)
        for _ in range(2):
            await middleware.dispatch(mock_request, mock_call_next)
        
        # 3rd request within burst period should be blocked
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        
        assert exc_info.value.status_code == 429
        assert "short period" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_rate_limit_by_ip(self, mock_app, mock_call_next):
        """Test rate limiting by IP address."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=2,
            period=60,
            by_ip=True,
            by_user=False,
            use_redis=False
        )
        
        # Create two requests from different IPs
        request1 = Mock(spec=Request)
        request1.client = Mock()
        request1.client.host = "192.168.1.1"
        request1.url = Mock()
        request1.url.path = "/api/v1/test"
        request1.method = "GET"
        request1.headers = Headers({})
        
        request2 = Mock(spec=Request)
        request2.client = Mock()
        request2.client.host = "192.168.1.2"
        request2.url = Mock()
        request2.url.path = "/api/v1/test"
        request2.method = "GET"
        request2.headers = Headers({})
        
        # Each IP should have its own limit
        for _ in range(2):
            await middleware.dispatch(request1, mock_call_next)
            await middleware.dispatch(request2, mock_call_next)
        
        # 3rd request from first IP should be blocked
        with pytest.raises(HTTPException):
            await middleware.dispatch(request1, mock_call_next)
        
        # 3rd request from second IP should also be blocked
        with pytest.raises(HTTPException):
            await middleware.dispatch(request2, mock_call_next)
    
    @pytest.mark.asyncio
    async def test_rate_limit_skip_paths(self, mock_app, mock_call_next):
        """Test that certain paths are skipped."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=1,
            period=60,
            use_redis=False
        )
        
        # Create request to health endpoint
        health_request = Mock(spec=Request)
        health_request.url = Mock()
        health_request.url.path = "/health"
        
        # Should not be rate limited
        for _ in range(10):
            response = await middleware.dispatch(health_request, mock_call_next)
            assert response is not None
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, mock_app, mock_request, mock_call_next):
        """Test rate limit headers in response."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=10,
            period=60,
            use_redis=False
        )
        
        # Make a request
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Check headers
        assert response.headers["X-RateLimit-Limit"] == "10"
        assert int(response.headers["X-RateLimit-Remaining"]) == 9
        assert "X-RateLimit-Reset" in response.headers
    
    @pytest.mark.asyncio
    async def test_rate_limit_cleanup(self, mock_app, mock_request, mock_call_next):
        """Test that old entries are cleaned up."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=2,
            period=1,  # 1 second period for testing
            use_redis=False
        )
        
        # Make 2 requests (at limit)
        for _ in range(2):
            await middleware.dispatch(mock_request, mock_call_next)
        
        # 3rd request should be blocked
        with pytest.raises(HTTPException):
            await middleware.dispatch(mock_request, mock_call_next)
        
        # Wait for period to expire
        await asyncio.sleep(1.1)
        
        # Should be able to make requests again
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response is not None
    
    def test_get_client_ip_with_proxy_headers(self, mock_app):
        """Test client IP extraction with proxy headers."""
        middleware = RateLimitMiddleware(mock_app, use_redis=False)
        
        # Test X-Forwarded-For
        request = Mock(spec=Request)
        request.headers = Headers({"X-Forwarded-For": "203.0.113.1, 198.51.100.1"})
        request.client = Mock()
        request.client.host = "10.0.0.1"
        
        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.1"  # First IP in chain
        
        # Test X-Real-IP
        request.headers = Headers({"X-Real-IP": "203.0.113.2"})
        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.2"
        
        # Test direct client IP
        request.headers = Headers({})
        ip = middleware._get_client_ip(request)
        assert ip == "10.0.0.1"
    
    @pytest.mark.asyncio
    async def test_get_user_id_from_token(self, mock_app):
        """Test user ID extraction from JWT token."""
        middleware = RateLimitMiddleware(mock_app, use_redis=False)
        
        # Test with Bearer token
        request = Mock(spec=Request)
        request.headers = Headers({"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"})
        
        user_id = await middleware._get_user_id(request)
        assert user_id is not None
        assert len(user_id) == 16  # Hash truncated to 16 chars
        
        # Test without token
        request.headers = Headers({})
        user_id = await middleware._get_user_id(request)
        assert user_id is None


class TestRateLimitingWithRedis:
    """Test rate limiting with Redis backend."""
    
    @pytest.mark.asyncio
    @patch('app.middleware.rate_limit.get_redis_client')
    async def test_redis_rate_limiting(self, mock_get_redis, mock_app, mock_request, mock_call_next):
        """Test rate limiting using Redis."""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.pipeline.return_value = mock_redis
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=0)
        mock_redis.zadd = AsyncMock()
        mock_redis.expire = AsyncMock()
        mock_redis.execute = AsyncMock(return_value=[None, 0, None, None])
        mock_get_redis.return_value = mock_redis
        
        middleware = RateLimitMiddleware(
            mock_app,
            requests=5,
            period=60,
            use_redis=True
        )
        
        # Make a request
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response is not None
        
        # Verify Redis operations were called
        mock_redis.zremrangebyscore.assert_called()
        mock_redis.zcard.assert_called()
        mock_redis.zadd.assert_called()
        mock_redis.expire.assert_called()