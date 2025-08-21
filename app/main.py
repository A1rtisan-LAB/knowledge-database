"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import structlog

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.api import router as api_router
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.input_validation import InputValidationMiddleware
from app.services.opensearch import init_opensearch
from app.services.redis import init_redis, close_redis

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Knowledge Database API", version=settings.app_version, env=settings.app_env)
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize OpenSearch
    await init_opensearch()
    logger.info("OpenSearch initialized")
    
    # Initialize Redis
    await init_redis()
    logger.info("Redis initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Knowledge Database API")
    
    # Close database connections
    await close_db()
    
    # Close Redis connections
    await close_redis()
    
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Comprehensive knowledge management system with AI-powered search and bilingual support",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# Add CORS middleware with strict settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if settings.app_env == "production" else ["*"],
    allow_credentials=True if settings.app_env == "production" else settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Add trusted host middleware
if settings.app_env == "production":
    # In production, only allow specific hosts
    allowed_hosts = []
    for origin in settings.cors_origins:
        if origin != "*":
            # Extract host from origin URL
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            if parsed.hostname:
                allowed_hosts.append(parsed.hostname)
    
    if allowed_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )
else:
    # In development, allow all hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
)

# Add security middleware
app.add_middleware(LoggingMiddleware)

# Add input validation middleware
app.add_middleware(
    InputValidationMiddleware,
    strict_mode=settings.app_env == "production"
)

# Add enhanced rate limiting
if settings.rate_limit_enabled:
    app.add_middleware(
        RateLimitMiddleware,
        requests=settings.rate_limit_requests,
        period=settings.rate_limit_period,
        burst_requests=10,  # Max 10 requests per second
        burst_period=1,
        use_redis=True,
        by_user=True,
        by_ip=True,
        by_endpoint=False  # Can be enabled for specific endpoint limiting
    )

# Include API routes
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "docs": "/docs" if settings.debug else None,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": f"The path {request.url.path} was not found",
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    logger.error("Internal server error", exc_info=exc, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An internal server error occurred",
        },
    )