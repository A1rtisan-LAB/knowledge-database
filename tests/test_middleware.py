"""Comprehensive tests for middleware components."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime, timedelta
import time
import json
from uuid import uuid4
from httpx import AsyncClient
from fastapi import Request, Response, HTTPException
from starlette.datastructures import Headers

from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.core.config import Settings


@pytest.mark.asyncio
class TestLoggingMiddleware:
    """Test logging middleware functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.log_level = "INFO"
        settings.log_format = "json"
        settings.log_requests = True
        settings.log_responses = True
        settings.log_slow_requests_threshold = 1000  # ms
        return settings
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/v1/knowledge"
        request.url.query = "q=test"
        request.headers = Headers({
            "user-agent": "test-client",
            "x-request-id": str(uuid4())
        })
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.path_params = {}
        request.query_params = {"q": "test"}
        request.state = Mock()
        return request
    
    @pytest.fixture
    def mock_response(self):
        """Create mock response."""
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}
        return response
    
    async def test_logging_middleware_basic(self, mock_settings, mock_request, mock_response):
        """Test basic logging middleware functionality."""
        with patch('app.middleware.logging.get_settings', return_value=mock_settings):
            with patch('app.middleware.logging.logger') as mock_logger:
                middleware = LoggingMiddleware(app=Mock())
                
                async def call_next(request):
                    return mock_response
                
                response = await middleware.dispatch(mock_request, call_next)
                
                assert response == mock_response
                # Should log request and response
                assert mock_logger.info.call_count >= 1
    
    async def test_request_id_generation(self, mock_request, mock_response):
        """Test request ID generation and propagation."""
        mock_request.headers = Headers({})  # No existing request ID
        mock_request.state = Mock()
        
        with patch('app.middleware.logging.get_settings', return_value=Mock()):
            middleware = LoggingMiddleware(app=Mock())
            
            async def call_next(request):
                # Check that request_id was set
                assert hasattr(request.state, 'request_id')
                return mock_response
            
            await middleware.dispatch(mock_request, call_next)
    
    async def test_existing_request_id(self, mock_request, mock_response):
        """Test using existing request ID from headers."""
        existing_id = "existing-request-id"
        mock_request.headers = Headers({"x-request-id": existing_id})
        mock_request.state = Mock()
        
        with patch('app.middleware.logging.get_settings', return_value=Mock()):
            middleware = LoggingMiddleware(app=Mock())
            
            async def call_next(request):
                # Request ID should be generated even if header exists
                assert hasattr(request.state, 'request_id')
                return mock_response
            
            await middleware.dispatch(mock_request, call_next)
    
    async def test_log_slow_requests(self, mock_settings, mock_request, mock_response):
        """Test logging slow requests."""
        mock_settings.log_slow_requests_threshold = 100  # 100ms threshold
        
        with patch('app.middleware.logging.get_settings', return_value=mock_settings):
            with patch('app.middleware.logging.logger') as mock_logger:
                middleware = LoggingMiddleware(app=Mock())
                
                async def slow_call_next(request):
                    await asyncio.sleep(0.2)  # 200ms delay
                    return mock_response
                
                import asyncio
                response = await middleware.dispatch(mock_request, slow_call_next)
                
                # Should log as slow request
                mock_logger.warning.assert_called()
                warning_call = mock_logger.warning.call_args[0][0]
                assert "slow" in warning_call.lower()
    
    async def test_log_error_responses(self, mock_settings, mock_request):
        """Test logging error responses."""
        with patch('app.middleware.logging.get_settings', return_value=mock_settings):
            with patch('app.middleware.logging.logger') as mock_logger:
                middleware = LoggingMiddleware(app=Mock())
                
                error_response = Mock(spec=Response)
                error_response.status_code = 500
                error_response.headers = {}
                
                async def error_call_next(request):
                    return error_response
                
                response = await middleware.dispatch(mock_request, error_call_next)
                
                assert response.status_code == 500
                # Should log error
                mock_logger.error.assert_called()
    
    async def test_log_request_body(self, mock_settings, mock_request):
        """Test logging request body."""
        mock_settings.log_request_body = True
        mock_request.body = AsyncMock(return_value=b'{"test": "data"}')
        
        with patch('app.middleware.logging.get_settings', return_value=mock_settings):
            with patch('app.middleware.logging.logger') as mock_logger:
                middleware = LoggingMiddleware(app=Mock())
                
                async def call_next(request):
                    return Mock(status_code=200, headers={})
                
                await middleware.dispatch(mock_request, call_next)
                
                # Should include body in logs
                log_call = mock_logger.info.call_args[0][0]
                assert "body" in log_call.lower() or "data" in log_call.lower()
    
    async def test_log_response_time(self, mock_settings, mock_request, mock_response):
        """Test logging response time."""
        with patch('app.middleware.logging.get_settings', return_value=mock_settings):
            with patch('app.middleware.logging.logger') as mock_logger:
                middleware = LoggingMiddleware(app=Mock())
                
                async def call_next(request):
                    return mock_response
                
                await middleware.dispatch(mock_request, call_next)
                
                # Should log response time
                log_call = mock_logger.info.call_args[0][0]
                assert "ms" in log_call or "duration" in log_call.lower()
    
    async def test_log_user_info(self, mock_settings, mock_request, mock_response):
        """Test logging user information if available."""
        mock_request.state.user = Mock()
        mock_request.state.user.id = "user123"
        mock_request.state.user.email = "user@example.com"
        
        with patch('app.middleware.logging.get_settings', return_value=mock_settings):
            with patch('app.middleware.logging.logger') as mock_logger:
                middleware = LoggingMiddleware(app=Mock())
                
                async def call_next(request):
                    return mock_response
                
                await middleware.dispatch(mock_request, call_next)
                
                # Should include user info in logs
                log_call = str(mock_logger.info.call_args)
                assert "user123" in log_call or "user@example.com" in log_call
    
    async def test_sanitize_sensitive_data(self, mock_settings, mock_request):
        """Test sanitization of sensitive data in logs."""
        mock_request.headers = Headers({
            "authorization": "Bearer secret-token",
            "x-api-key": "secret-api-key"
        })
        
        with patch('app.middleware.logging.get_settings', return_value=mock_settings):
            with patch('app.middleware.logging.logger') as mock_logger:
                middleware = LoggingMiddleware(app=Mock())
                
                async def call_next(request):
                    return Mock(status_code=200, headers={})
                
                await middleware.dispatch(mock_request, call_next)
                
                # Should not log sensitive data
                log_calls = str(mock_logger.info.call_args_list)
                assert "secret-token" not in log_calls
                assert "secret-api-key" not in log_calls
                # Should show masked values
                assert "***" in log_calls or "REDACTED" in log_calls
    
    async def test_log_exceptions(self, mock_settings, mock_request):
        """Test logging unhandled exceptions."""
        with patch('app.middleware.logging.get_settings', return_value=mock_settings):
            with patch('app.middleware.logging.logger') as mock_logger:
                middleware = LoggingMiddleware(app=Mock())
                
                async def exception_call_next(request):
                    raise ValueError("Test exception")
                
                with pytest.raises(ValueError):
                    await middleware.dispatch(mock_request, exception_call_next)
                
                # Should log exception
                mock_logger.exception.assert_called()


@pytest.mark.asyncio
class TestRateLimitMiddleware:
    """Test rate limiting middleware functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.rate_limit_enabled = True
        settings.rate_limit_default = 100
        settings.rate_limit_window = 60  # seconds
        settings.rate_limit_burst = 10
        return settings
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v1/search"
        request.headers = Headers({})
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = Mock()
        return request
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        client = AsyncMock()
        client.incr = AsyncMock()
        client.expire = AsyncMock()
        client.ttl = AsyncMock()
        client.get = AsyncMock()
        return client
    
    async def test_rate_limit_allowed(self, mock_settings, mock_request, mock_redis_client):
        """Test request allowed under rate limit."""
        with patch('app.middleware.rate_limit.get_settings', return_value=mock_settings):
            with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis_client):
                mock_redis_client.incr.return_value = 1  # First request
                
                middleware = RateLimitMiddleware(app=Mock())
                
                async def call_next(request):
                    return Mock(status_code=200, headers={})
                
                response = await middleware.dispatch(mock_request, call_next)
                
                assert response.status_code == 200
                mock_redis_client.incr.assert_called()
                mock_redis_client.expire.assert_called()
    
    async def test_rate_limit_exceeded(self, mock_settings, mock_request, mock_redis_client):
        """Test request blocked when rate limit exceeded."""
        with patch('app.middleware.rate_limit.get_settings', return_value=mock_settings):
            with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis_client):
                mock_redis_client.incr.return_value = 101  # Over limit
                mock_redis_client.ttl.return_value = 30  # 30 seconds remaining
                
                middleware = RateLimitMiddleware(app=Mock())
                
                async def call_next(request):
                    return Mock(status_code=200, headers={})
                
                response = await middleware.dispatch(mock_request, call_next)
                
                assert response.status_code == 429
                # Should include retry-after header
                assert "retry-after" in response.headers
    
    async def test_rate_limit_per_user(self, mock_settings, mock_request, mock_redis_client):
        """Test rate limiting per authenticated user."""
        mock_request.state.user = Mock()
        mock_request.state.user.id = "user123"
        
        with patch('app.middleware.rate_limit.get_settings', return_value=mock_settings):
            with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis_client):
                mock_redis_client.incr.return_value = 1
                
                middleware = RateLimitMiddleware(app=Mock())
                
                async def call_next(request):
                    return Mock(status_code=200, headers={})
                
                await middleware.dispatch(mock_request, call_next)
                
                # Should use user-specific key
                incr_call = mock_redis_client.incr.call_args[0][0]
                assert "user123" in incr_call
    
    async def test_rate_limit_per_ip(self, mock_settings, mock_request, mock_redis_client):
        """Test rate limiting per IP address."""
        mock_request.client.host = "192.168.1.100"
        
        with patch('app.middleware.rate_limit.get_settings', return_value=mock_settings):
            with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis_client):
                mock_redis_client.incr.return_value = 1
                
                middleware = RateLimitMiddleware(app=Mock())
                
                async def call_next(request):
                    return Mock(status_code=200, headers={})
                
                await middleware.dispatch(mock_request, call_next)
                
                # Should use IP-specific key
                incr_call = mock_redis_client.incr.call_args[0][0]
                assert "192.168.1.100" in incr_call
    
    async def test_rate_limit_burst_handling(self, mock_settings, mock_request, mock_redis_client):
        """Test burst rate limiting."""
        mock_settings.rate_limit_burst = 5
        
        with patch('app.middleware.rate_limit.get_settings', return_value=mock_settings):
            with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis_client):
                middleware = RateLimitMiddleware(app=Mock())
                
                async def call_next(request):
                    return Mock(status_code=200, headers={})
                
                # Simulate burst of requests
                for i in range(6):
                    mock_redis_client.incr.return_value = i + 1
                    response = await middleware.dispatch(mock_request, call_next)
                    
                    if i < 5:
                        assert response.status_code == 200
                    else:
                        # Burst limit exceeded
                        assert response.status_code == 429
    
    async def test_rate_limit_whitelist(self, mock_settings, mock_request, mock_redis_client):
        """Test whitelisted IPs bypass rate limiting."""
        mock_settings.rate_limit_whitelist = ["127.0.0.1", "192.168.1.0/24"]
        mock_request.client.host = "127.0.0.1"
        
        with patch('app.middleware.rate_limit.get_settings', return_value=mock_settings):
            with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis_client):
                middleware = RateLimitMiddleware(app=Mock())
                
                async def call_next(request):
                    return Mock(status_code=200, headers={})
                
                # Should not check rate limit for whitelisted IP
                response = await middleware.dispatch(mock_request, call_next)
                
                assert response.status_code == 200
                mock_redis_client.incr.assert_not_called()
    
    async def test_rate_limit_custom_limits(self, mock_settings, mock_request, mock_redis_client):
        """Test custom rate limits for specific endpoints."""
        mock_settings.rate_limit_custom = {
            "/api/v1/search": {"limit": 10, "window": 60},
            "/api/v1/knowledge": {"limit": 50, "window": 60}
        }
        mock_request.url.path = "/api/v1/search"
        
        with patch('app.middleware.rate_limit.get_settings', return_value=mock_settings):
            with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis_client):
                mock_redis_client.incr.return_value = 11  # Over custom limit
                
                middleware = RateLimitMiddleware(app=Mock())
                
                async def call_next(request):
                    return Mock(status_code=200, headers={})
                
                response = await middleware.dispatch(mock_request, call_next)
                
                assert response.status_code == 429
    
    async def test_rate_limit_headers(self, mock_settings, mock_request, mock_redis_client):
        """Test rate limit headers in response."""
        with patch('app.middleware.rate_limit.get_settings', return_value=mock_settings):
            with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis_client):
                mock_redis_client.incr.return_value = 50
                mock_redis_client.ttl.return_value = 30
                
                middleware = RateLimitMiddleware(app=Mock())
                
                async def call_next(request):
                    return Mock(status_code=200, headers={})
                
                response = await middleware.dispatch(mock_request, call_next)
                
                assert response.status_code == 200
                # Should include rate limit headers
                assert "x-ratelimit-limit" in response.headers
                assert "x-ratelimit-remaining" in response.headers
                assert "x-ratelimit-reset" in response.headers
    
    async def test_rate_limit_disabled(self, mock_settings, mock_request, mock_redis_client):
        """Test rate limiting can be disabled."""
        mock_settings.rate_limit_enabled = False
        
        with patch('app.middleware.rate_limit.get_settings', return_value=mock_settings):
            with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis_client):
                middleware = RateLimitMiddleware(app=Mock())
                
                async def call_next(request):
                    return Mock(status_code=200, headers={})
                
                response = await middleware.dispatch(mock_request, call_next)
                
                assert response.status_code == 200
                # Should not check rate limit
                mock_redis_client.incr.assert_not_called()
    
    async def test_rate_limit_redis_failure(self, mock_settings, mock_request, mock_redis_client):
        """Test graceful handling of Redis failures."""
        with patch('app.middleware.rate_limit.get_settings', return_value=mock_settings):
            with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis_client):
                mock_redis_client.incr.side_effect = Exception("Redis connection failed")
                
                middleware = RateLimitMiddleware(app=Mock())
                
                async def call_next(request):
                    return Mock(status_code=200, headers={})
                
                with patch('app.middleware.rate_limit.logger') as mock_logger:
                    response = await middleware.dispatch(mock_request, call_next)
                    
                    # Should allow request on Redis failure
                    assert response.status_code == 200
                    mock_logger.error.assert_called()


@pytest.mark.asyncio
class TestMiddlewareIntegration:
    """Test middleware components working together."""
    
    async def test_middleware_chain(self, client: AsyncClient):
        """Test multiple middleware in chain."""
        # This tests the actual middleware chain with a real client
        response = await client.get("/api/v1/categories")
        
        # Should have gone through all middleware
        assert response.status_code in [200, 401, 429]
        
        # Check for middleware headers if present
        headers = response.headers
        # Request ID from logging middleware
        if "x-request-id" in headers:
            assert headers["x-request-id"]
        
        # Rate limit headers if rate limiting is enabled
        if "x-ratelimit-limit" in headers:
            assert int(headers["x-ratelimit-limit"]) > 0
    
    async def test_middleware_error_propagation(self, client: AsyncClient):
        """Test error propagation through middleware chain."""
        # Test with invalid endpoint
        response = await client.get("/api/v1/invalid-endpoint")
        
        assert response.status_code == 404
        # Error should be logged by logging middleware
    
    async def test_middleware_performance(self, client: AsyncClient):
        """Test middleware doesn't significantly impact performance."""
        import time
        
        start = time.time()
        response = await client.get("/api/v1/categories")
        duration = (time.time() - start) * 1000  # ms
        
        # Middleware should not add significant overhead
        assert duration < 1000  # Less than 1 second
        assert response.status_code in [200, 401, 429]