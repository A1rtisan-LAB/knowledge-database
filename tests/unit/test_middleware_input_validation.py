"""Comprehensive unit tests for InputValidationMiddleware."""

import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest
from fastapi import Request, Response, HTTPException, status
from starlette.datastructures import Headers

from app.middleware.input_validation import InputValidationMiddleware


@pytest.mark.asyncio
class TestInputValidationMiddleware:
    """Test InputValidationMiddleware functionality."""
    
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
        request.url.query = ""
        request.headers = Headers({})
        request.path_params = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request
    
    @pytest.fixture
    def mock_response(self):
        """Create mock response."""
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}
        return response
    
    @pytest.fixture
    def middleware_strict(self, mock_app):
        """Create InputValidationMiddleware instance in strict mode."""
        return InputValidationMiddleware(mock_app, strict_mode=True)
    
    @pytest.fixture
    def middleware_lenient(self, mock_app):
        """Create InputValidationMiddleware instance in lenient mode."""
        return InputValidationMiddleware(mock_app, strict_mode=False)
    
    async def test_dispatch_clean_request(self, middleware_strict, mock_request, mock_response):
        """Test processing clean request without validation issues."""
        async def call_next(request):
            return mock_response
        
        response = await middleware_strict.dispatch(mock_request, call_next)
        
        # Verify security headers are added
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    
    async def test_skip_paths(self, middleware_strict, mock_response):
        """Test that certain paths skip validation."""
        skip_paths = ["/docs", "/openapi.json", "/redoc", "/health", "/api/v1/files/upload"]
        
        for path in skip_paths:
            request = Mock(spec=Request)
            request.url = Mock()
            request.url.path = path
            
            async def call_next(req):
                return mock_response
            
            response = await middleware_strict.dispatch(request, call_next)
            assert response == mock_response
    
    async def test_validate_headers_size_limit(self, middleware_strict, mock_request):
        """Test header size validation."""
        # Create headers that exceed the limit
        large_header = "x" * 5000
        mock_request.headers = Headers({
            "large-header": large_header,
            "another-header": "x" * 4000  # Total > 8000
        })
        
        async def call_next(request):
            return Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware_strict.dispatch(mock_request, call_next)
        
        assert exc_info.value.status_code == status.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE
        assert "too large" in exc_info.value.detail.lower()
    
    async def test_validate_headers_malicious_patterns(self, middleware_strict, mock_request):
        """Test detection of malicious patterns in headers."""
        malicious_headers = [
            {"evil-header": "value\r\nSet-Cookie: evil=true"},  # CRLF injection
            {"xss-header": "<script>alert('xss')</script>"},  # XSS
            {"path-header": "../../etc/passwd"},  # Path traversal
            {"js-header": "javascript:alert(1)"},  # JavaScript injection
        ]
        
        async def call_next(request):
            return Mock()
        
        for headers_dict in malicious_headers:
            mock_request.headers = Headers(headers_dict)
            
            with pytest.raises(HTTPException) as exc_info:
                await middleware_strict.dispatch(mock_request, call_next)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid header value" in exc_info.value.detail
    
    async def test_validate_query_params_length(self, middleware_strict, mock_request):
        """Test query parameter length validation."""
        # Create query string that exceeds the limit
        mock_request.url.query = "q=" + "x" * 2001  # > 2000 character limit
        
        async def call_next(request):
            return Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware_strict.dispatch(mock_request, call_next)
        
        assert exc_info.value.status_code == status.HTTP_414_REQUEST_URI_TOO_LONG
        assert "too long" in exc_info.value.detail.lower()
    
    async def test_validate_query_params_sql_injection(self, middleware_strict, mock_request):
        """Test SQL injection detection in query parameters."""
        with patch('app.middleware.input_validation.validate_sql_input', return_value=False):
            mock_request.url.query = "id=1 OR 1=1"
            
            async def call_next(request):
                return Mock()
            
            with pytest.raises(HTTPException) as exc_info:
                await middleware_strict.dispatch(mock_request, call_next)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "malicious" in exc_info.value.detail.lower()
    
    async def test_validate_query_params_xss(self, middleware_strict, mock_request):
        """Test XSS detection in query parameters."""
        with patch('app.middleware.input_validation.validate_xss_input', return_value=False):
            mock_request.url.query = "search=<script>alert('xss')</script>"
            
            async def call_next(request):
                return Mock()
            
            with pytest.raises(HTTPException) as exc_info:
                await middleware_strict.dispatch(mock_request, call_next)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "malicious" in exc_info.value.detail.lower()
    
    async def test_validate_path_params_uuid(self, middleware_strict, mock_request, mock_response):
        """Test UUID validation in path parameters."""
        # Valid UUID
        mock_request.path_params = {"item_id": "550e8400-e29b-41d4-a716-446655440000"}
        
        with patch('app.middleware.input_validation.validate_uuid', return_value=True):
            async def call_next(request):
                return mock_response
            
            response = await middleware_strict.dispatch(mock_request, call_next)
            assert response == mock_response
        
        # Invalid UUID
        mock_request.path_params = {"item_id": "invalid-uuid-format-here"}
        
        with patch('app.middleware.input_validation.validate_uuid', return_value=False):
            async def call_next(request):
                return mock_response
            
            with pytest.raises(HTTPException) as exc_info:
                await middleware_strict.dispatch(mock_request, call_next)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid UUID" in exc_info.value.detail
    
    async def test_validate_path_params_slug(self, middleware_strict, mock_request, mock_response):
        """Test slug validation in path parameters."""
        # Valid slug
        mock_request.path_params = {"category_slug": "valid-slug-123"}
        
        with patch('app.middleware.input_validation.validate_slug', return_value=True):
            async def call_next(request):
                return mock_response
            
            response = await middleware_strict.dispatch(mock_request, call_next)
            assert response == mock_response
        
        # Invalid slug
        mock_request.path_params = {"category_slug": "invalid slug with spaces"}
        
        with patch('app.middleware.input_validation.validate_slug', return_value=False):
            async def call_next(request):
                return mock_response
            
            with pytest.raises(HTTPException) as exc_info:
                await middleware_strict.dispatch(mock_request, call_next)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid slug" in exc_info.value.detail
    
    async def test_validate_path_params_injection(self, middleware_strict, mock_request):
        """Test injection detection in path parameters."""
        mock_request.path_params = {"param": "'; DROP TABLE users; --"}
        
        with patch('app.middleware.input_validation.validate_sql_input', return_value=False):
            async def call_next(request):
                return Mock()
            
            with pytest.raises(HTTPException) as exc_info:
                await middleware_strict.dispatch(mock_request, call_next)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "malicious" in exc_info.value.detail.lower()
    
    async def test_validate_body_json(self, middleware_strict, mock_request, mock_response):
        """Test JSON body validation."""
        mock_request.method = "POST"
        mock_request.headers = Headers({"content-type": "application/json"})
        
        # Valid JSON
        valid_body = json.dumps({"name": "test", "value": 123})
        mock_request.body = AsyncMock(return_value=valid_body.encode())
        
        async def call_next(request):
            return mock_response
        
        response = await middleware_strict.dispatch(mock_request, call_next)
        assert response == mock_response
    
    async def test_validate_body_invalid_json(self, middleware_strict, mock_request):
        """Test invalid JSON body detection."""
        mock_request.method = "POST"
        mock_request.headers = Headers({"content-type": "application/json"})
        mock_request.body = AsyncMock(return_value=b"{'invalid': json}")
        
        async def call_next(request):
            return Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware_strict.dispatch(mock_request, call_next)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid JSON" in exc_info.value.detail
    
    async def test_validate_body_size_limit(self, middleware_strict, mock_request):
        """Test body size validation."""
        mock_request.method = "POST"
        mock_request.headers = Headers({"content-type": "application/json"})
        
        # Create body that exceeds 10MB limit
        large_body = b"x" * (11 * 1024 * 1024)
        mock_request.body = AsyncMock(return_value=large_body)
        
        async def call_next(request):
            return Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware_strict.dispatch(mock_request, call_next)
        
        assert exc_info.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert "too large" in exc_info.value.detail.lower()
    
    async def test_validate_json_data_depth(self, middleware_strict, mock_request):
        """Test JSON depth validation to prevent DoS."""
        mock_request.method = "POST"
        mock_request.headers = Headers({"content-type": "application/json"})
        
        # Create deeply nested JSON (depth > 10)
        deep_json = {"level": 1}
        current = deep_json
        for i in range(11):
            current["nested"] = {"level": i + 2}
            current = current["nested"]
        
        mock_request.body = AsyncMock(return_value=json.dumps(deep_json).encode())
        
        async def call_next(request):
            return Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware_strict.dispatch(mock_request, call_next)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "too deep" in exc_info.value.detail.lower()
    
    async def test_validate_json_data_malicious_keys(self, middleware_strict, mock_request):
        """Test detection of malicious patterns in JSON keys."""
        mock_request.method = "POST"
        mock_request.headers = Headers({"content-type": "application/json"})
        
        malicious_json = {
            "<script>alert('xss')</script>": "value",
            "normal_key": "normal_value"
        }
        
        mock_request.body = AsyncMock(return_value=json.dumps(malicious_json).encode())
        
        with patch('app.middleware.input_validation.validate_xss_input', return_value=False):
            async def call_next(request):
                return Mock()
            
            with pytest.raises(HTTPException) as exc_info:
                await middleware_strict.dispatch(mock_request, call_next)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "malicious JSON key" in exc_info.value.detail
    
    async def test_validate_json_data_malicious_values(self, middleware_strict, mock_request, mock_response):
        """Test detection of malicious patterns in JSON values."""
        mock_request.method = "POST"
        mock_request.headers = Headers({"content-type": "application/json"})
        
        malicious_json = {
            "query": "SELECT * FROM users WHERE 1=1"
        }
        
        mock_request.body = AsyncMock(return_value=json.dumps(malicious_json).encode())
        
        with patch('app.middleware.input_validation.validate_sql_input', return_value=False):
            with patch('app.middleware.input_validation.logger') as mock_logger:
                async def call_next(request):
                    return mock_response
                
                # In strict mode, it logs but allows through (as per implementation)
                response = await middleware_strict.dispatch(mock_request, call_next)
                assert response == mock_response
                mock_logger.warning.assert_called()
    
    async def test_lenient_mode(self, middleware_lenient, mock_request, mock_response):
        """Test that lenient mode allows suspicious patterns through."""
        mock_request.headers = Headers({"suspicious": "../../etc/passwd"})
        
        async def call_next(request):
            return mock_response
        
        # Should not raise exception in lenient mode
        response = await middleware_lenient.dispatch(mock_request, call_next)
        assert response == mock_response
    
    async def test_form_data_validation(self, middleware_strict, mock_request, mock_response):
        """Test form data validation."""
        mock_request.method = "POST"
        mock_request.headers = Headers({"content-type": "application/x-www-form-urlencoded"})
        mock_request.body = AsyncMock(return_value=b"username=test&password=secret")
        
        async def call_next(request):
            return mock_response
        
        response = await middleware_strict.dispatch(mock_request, call_next)
        assert response == mock_response
    
    async def test_non_validated_content_types(self, middleware_strict, mock_request, mock_response):
        """Test that non-JSON/form content types skip body validation."""
        mock_request.method = "POST"
        mock_request.headers = Headers({"content-type": "multipart/form-data"})
        
        async def call_next(request):
            return mock_response
        
        # Should skip body validation for multipart
        response = await middleware_strict.dispatch(mock_request, call_next)
        assert response == mock_response
    
    async def test_validate_json_arrays(self, middleware_strict, mock_request, mock_response):
        """Test validation of JSON arrays."""
        mock_request.method = "POST"
        mock_request.headers = Headers({"content-type": "application/json"})
        
        json_array = [
            {"name": "item1", "value": 1},
            {"name": "item2", "value": 2},
            {"name": "item3", "value": 3}
        ]
        
        mock_request.body = AsyncMock(return_value=json.dumps(json_array).encode())
        
        async def call_next(request):
            return mock_response
        
        response = await middleware_strict.dispatch(mock_request, call_next)
        assert response == mock_response
    
    async def test_http_methods_without_body(self, middleware_strict, mock_request, mock_response):
        """Test that GET, DELETE, etc. don't trigger body validation."""
        methods = ["GET", "DELETE", "HEAD", "OPTIONS"]
        
        for method in methods:
            mock_request.method = method
            
            async def call_next(request):
                return mock_response
            
            response = await middleware_strict.dispatch(mock_request, call_next)
            assert response == mock_response
    
    async def test_exception_during_validation(self, middleware_strict, mock_request):
        """Test handling of unexpected exceptions during validation."""
        mock_request.method = "POST"
        mock_request.headers = Headers({"content-type": "application/json"})
        mock_request.body = AsyncMock(side_effect=Exception("Unexpected error"))
        
        with patch('app.middleware.input_validation.logger') as mock_logger:
            async def call_next(request):
                return Mock()
            
            with pytest.raises(HTTPException) as exc_info:
                await middleware_strict.dispatch(mock_request, call_next)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid request body" in exc_info.value.detail
            mock_logger.error.assert_called()
    
    async def test_logging_validation_failures(self, middleware_strict, mock_request):
        """Test that validation failures are logged."""
        mock_request.url.query = "q=" + "x" * 2001
        
        with patch('app.middleware.input_validation.logger') as mock_logger:
            async def call_next(request):
                return Mock()
            
            with pytest.raises(HTTPException):
                await middleware_strict.dispatch(mock_request, call_next)
            
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args
            assert "validation failed" in warning_call[0][0].lower()
    
    async def test_empty_query_params(self, middleware_strict, mock_request, mock_response):
        """Test that empty query parameters are handled correctly."""
        mock_request.url.query = ""
        
        async def call_next(request):
            return mock_response
        
        response = await middleware_strict.dispatch(mock_request, call_next)
        assert response == mock_response
    
    async def test_unicode_in_parameters(self, middleware_strict, mock_request, mock_response):
        """Test handling of Unicode characters in parameters."""
        mock_request.path_params = {"name": "用户名"}
        mock_request.url.query = "search=テスト"
        
        async def call_next(request):
            return mock_response
        
        # Should handle Unicode properly
        response = await middleware_strict.dispatch(mock_request, call_next)
        assert response == mock_response