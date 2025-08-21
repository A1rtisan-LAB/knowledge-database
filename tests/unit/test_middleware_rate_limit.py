"""Comprehensive unit tests for RateLimitMiddleware."""

import asyncio
import time
import hashlib
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
import pytest
from fastapi import Request, Response, HTTPException, status
from starlette.datastructures import Headers

from app.middleware.rate_limit import RateLimitMiddleware


@pytest.mark.asyncio
class TestRateLimitMiddleware:
    """Test RateLimitMiddleware functionality."""
    
    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI app."""
        return Mock()
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request with necessary attributes."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/v1/knowledge"
        request.headers = Headers({})
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = Mock()
        return request
    
    @pytest.fixture
    def mock_response(self):
        """Create mock response."""
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}
        return response
    
    @pytest.fixture
    def middleware_default(self, mock_app):
        """Create RateLimitMiddleware with default settings."""
        return RateLimitMiddleware(
            mock_app,
            requests=100,
            period=60,
            burst_requests=10,
            burst_period=1,
            use_redis=False,  # Use in-memory for unit tests
            by_user=True,
            by_ip=True,
            by_endpoint=False
        )
    
    @pytest.fixture
    def middleware_redis(self, mock_app):
        """Create RateLimitMiddleware with Redis enabled."""
        return RateLimitMiddleware(
            mock_app,
            requests=100,
            period=60,
            burst_requests=10,
            burst_period=1,
            use_redis=True,
            by_user=True,
            by_ip=True,
            by_endpoint=True
        )
    
    async def test_skip_paths(self, middleware_default, mock_response):
        """Test that certain paths skip rate limiting."""
        skip_paths = ["/health", "/", "/docs", "/openapi.json", "/redoc"]
        
        for path in skip_paths:
            request = Mock(spec=Request)
            request.url = Mock()
            request.url.path = path
            
            async def call_next(req):
                return mock_response
            
            response = await middleware_default.dispatch(request, call_next)
            assert response == mock_response
    
    async def test_rate_limit_by_ip(self, middleware_default, mock_request, mock_response):
        """Test rate limiting by IP address."""
        mock_request.client.host = "192.168.1.100"
        
        async def call_next(request):
            return mock_response
        
        # First request should pass
        response = await middleware_default.dispatch(mock_request, call_next)
        assert response.status_code == 200
        
        # Check that IP-based identifier was used
        assert any("ip:192.168.1.100" in key for key in middleware_default.clients.keys())
    
    async def test_rate_limit_by_user(self, middleware_default, mock_response):
        """Test rate limiting by authenticated user."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v1/knowledge"
        request.headers = Headers({"Authorization": "Bearer test-token-123"})
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = Mock()
        request.state.user = Mock()
        request.state.user.id = "user123"
        
        async def call_next(req):
            return mock_response
        
        # Make request
        response = await middleware_default.dispatch(request, call_next)
        assert response.status_code == 200
        
        # Check that user-based identifier was created
        token_hash = hashlib.sha256("test-token-123".encode()).hexdigest()[:16]
        assert any(token_hash in key for key in middleware_default.clients.keys())
    
    async def test_rate_limit_by_endpoint(self, mock_app, mock_request, mock_response):
        """Test rate limiting by endpoint."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=100,
            period=60,
            by_user=False,
            by_ip=False,
            by_endpoint=True,
            use_redis=False
        )
        
        mock_request.url.path = "/api/v1/search"
        
        async def call_next(request):
            return mock_response
        
        response = await middleware.dispatch(mock_request, call_next)
        assert response.status_code == 200
        
        # Check that endpoint-based identifier was used
        assert any("endpoint:GET:/api/v1/search" in key for key in middleware.clients.keys())
    
    async def test_burst_limit_exceeded(self, mock_app, mock_request):
        """Test burst rate limit enforcement."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=100,
            period=60,
            burst_requests=3,
            burst_period=1,
            use_redis=False
        )
        
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}
        
        async def call_next(request):
            return response
        
        # Make burst requests
        for i in range(3):
            result = await middleware.dispatch(mock_request, call_next)
            assert result.status_code == 200
        
        # Fourth request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, call_next)
        
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "short period" in exc_info.value.detail
        assert "Retry-After" in exc_info.value.headers
    
    async def test_normal_limit_exceeded(self, mock_app, mock_request):
        """Test normal rate limit enforcement."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=5,
            period=60,
            burst_requests=10,  # Higher than normal to test normal limit
            burst_period=1,
            use_redis=False
        )
        
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}
        
        async def call_next(request):
            return response
        
        # Make requests up to limit
        for i in range(5):
            result = await middleware.dispatch(mock_request, call_next)
            assert result.status_code == 200
        
        # Sixth request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, call_next)
        
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Rate limit exceeded" in exc_info.value.detail
        assert "Retry-After" in exc_info.value.headers
    
    async def test_rate_limit_headers(self, middleware_default, mock_request, mock_response):
        """Test that rate limit headers are added to response."""
        async def call_next(request):
            return mock_response
        
        response = await middleware_default.dispatch(mock_request, call_next)
        
        # Check rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert "X-RateLimit-Remaining" in response.headers
        assert int(response.headers["X-RateLimit-Remaining"]) >= 0
        assert "X-RateLimit-Reset" in response.headers
        assert int(response.headers["X-RateLimit-Reset"]) > time.time()
    
    async def test_get_client_ip_forwarded(self, middleware_default, mock_response):
        """Test getting client IP from forwarded headers."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.headers = Headers({
            "X-Forwarded-For": "203.0.113.1, 198.51.100.2"
        })
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = Mock()
        
        async def call_next(req):
            return mock_response
        
        await middleware_default.dispatch(request, call_next)
        
        # Should use first IP from X-Forwarded-For
        assert any("ip:203.0.113.1" in key for key in middleware_default.clients.keys())
    
    async def test_get_client_ip_real_ip(self, middleware_default, mock_response):
        """Test getting client IP from X-Real-IP header."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.headers = Headers({
            "X-Real-IP": "203.0.113.1"
        })
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = Mock()
        
        async def call_next(req):
            return mock_response
        
        await middleware_default.dispatch(request, call_next)
        
        # Should use IP from X-Real-IP
        assert any("ip:203.0.113.1" in key for key in middleware_default.clients.keys())
    
    async def test_get_client_ip_no_client(self, middleware_default, mock_response):
        """Test handling request without client information."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.headers = Headers({})
        request.client = None
        request.state = Mock()
        
        async def call_next(req):
            return mock_response
        
        await middleware_default.dispatch(request, call_next)
        
        # Should use "unknown" as IP
        assert any("ip:unknown" in key for key in middleware_default.clients.keys())
    
    async def test_get_user_id_from_token(self, middleware_default, mock_response):
        """Test extracting user ID from authorization token."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.headers = Headers({
            "Authorization": "Bearer my-jwt-token-here"
        })
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = Mock()
        
        async def call_next(req):
            return mock_response
        
        await middleware_default.dispatch(request, call_next)
        
        # Should create hash from token
        token_hash = hashlib.sha256("my-jwt-token-here".encode()).hexdigest()[:16]
        assert any(f"user:{token_hash}" in key for key in middleware_default.clients.keys())
    
    async def test_cleanup_old_entries(self, mock_app, mock_request, mock_response):
        """Test cleanup of old rate limit entries."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=100,
            period=1,  # 1 second period for quick testing
            use_redis=False
        )
        
        async def call_next(request):
            return mock_response
        
        # Add some entries
        await middleware.dispatch(mock_request, call_next)
        assert len(middleware.clients) > 0
        
        # Wait for entries to expire
        await asyncio.sleep(1.5)
        
        # Trigger cleanup with new request
        with patch('app.middleware.rate_limit.time.time') as mock_time:
            # Mock time to trigger cleanup
            mock_time.return_value = time.time() + 61
            await middleware.dispatch(mock_request, call_next)
        
        # Old entries should be cleaned
        for entries in middleware.clients.values():
            for timestamp in entries:
                assert timestamp > time.time() - 2
    
    @patch('app.middleware.rate_limit.get_redis_client')
    async def test_redis_rate_limiting(self, mock_redis_client, middleware_redis, mock_request, mock_response):
        """Test rate limiting with Redis backend."""
        # Setup mock Redis client
        redis_mock = AsyncMock()
        redis_mock.pipeline = MagicMock()
        pipe_mock = AsyncMock()
        redis_mock.pipeline.return_value = pipe_mock
        
        pipe_mock.zremrangebyscore = AsyncMock()
        pipe_mock.zcard = AsyncMock()
        pipe_mock.zadd = AsyncMock()
        pipe_mock.expire = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, 5, None, None])  # 5 requests counted
        
        mock_redis_client.return_value = redis_mock
        
        async def call_next(request):
            return mock_response
        
        response = await middleware_redis.dispatch(mock_request, call_next)
        
        assert response.status_code == 200
        redis_mock.pipeline.assert_called()
        pipe_mock.execute.assert_called()
    
    @patch('app.middleware.rate_limit.get_redis_client')
    async def test_redis_rate_limit_exceeded(self, mock_redis_client, middleware_redis, mock_request):
        """Test rate limit exceeded with Redis backend."""
        redis_mock = AsyncMock()
        redis_mock.pipeline = MagicMock()
        pipe_mock = AsyncMock()
        redis_mock.pipeline.return_value = pipe_mock
        
        pipe_mock.zremrangebyscore = AsyncMock()
        pipe_mock.zcard = AsyncMock()
        pipe_mock.zadd = AsyncMock()
        pipe_mock.expire = AsyncMock()
        pipe_mock.execute = AsyncMock(return_value=[None, 101, None, None])  # Over limit
        
        redis_mock.zrange = AsyncMock(return_value=[(b"entry", 1000.0)])
        redis_mock.zrem = AsyncMock()
        
        mock_redis_client.return_value = redis_mock
        
        async def call_next(request):
            return Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware_redis.dispatch(mock_request, call_next)
        
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        redis_mock.zrem.assert_called()  # Should remove the over-limit entry
    
    @patch('app.middleware.rate_limit.get_redis_client')
    async def test_redis_failure_fallback(self, mock_redis_client, middleware_redis, mock_request, mock_response):
        """Test fallback to in-memory when Redis fails."""
        mock_redis_client.side_effect = Exception("Redis connection failed")
        
        with patch('app.middleware.rate_limit.logger') as mock_logger:
            async def call_next(request):
                return mock_response
            
            # Should fall back to in-memory and allow request
            response = await middleware_redis.dispatch(mock_request, call_next)
            assert response.status_code == 200
            mock_logger.error.assert_called()
            
            # Check in-memory storage was used
            assert len(middleware_redis.clients) > 0
    
    async def test_multiple_identifiers(self, mock_app, mock_response):
        """Test rate limiting with multiple identifiers."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=5,
            period=60,
            by_user=True,
            by_ip=True,
            by_endpoint=True,
            use_redis=False
        )
        
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.method = "GET"
        request.headers = Headers({"Authorization": "Bearer token123"})
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.state = Mock()
        
        async def call_next(req):
            return mock_response
        
        await middleware.dispatch(request, call_next)
        
        # Should have identifiers for IP, user, and endpoint
        keys = list(middleware.clients.keys())
        assert any("ip:192.168.1.100" in key for key in keys)
        assert any("user:" in key for key in keys)
        assert any("endpoint:GET:/api/v1/test" in key for key in keys)
    
    async def test_logging_rate_limit_exceeded(self, mock_app, mock_request):
        """Test that rate limit violations are logged."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=1,
            period=60,
            use_redis=False
        )
        
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}
        
        async def call_next(request):
            return response
        
        # First request passes
        await middleware.dispatch(mock_request, call_next)
        
        # Second request should be blocked and logged
        with patch('app.middleware.rate_limit.logger') as mock_logger:
            with pytest.raises(HTTPException):
                await middleware.dispatch(mock_request, call_next)
            
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args
            assert "Rate limit exceeded" in warning_call[0][0]
    
    async def test_concurrent_requests(self, middleware_default, mock_response):
        """Test handling concurrent requests with rate limiting."""
        async def make_request(request_id):
            request = Mock(spec=Request)
            request.url = Mock()
            request.url.path = f"/api/v1/test{request_id}"
            request.headers = Headers({})
            request.client = Mock()
            request.client.host = f"127.0.0.{request_id}"
            request.state = Mock()
            
            async def call_next(req):
                await asyncio.sleep(0.01)
                return mock_response
            
            try:
                response = await middleware_default.dispatch(request, call_next)
                return response.status_code
            except HTTPException as e:
                return e.status_code
        
        # Make concurrent requests from different IPs
        tasks = [make_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed as they're from different IPs
        assert all(status == 200 for status in results)
    
    async def test_request_count_calculation(self, mock_app, mock_request, mock_response):
        """Test accurate request counting."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=10,
            period=60,
            use_redis=False
        )
        
        async def call_next(request):
            return mock_response
        
        # Make 5 requests
        for _ in range(5):
            await middleware.dispatch(mock_request, call_next)
        
        # Check remaining count in headers
        response = await middleware.dispatch(mock_request, call_next)
        remaining = int(response.headers["X-RateLimit-Remaining"])
        assert remaining == 3  # 10 - 6 (5 previous + 1 current) - 1 = 3
    
    async def test_retry_after_calculation(self, mock_app, mock_request):
        """Test Retry-After header calculation."""
        middleware = RateLimitMiddleware(
            mock_app,
            requests=1,
            period=60,
            use_redis=False
        )
        
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}
        
        async def call_next(request):
            return response
        
        # First request
        await middleware.dispatch(mock_request, call_next)
        
        # Second request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, call_next)
        
        retry_after = int(exc_info.value.headers["Retry-After"])
        assert retry_after > 0
        assert retry_after <= 61  # Should be approximately the period
    
    @patch('app.middleware.rate_limit.get_redis_client')
    async def test_get_request_count_redis(self, mock_redis_client, middleware_redis, mock_request):
        """Test getting request count from Redis."""
        redis_mock = AsyncMock()
        redis_mock.zremrangebyscore = AsyncMock()
        redis_mock.zcard = AsyncMock(return_value=42)
        
        mock_redis_client.return_value = redis_mock
        
        count = await middleware_redis._get_request_count("test-identifier", 60)
        
        assert count == 42
        redis_mock.zremrangebyscore.assert_called()
        redis_mock.zcard.assert_called()
    
    @patch('app.middleware.rate_limit.get_redis_client')
    async def test_get_request_count_redis_failure(self, mock_redis_client, middleware_redis):
        """Test fallback when getting request count from Redis fails."""
        mock_redis_client.side_effect = Exception("Redis error")
        
        # Should fall back to in-memory and return 0
        count = await middleware_redis._get_request_count("test-identifier", 60)
        assert count == 0
    
    async def test_different_http_methods(self, middleware_default, mock_response):
        """Test rate limiting for different HTTP methods."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        
        for method in methods:
            request = Mock(spec=Request)
            request.method = method
            request.url = Mock()
            request.url.path = f"/api/v1/{method.lower()}"
            request.headers = Headers({})
            request.client = Mock()
            request.client.host = f"10.0.0.{methods.index(method)}"
            request.state = Mock()
            
            async def call_next(req):
                return mock_response
            
            response = await middleware_default.dispatch(request, call_next)
            assert response.status_code == 200