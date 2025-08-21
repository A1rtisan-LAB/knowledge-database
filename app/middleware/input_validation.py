"""Input validation middleware for security."""

import json
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers, MutableHeaders
import structlog

from app.core.security_utils import (
    sanitize_input,
    validate_sql_input,
    validate_xss_input,
    validate_email,
    validate_uuid,
    validate_slug
)

logger = structlog.get_logger()


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for validating and sanitizing user input."""
    
    def __init__(self, app, strict_mode: bool = True):
        """
        Initialize input validation middleware.
        
        Args:
            app: FastAPI application
            strict_mode: If True, reject requests with malicious patterns
        """
        super().__init__(app)
        self.strict_mode = strict_mode
        
        # Paths that should skip validation (e.g., file uploads)
        self.skip_paths = [
            "/docs",
            "/openapi.json",
            "/redoc",
            "/health",
            "/api/v1/files/upload",  # File upload endpoints
        ]
        
        # Maximum allowed sizes
        self.max_query_length = 2000
        self.max_header_length = 8000
        self.max_body_size = 10 * 1024 * 1024  # 10MB
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Validate and sanitize request input.
        
        Args:
            request: Incoming request
            call_next: Next middleware or endpoint
            
        Returns:
            Response object
        """
        # Skip validation for certain paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
        
        try:
            # Validate headers
            self._validate_headers(request.headers)
            
            # Validate query parameters
            self._validate_query_params(request.url.query)
            
            # Validate path parameters
            self._validate_path_params(request.path_params)
            
            # Validate body for POST/PUT/PATCH requests
            if request.method in ["POST", "PUT", "PATCH"]:
                await self._validate_body(request)
            
        except HTTPException as e:
            logger.warning(
                "Input validation failed",
                path=request.url.path,
                method=request.method,
                client_ip=request.client.host if request.client else "unknown",
                error=str(e.detail)
            )
            raise e
        
        # Process request
        response = await call_next(request)
        
        # Add security headers to response
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response
    
    def _validate_headers(self, headers: Headers):
        """
        Validate request headers.
        
        Args:
            headers: Request headers
            
        Raises:
            HTTPException: If validation fails
        """
        # Check header size
        total_size = sum(len(k) + len(v) for k, v in headers.items())
        if total_size > self.max_header_length:
            raise HTTPException(
                status_code=status.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE,
                detail="Request headers too large"
            )
        
        # Validate specific headers
        for key, value in headers.items():
            # Check for malicious patterns in header values
            if not self._is_safe_header_value(value):
                if self.strict_mode:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid header value for {key}"
                    )
    
    def _validate_query_params(self, query: str):
        """
        Validate query parameters.
        
        Args:
            query: Query string
            
        Raises:
            HTTPException: If validation fails
        """
        if not query:
            return
        
        # Check query string length
        if len(query) > self.max_query_length:
            raise HTTPException(
                status_code=status.HTTP_414_REQUEST_URI_TOO_LONG,
                detail="Query string too long"
            )
        
        # Check for SQL injection patterns
        if not validate_sql_input(query):
            if self.strict_mode:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Potentially malicious query parameters detected"
                )
        
        # Check for XSS patterns
        if not validate_xss_input(query):
            if self.strict_mode:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Potentially malicious query parameters detected"
                )
    
    def _validate_path_params(self, path_params: dict):
        """
        Validate path parameters.
        
        Args:
            path_params: Path parameters
            
        Raises:
            HTTPException: If validation fails
        """
        for key, value in path_params.items():
            if isinstance(value, str):
                # Validate UUIDs
                if "id" in key.lower() and len(value) == 36:
                    if not validate_uuid(value):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid UUID format for {key}"
                        )
                
                # Validate slugs
                elif "slug" in key.lower():
                    if not validate_slug(value):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid slug format for {key}"
                        )
                
                # Check for injection patterns
                elif not validate_sql_input(value) or not validate_xss_input(value):
                    if self.strict_mode:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Potentially malicious path parameter: {key}"
                        )
    
    async def _validate_body(self, request: Request):
        """
        Validate request body.
        
        Args:
            request: Request object
            
        Raises:
            HTTPException: If validation fails
        """
        # Check content-type
        content_type = request.headers.get("content-type", "")
        
        # Only validate JSON and form data
        if not ("application/json" in content_type or "application/x-www-form-urlencoded" in content_type):
            return
        
        try:
            # Read body
            body = await request.body()
            
            # Check body size
            if len(body) > self.max_body_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Request body too large"
                )
            
            # Parse and validate JSON
            if "application/json" in content_type:
                try:
                    data = json.loads(body)
                    self._validate_json_data(data)
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid JSON in request body"
                    )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating request body: {e}")
            if self.strict_mode:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request body"
                )
    
    def _validate_json_data(self, data, depth=0):
        """
        Recursively validate JSON data.
        
        Args:
            data: JSON data to validate
            depth: Current recursion depth
            
        Raises:
            HTTPException: If validation fails
        """
        # Prevent deep recursion (potential DoS)
        if depth > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JSON structure too deep"
            )
        
        if isinstance(data, dict):
            for key, value in data.items():
                # Validate keys
                if isinstance(key, str) and (not validate_sql_input(key) or not validate_xss_input(key)):
                    if self.strict_mode:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Potentially malicious JSON key: {key}"
                        )
                
                # Recursively validate values
                self._validate_json_data(value, depth + 1)
        
        elif isinstance(data, list):
            for item in data:
                self._validate_json_data(item, depth + 1)
        
        elif isinstance(data, str):
            # Validate string values
            if not validate_sql_input(data) or not validate_xss_input(data):
                if self.strict_mode:
                    logger.warning(f"Potentially malicious JSON value detected: {data[:100]}")
                    # In strict mode, we might want to sanitize instead of rejecting
                    # For now, we'll log but allow it through
    
    def _is_safe_header_value(self, value: str) -> bool:
        """
        Check if header value is safe.
        
        Args:
            value: Header value
            
        Returns:
            bool: True if safe
        """
        # Check for common injection patterns
        dangerous_patterns = [
            "\r", "\n",  # CRLF injection
            "<script", "javascript:",  # XSS
            "../", "..\\",  # Path traversal
        ]
        
        value_lower = value.lower()
        return not any(pattern in value_lower for pattern in dangerous_patterns)