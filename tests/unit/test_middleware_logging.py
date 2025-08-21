"""Comprehensive unit tests for LoggingMiddleware."""

import asyncio
import time
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
import pytest
from fastapi import Request, Response
from starlette.datastructures import Headers
import structlog

from app.middleware.logging import LoggingMiddleware


@pytest.mark.asyncio
class TestLoggingMiddleware:
    """Test LoggingMiddleware functionality."""
    
    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI app."""
        return Mock()
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request with all necessary attributes."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/v1/knowledge"
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
    def middleware(self, mock_app):
        """Create LoggingMiddleware instance."""
        return LoggingMiddleware(mock_app)
    
    async def test_dispatch_successful_request(self, middleware, mock_request, mock_response):
        """Test successful request processing with logging."""
        with patch('app.middleware.logging.logger') as mock_logger:
            with patch('app.middleware.logging.uuid.uuid4', return_value='test-uuid-123'):
                async def call_next(request):
                    return mock_response
                
                response = await middleware.dispatch(mock_request, call_next)
                
                # Verify request ID was set
                assert mock_request.state.request_id == 'test-uuid-123'
                
                # Verify response headers include request ID
                assert response.headers["X-Request-ID"] == 'test-uuid-123'
                
                # Verify logging calls
                assert mock_logger.info.call_count == 2
                
                # Check first log (request started)
                first_call = mock_logger.info.call_args_list[0]
                assert first_call[0][0] == "Request started"
                assert first_call[1]["request_id"] == 'test-uuid-123'
                assert first_call[1]["method"] == "GET"
                assert first_call[1]["path"] == "/api/v1/knowledge"
                assert first_call[1]["client"] == "127.0.0.1"
                
                # Check second log (request completed)
                second_call = mock_logger.info.call_args_list[1]
                assert second_call[0][0] == "Request completed"
                assert second_call[1]["request_id"] == 'test-uuid-123'
                assert second_call[1]["status_code"] == 200
                assert "duration_ms" in second_call[1]
    
    async def test_dispatch_with_exception(self, middleware, mock_request):
        """Test exception handling during request processing."""
        with patch('app.middleware.logging.logger') as mock_logger:
            with patch('app.middleware.logging.uuid.uuid4', return_value='error-uuid-456'):
                async def call_next(request):
                    raise ValueError("Test error")
                
                with pytest.raises(ValueError, match="Test error"):
                    await middleware.dispatch(mock_request, call_next)
                
                # Verify error logging
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args
                assert error_call[0][0] == "Request failed"
                assert error_call[1]["request_id"] == 'error-uuid-456'
                assert error_call[1]["error"] == "Test error"
                assert error_call[1]["exc_info"] is True
    
    async def test_dispatch_no_client(self, middleware, mock_response):
        """Test request without client information."""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.client = None  # No client info
        request.state = Mock()
        
        with patch('app.middleware.logging.logger') as mock_logger:
            async def call_next(req):
                return mock_response
            
            response = await middleware.dispatch(request, call_next)
            
            # Check that client is None in logs
            first_call = mock_logger.info.call_args_list[0]
            assert first_call[1]["client"] is None
    
    async def test_duration_calculation(self, middleware, mock_request, mock_response):
        """Test accurate duration calculation."""
        with patch('app.middleware.logging.logger') as mock_logger:
            with patch('app.middleware.logging.time.time') as mock_time:
                # Mock time progression
                mock_time.side_effect = [1000.0, 1000.5]  # 500ms duration
                
                async def call_next(request):
                    return mock_response
                
                await middleware.dispatch(mock_request, call_next)
                
                # Check duration in completed log
                second_call = mock_logger.info.call_args_list[1]
                assert second_call[1]["duration_ms"] == 500
    
    async def test_multiple_concurrent_requests(self, middleware):
        """Test handling multiple concurrent requests with unique IDs."""
        request_ids = []
        
        async def process_request(path):
            request = Mock(spec=Request)
            request.method = "GET"
            request.url = Mock()
            request.url.path = path
            request.client = Mock()
            request.client.host = "127.0.0.1"
            request.state = Mock()
            
            response = Mock(spec=Response)
            response.status_code = 200
            response.headers = {}
            
            async def call_next(req):
                await asyncio.sleep(0.01)  # Simulate processing
                return response
            
            await middleware.dispatch(request, call_next)
            request_ids.append(request.state.request_id)
            return request.state.request_id
        
        # Process multiple requests concurrently
        tasks = [process_request(f"/api/v1/test{i}") for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Verify all request IDs are unique
        assert len(set(results)) == 5
        assert len(request_ids) == 5
    
    async def test_request_id_generation(self, middleware, mock_request, mock_response):
        """Test UUID generation for request ID."""
        with patch('app.middleware.logging.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
            
            async def call_next(request):
                return mock_response
            
            await middleware.dispatch(mock_request, call_next)
            
            assert mock_request.state.request_id == '12345678-1234-5678-1234-567812345678'
            mock_uuid.assert_called_once()
    
    async def test_response_header_modification(self, middleware, mock_request):
        """Test that response headers are properly modified."""
        response = Mock(spec=Response)
        response.status_code = 201
        response.headers = {"Content-Type": "application/json"}
        
        async def call_next(request):
            return response
        
        result = await middleware.dispatch(mock_request, call_next)
        
        # Check that X-Request-ID header was added
        assert "X-Request-ID" in result.headers
        # Check that original headers are preserved
        assert result.headers["Content-Type"] == "application/json"
    
    async def test_various_http_methods(self, middleware, mock_response):
        """Test middleware with various HTTP methods."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
        
        for method in methods:
            request = Mock(spec=Request)
            request.method = method
            request.url = Mock()
            request.url.path = f"/api/v1/{method.lower()}"
            request.client = Mock()
            request.client.host = "127.0.0.1"
            request.state = Mock()
            
            with patch('app.middleware.logging.logger') as mock_logger:
                async def call_next(req):
                    return mock_response
                
                await middleware.dispatch(request, call_next)
                
                # Verify method is logged correctly
                first_call = mock_logger.info.call_args_list[0]
                assert first_call[1]["method"] == method
    
    async def test_various_status_codes(self, middleware, mock_request):
        """Test middleware with various response status codes."""
        status_codes = [200, 201, 204, 301, 400, 401, 403, 404, 500, 502]
        
        for status_code in status_codes:
            response = Mock(spec=Response)
            response.status_code = status_code
            response.headers = {}
            
            with patch('app.middleware.logging.logger') as mock_logger:
                async def call_next(request):
                    return response
                
                await middleware.dispatch(mock_request, call_next)
                
                # Verify status code is logged correctly
                second_call = mock_logger.info.call_args_list[1]
                assert second_call[1]["status_code"] == status_code
    
    async def test_exception_during_logging(self, middleware, mock_request, mock_response):
        """Test that exceptions in logging don't break request processing."""
        with patch('app.middleware.logging.logger.info') as mock_info:
            mock_info.side_effect = [Exception("Logging failed"), None]
            
            async def call_next(request):
                return mock_response
            
            # Should still process request despite logging failure
            response = await middleware.dispatch(mock_request, call_next)
            assert response == mock_response
    
    async def test_long_running_request(self, middleware, mock_request, mock_response):
        """Test logging for long-running requests."""
        with patch('app.middleware.logging.logger') as mock_logger:
            with patch('app.middleware.logging.time.time') as mock_time:
                # Mock a 5-second request
                mock_time.side_effect = [1000.0, 1005.0]
                
                async def call_next(request):
                    return mock_response
                
                await middleware.dispatch(mock_request, call_next)
                
                # Check duration
                second_call = mock_logger.info.call_args_list[1]
                assert second_call[1]["duration_ms"] == 5000
    
    async def test_path_with_query_params(self, middleware, mock_response):
        """Test logging paths with query parameters."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/v1/search"
        request.url.query = "q=test&limit=10"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = Mock()
        
        with patch('app.middleware.logging.logger') as mock_logger:
            async def call_next(req):
                return mock_response
            
            await middleware.dispatch(request, call_next)
            
            # Verify path is logged correctly (without query params)
            first_call = mock_logger.info.call_args_list[0]
            assert first_call[1]["path"] == "/api/v1/search"
    
    async def test_exception_types(self, middleware, mock_request):
        """Test different exception types are handled correctly."""
        exceptions = [
            ValueError("Value error"),
            KeyError("Key error"),
            RuntimeError("Runtime error"),
            Exception("Generic exception"),
            TypeError("Type error")
        ]
        
        for exc in exceptions:
            with patch('app.middleware.logging.logger') as mock_logger:
                async def call_next(request):
                    raise exc
                
                with pytest.raises(type(exc)):
                    await middleware.dispatch(mock_request, call_next)
                
                # Verify error is logged with correct message
                error_call = mock_logger.error.call_args
                assert error_call[1]["error"] == str(exc)
                assert error_call[1]["exc_info"] is True