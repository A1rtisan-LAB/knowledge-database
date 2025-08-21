"""Application configuration using Pydantic settings."""

from typing import List, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = Field(default="Knowledge Database API")
    app_version: str = Field(default="1.0.0")
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)
    api_prefix: str = Field(default="/api/v1")
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=4)
    reload: bool = Field(default=False)
    
    # Security
    secret_key: str = Field(...)  # Required, no default for security
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    
    # CORS
    cors_origins: List[str] = Field(default=["*"])
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: List[str] = Field(default=["*"])
    cors_allow_headers: List[str] = Field(default=["*"])
    
    # Database
    database_url: str = Field(...)
    database_pool_size: int = Field(default=20)
    database_max_overflow: int = Field(default=40)
    database_pool_timeout: int = Field(default=30)
    database_echo: bool = Field(default=False)
    
    # OpenSearch
    opensearch_host: str = Field(default="localhost")
    opensearch_port: int = Field(default=9200)
    opensearch_username: Optional[str] = Field(default=None)
    opensearch_password: Optional[str] = Field(default=None)
    opensearch_use_ssl: bool = Field(default=False)
    opensearch_verify_certs: bool = Field(default=False)
    opensearch_index_prefix: str = Field(default="knowledge")
    
    # Redis
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = Field(default=None)
    redis_cache_ttl: int = Field(default=3600)
    
    # RabbitMQ
    rabbitmq_host: str = Field(default="localhost")
    rabbitmq_port: int = Field(default=5672)
    rabbitmq_username: Optional[str] = Field(default=None)
    rabbitmq_password: Optional[str] = Field(default=None)
    rabbitmq_vhost: str = Field(default="/")
    
    # Translation
    translation_service: str = Field(default="google")
    translation_api_key: Optional[str] = Field(default=None)
    
    # Embedding
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    embedding_dimension: int = Field(default=384)
    embedding_batch_size: int = Field(default=32)
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    log_file: Optional[str] = Field(default="logs/app.log")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests: int = Field(default=100)
    rate_limit_period: int = Field(default=60)
    
    # File Upload
    max_upload_size: int = Field(default=10485760)  # 10MB
    allowed_extensions: List[str] = Field(default=["csv", "json", "md", "txt"])
    
    # Pagination
    default_page_size: int = Field(default=20)
    max_page_size: int = Field(default=100)
    
    # Admin
    admin_email: Optional[str] = Field(default=None)
    admin_password: Optional[str] = Field(default=None)
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v):
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [method.strip() for method in v.split(",")]
        return v
    
    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v):
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [header.strip() for header in v.split(",")]
        return v
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "")
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def rabbitmq_url(self) -> str:
        """Get RabbitMQ connection URL."""
        return f"amqp://{self.rabbitmq_username}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}{self.rabbitmq_vhost}"
    
    @property
    def opensearch_url(self) -> str:
        """Get OpenSearch connection URL."""
        protocol = "https" if self.opensearch_use_ssl else "http"
        if self.opensearch_username and self.opensearch_password:
            return f"{protocol}://{self.opensearch_username}:{self.opensearch_password}@{self.opensearch_host}:{self.opensearch_port}"
        return f"{protocol}://{self.opensearch_host}:{self.opensearch_port}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()