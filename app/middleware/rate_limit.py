"""Enhanced rate limiting middleware with multiple strategies."""

import time
import hashlib
import asyncio
from typing import Dict, Callable, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.services.redis import get_redis_client

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limiting middleware with Redis support and multiple strategies."""
    
    def __init__(
        self,
        app,
        requests: int = 100,
        period: int = 60,
        burst_requests: int = 10,
        burst_period: int = 1,
        use_redis: bool = True,
        by_user: bool = True,
        by_ip: bool = True,
        by_endpoint: bool = False
    ):
        """
        Initialize enhanced rate limiter.
        
        Args:
            app: FastAPI application
            requests: Maximum requests allowed in period
            period: Time period in seconds
            burst_requests: Maximum burst requests
            burst_period: Burst time period in seconds
            use_redis: Use Redis for distributed rate limiting
            by_user: Rate limit by authenticated user
            by_ip: Rate limit by IP address
            by_endpoint: Rate limit by endpoint
        """
        super().__init__(app)
        self.requests = requests
        self.period = period
        self.burst_requests = burst_requests
        self.burst_period = burst_period
        self.use_redis = use_redis
        self.by_user = by_user
        self.by_ip = by_ip
        self.by_endpoint = by_endpoint
        
        # In-memory storage as fallback
        self.clients: Dict[str, list] = {}
        self.burst_clients: Dict[str, list] = {}
        
        # Cleanup task
        self.cleanup_task = None
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check rate limit and process request with multiple strategies.
        
        Args:
            request: Incoming request
            call_next: Next middleware or endpoint
            
        Returns:
            Response object
        """
        # Skip rate limiting for health checks and documentation
        skip_paths = ["/health", "/", "/docs", "/openapi.json", "/redoc"]
        if request.url.path in skip_paths:
            return await call_next(request)
        
        # Build client identifier
        identifiers = []
        
        # IP-based identifier
        if self.by_ip:
            client_ip = self._get_client_ip(request)
            identifiers.append(f"ip:{client_ip}")
        
        # User-based identifier (if authenticated)
        if self.by_user:
            user_id = await self._get_user_id(request)
            if user_id:
                identifiers.append(f"user:{user_id}")
        
        # Endpoint-based identifier
        if self.by_endpoint:
            endpoint = f"{request.method}:{request.url.path}"
            identifiers.append(f"endpoint:{endpoint}")
        
        # Check rate limits for all identifiers
        for identifier in identifiers:
            # Check burst limit first (more restrictive)
            is_allowed, retry_after = await self._check_rate_limit(
                identifier,
                self.burst_requests,
                self.burst_period,
                is_burst=True
            )
            
            if not is_allowed:
                logger.warning(
                    "Burst rate limit exceeded",
                    identifier=identifier,
                    path=request.url.path,
                    method=request.method
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests in a short period. Please slow down.",
                    headers={"Retry-After": str(retry_after)}
                )
            
            # Check normal rate limit
            is_allowed, retry_after = await self._check_rate_limit(
                identifier,
                self.requests,
                self.period,
                is_burst=False
            )
            
            if not is_allowed:
                logger.warning(
                    "Rate limit exceeded",
                    identifier=identifier,
                    path=request.url.path,
                    method=request.method
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(retry_after)}
                )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers (for the most restrictive identifier)
        if identifiers:
            remaining = self.requests
            for identifier in identifiers:
                count = await self._get_request_count(identifier, self.period)
                remaining = min(remaining, self.requests - count)
            
            response.headers["X-RateLimit-Limit"] = str(self.requests)
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.period))
        
        return response
    
    async def _check_rate_limit(
        self,
        identifier: str,
        limit: int,
        period: int,
        is_burst: bool = False
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Client identifier
            limit: Request limit
            period: Time period in seconds
            is_burst: Whether this is a burst check
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()
        
        if self.use_redis:
            try:
                return await self._check_redis_rate_limit(identifier, limit, period)
            except Exception as e:
                logger.error(f"Redis rate limit check failed: {e}")
                # Fall back to in-memory
        
        # In-memory rate limiting
        storage = self.burst_clients if is_burst else self.clients
        
        if identifier not in storage:
            storage[identifier] = []
        
        # Clean old entries
        storage[identifier] = [
            ts for ts in storage[identifier]
            if ts > now - period
        ]
        
        # Check limit
        if len(storage[identifier]) >= limit:
            oldest = min(storage[identifier]) if storage[identifier] else now
            retry_after = int(oldest + period - now) + 1
            return False, retry_after
        
        # Add current request
        storage[identifier].append(now)
        
        # Periodic cleanup
        if now - self.last_cleanup > 60:  # Cleanup every minute
            self.last_cleanup = now
            asyncio.create_task(self._cleanup_old_entries())
        
        return True, 0
    
    async def _check_redis_rate_limit(
        self,
        identifier: str,
        limit: int,
        period: int
    ) -> tuple[bool, int]:
        """
        Check rate limit using Redis.
        
        Args:
            identifier: Client identifier
            limit: Request limit
            period: Time period in seconds
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        try:
            client = await get_redis_client()
            key = f"rate_limit:{identifier}"
            now = time.time()
            
            # Use Redis sorted set for sliding window
            pipe = client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, now - period)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiry
            pipe.expire(key, period + 1)
            
            results = await pipe.execute()
            count = results[1]  # Current count before adding
            
            if count >= limit:
                # Get oldest entry for retry-after
                oldest_entries = await client.zrange(key, 0, 0, withscores=True)
                if oldest_entries:
                    oldest_score = oldest_entries[0][1]
                    retry_after = int(oldest_score + period - now) + 1
                else:
                    retry_after = period
                
                # Remove the entry we just added since it's over limit
                await client.zrem(key, str(now))
                
                return False, retry_after
            
            return True, 0
            
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            raise
    
    async def _get_request_count(self, identifier: str, period: int) -> int:
        """
        Get current request count for an identifier.
        
        Args:
            identifier: Client identifier
            period: Time period in seconds
            
        Returns:
            Current request count
        """
        if self.use_redis:
            try:
                client = await get_redis_client()
                key = f"rate_limit:{identifier}"
                now = time.time()
                
                # Remove old entries and get count
                await client.zremrangebyscore(key, 0, now - period)
                count = await client.zcard(key)
                return count
            except Exception:
                pass
        
        # Fallback to in-memory
        now = time.time()
        if identifier in self.clients:
            self.clients[identifier] = [
                ts for ts in self.clients[identifier]
                if ts > now - period
            ]
            return len(self.clients[identifier])
        
        return 0
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address, considering proxy headers.
        
        Args:
            request: Request object
            
        Returns:
            Client IP address
        """
        # Check for proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _get_user_id(self, request: Request) -> Optional[str]:
        """
        Get user ID from request if authenticated.
        
        Args:
            request: Request object
            
        Returns:
            User ID if authenticated, None otherwise
        """
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        # For now, create a hash of the token as identifier
        # In production, you might want to decode the JWT to get the actual user ID
        token = auth_header[7:]  # Remove "Bearer " prefix
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        return token_hash
    
    async def _cleanup_old_entries(self):
        """
        Clean up old entries from in-memory storage.
        """
        now = time.time()
        
        # Clean normal rate limit storage
        for identifier in list(self.clients.keys()):
            self.clients[identifier] = [
                ts for ts in self.clients[identifier]
                if ts > now - self.period
            ]
            if not self.clients[identifier]:
                del self.clients[identifier]
        
        # Clean burst rate limit storage
        for identifier in list(self.burst_clients.keys()):
            self.burst_clients[identifier] = [
                ts for ts in self.burst_clients[identifier]
                if ts > now - self.burst_period
            ]
            if not self.burst_clients[identifier]:
                del self.burst_clients[identifier]
        
        logger.debug(
            "Cleaned up rate limit entries",
            normal_clients=len(self.clients),
            burst_clients=len(self.burst_clients)
        )