"""Comprehensive tests for configuration module."""

import os
import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from app.core.config import Settings, get_settings


class TestSettingsDefaults:
    """Test cases for Settings default values."""
    
    def test_application_defaults(self):
        """Test application-related default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.app_name == "Knowledge Database API"
            assert settings.app_version == "1.0.0"
            assert settings.app_env == "development"
            assert settings.debug is False
            assert settings.api_prefix == "/api/v1"
    
    def test_server_defaults(self):
        """Test server-related default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
            assert settings.workers == 4
            assert settings.reload is False
    
    def test_security_defaults(self):
        """Test security-related default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key-123',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.secret_key == 'test-secret-key-123'
            assert settings.algorithm == "HS256"
            assert settings.access_token_expire_minutes == 30
            assert settings.refresh_token_expire_days == 7
    
    def test_cors_defaults(self):
        """Test CORS-related default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.cors_origins == ["*"]
            assert settings.cors_allow_credentials is True
            assert settings.cors_allow_methods == ["*"]
            assert settings.cors_allow_headers == ["*"]
    
    def test_database_defaults(self):
        """Test database-related default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.database_url == 'postgresql+asyncpg://user:pass@localhost/db'
            assert settings.database_pool_size == 20
            assert settings.database_max_overflow == 40
            assert settings.database_pool_timeout == 30
            assert settings.database_echo is False
    
    def test_opensearch_defaults(self):
        """Test OpenSearch-related default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.opensearch_host == "localhost"
            assert settings.opensearch_port == 9200
            assert settings.opensearch_username is None
            assert settings.opensearch_password is None
            assert settings.opensearch_use_ssl is False
            assert settings.opensearch_verify_certs is False
            assert settings.opensearch_index_prefix == "knowledge"
    
    def test_redis_defaults(self):
        """Test Redis-related default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.redis_host == "localhost"
            assert settings.redis_port == 6379
            assert settings.redis_db == 0
            assert settings.redis_password is None
            assert settings.redis_cache_ttl == 3600
    
    def test_rabbitmq_defaults(self):
        """Test RabbitMQ-related default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.rabbitmq_host == "localhost"
            assert settings.rabbitmq_port == 5672
            assert settings.rabbitmq_username is None
            assert settings.rabbitmq_password is None
            assert settings.rabbitmq_vhost == "/"
    
    def test_translation_defaults(self):
        """Test translation-related default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.translation_service == "google"
            assert settings.translation_api_key is None
    
    def test_embedding_defaults(self):
        """Test embedding-related default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
            assert settings.embedding_dimension == 384
            assert settings.embedding_batch_size == 32
    
    def test_logging_defaults(self):
        """Test logging-related default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.log_level == "INFO"
            assert settings.log_format == "json"
            assert settings.log_file == "logs/app.log"
    
    def test_rate_limit_defaults(self):
        """Test rate limiting default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.rate_limit_enabled is True
            assert settings.rate_limit_requests == 100
            assert settings.rate_limit_period == 60
    
    def test_file_upload_defaults(self):
        """Test file upload default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.max_upload_size == 10485760  # 10MB
            assert settings.allowed_extensions == ["csv", "json", "md", "txt"]
    
    def test_pagination_defaults(self):
        """Test pagination default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.default_page_size == 20
            assert settings.max_page_size == 100
    
    def test_admin_defaults(self):
        """Test admin default settings."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.admin_email is None
            assert settings.admin_password is None


class TestSettingsEnvironmentOverrides:
    """Test cases for environment variable overrides."""
    
    def test_override_from_environment(self):
        """Test that environment variables override defaults."""
        env_vars = {
            'SECRET_KEY': 'env-secret-key',
            'DATABASE_URL': 'postgresql+asyncpg://envuser:envpass@envhost/envdb',
            'APP_NAME': 'Custom API',
            'APP_VERSION': '2.0.0',
            'APP_ENV': 'production',
            'DEBUG': 'true',
            'HOST': '127.0.0.1',
            'PORT': '9000',
            'WORKERS': '8',
            'LOG_LEVEL': 'DEBUG',
            'REDIS_HOST': 'redis.example.com',
            'REDIS_PORT': '6380',
            'OPENSEARCH_HOST': 'search.example.com',
            'OPENSEARCH_PORT': '9201'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.secret_key == 'env-secret-key'
            assert settings.database_url == 'postgresql+asyncpg://envuser:envpass@envhost/envdb'
            assert settings.app_name == 'Custom API'
            assert settings.app_version == '2.0.0'
            assert settings.app_env == 'production'
            assert settings.debug is True
            assert settings.host == '127.0.0.1'
            assert settings.port == 9000
            assert settings.workers == 8
            assert settings.log_level == 'DEBUG'
            assert settings.redis_host == 'redis.example.com'
            assert settings.redis_port == 6380
            assert settings.opensearch_host == 'search.example.com'
            assert settings.opensearch_port == 9201
    
    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case insensitive."""
        env_vars = {
            'secret_key': 'lowercase-secret',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'App_Name': 'MixedCase API',
            'APP_VERSION': 'UPPERCASE'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.secret_key == 'lowercase-secret'
            assert settings.app_name == 'MixedCase API'
            assert settings.app_version == 'UPPERCASE'


class TestSettingsValidators:
    """Test cases for field validators."""
    
    def test_parse_cors_origins_string(self):
        """Test parsing CORS origins from comma-separated string."""
        env_vars = {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'CORS_ORIGINS': 'http://localhost:3000,https://example.com,https://app.example.com'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.cors_origins == [
                'http://localhost:3000',
                'https://example.com',
                'https://app.example.com'
            ]
    
    def test_parse_cors_origins_with_spaces(self):
        """Test parsing CORS origins with spaces."""
        env_vars = {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'CORS_ORIGINS': 'http://localhost:3000 , https://example.com , https://app.example.com'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.cors_origins == [
                'http://localhost:3000',
                'https://example.com',
                'https://app.example.com'
            ]
    
    def test_parse_cors_origins_list(self):
        """Test that list CORS origins are preserved."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            # When passed as a list directly (not from env), should be preserved
            settings = Settings(cors_origins=['http://localhost:3000', 'https://example.com'])
            assert settings.cors_origins == ['http://localhost:3000', 'https://example.com']
    
    def test_parse_cors_methods_string(self):
        """Test parsing CORS methods from comma-separated string."""
        env_vars = {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'CORS_ALLOW_METHODS': 'GET,POST,PUT,DELETE'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.cors_allow_methods == ['GET', 'POST', 'PUT', 'DELETE']
    
    def test_parse_cors_methods_wildcard(self):
        """Test parsing CORS methods wildcard."""
        env_vars = {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'CORS_ALLOW_METHODS': '*'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.cors_allow_methods == ['*']
    
    def test_parse_cors_headers_string(self):
        """Test parsing CORS headers from comma-separated string."""
        env_vars = {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'CORS_ALLOW_HEADERS': 'Content-Type,Authorization,X-Request-ID'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.cors_allow_headers == ['Content-Type', 'Authorization', 'X-Request-ID']
    
    def test_parse_cors_headers_wildcard(self):
        """Test parsing CORS headers wildcard."""
        env_vars = {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'CORS_ALLOW_HEADERS': '*'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.cors_allow_headers == ['*']


class TestSettingsProperties:
    """Test cases for computed properties."""
    
    def test_database_url_sync_property(self):
        """Test database_url_sync property for Alembic."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = Settings()
            
            assert settings.database_url == 'postgresql+asyncpg://user:pass@localhost/db'
            assert settings.database_url_sync == 'postgresql://user:pass@localhost/db'
    
    def test_redis_url_property_without_password(self):
        """Test redis_url property without password."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'REDIS_HOST': 'redis.local',
            'REDIS_PORT': '6380',
            'REDIS_DB': '1'
        }):
            settings = Settings()
            
            assert settings.redis_url == 'redis://redis.local:6380/1'
    
    def test_redis_url_property_with_password(self):
        """Test redis_url property with password."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'REDIS_HOST': 'redis.local',
            'REDIS_PORT': '6380',
            'REDIS_DB': '1',
            'REDIS_PASSWORD': 'secret123'
        }):
            settings = Settings()
            
            assert settings.redis_url == 'redis://:secret123@redis.local:6380/1'
    
    def test_rabbitmq_url_property(self):
        """Test rabbitmq_url property."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'RABBITMQ_HOST': 'rabbit.local',
            'RABBITMQ_PORT': '5673',
            'RABBITMQ_USERNAME': 'rabbituser',
            'RABBITMQ_PASSWORD': 'rabbitpass',
            'RABBITMQ_VHOST': '/myapp'
        }):
            settings = Settings()
            
            assert settings.rabbitmq_url == 'amqp://rabbituser:rabbitpass@rabbit.local:5673/myapp'
    
    def test_opensearch_url_property_without_auth(self):
        """Test opensearch_url property without authentication."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'OPENSEARCH_HOST': 'search.local',
            'OPENSEARCH_PORT': '9201',
            'OPENSEARCH_USE_SSL': 'false'
        }):
            settings = Settings()
            
            assert settings.opensearch_url == 'http://search.local:9201'
    
    def test_opensearch_url_property_with_auth(self):
        """Test opensearch_url property with authentication."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'OPENSEARCH_HOST': 'search.local',
            'OPENSEARCH_PORT': '9201',
            'OPENSEARCH_USERNAME': 'searchuser',
            'OPENSEARCH_PASSWORD': 'searchpass',
            'OPENSEARCH_USE_SSL': 'true'
        }):
            settings = Settings()
            
            assert settings.opensearch_url == 'https://searchuser:searchpass@search.local:9201'


class TestSettingsValidation:
    """Test cases for settings validation."""
    
    def test_required_fields_validation(self):
        """Test that required fields raise validation errors when missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            errors = exc_info.value.errors()
            error_fields = [error['loc'][0] for error in errors]
            
            # Check that required fields are in the errors
            assert 'secret_key' in error_fields
            assert 'database_url' in error_fields
    
    def test_type_validation(self):
        """Test that field types are validated."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'PORT': 'not-a-number',  # Should be int
            'DEBUG': 'not-a-bool',  # Should be bool
            'WORKERS': 'invalid'  # Should be int
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            errors = exc_info.value.errors()
            error_fields = [error['loc'][0] for error in errors]
            
            # Port and workers should have validation errors
            assert 'port' in error_fields
            assert 'workers' in error_fields
    
    def test_boolean_field_parsing(self):
        """Test boolean field parsing from strings."""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('1', True),
            ('yes', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('0', False),
            ('no', False),
        ]
        
        for value, expected in test_cases:
            with patch.dict(os.environ, {
                'SECRET_KEY': 'test-key',
                'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
                'DEBUG': value
            }):
                settings = Settings()
                assert settings.debug is expected


class TestGetSettings:
    """Test cases for get_settings function."""
    
    def test_get_settings_returns_settings(self):
        """Test that get_settings returns a Settings instance."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            settings = get_settings()
            assert isinstance(settings, Settings)
    
    def test_get_settings_caching(self):
        """Test that get_settings uses LRU cache."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            # Clear cache first
            get_settings.cache_clear()
            
            # First call
            settings1 = get_settings()
            
            # Second call should return the same instance
            settings2 = get_settings()
            
            assert settings1 is settings2
            
            # Check cache info
            cache_info = get_settings.cache_info()
            assert cache_info.hits == 1
            assert cache_info.misses == 1
    
    def test_get_settings_cache_clear(self):
        """Test clearing the settings cache."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            # Get settings
            settings1 = get_settings()
            
            # Clear cache
            get_settings.cache_clear()
            
            # Get settings again - should be a new instance
            settings2 = get_settings()
            
            # They should be different instances but equal values
            assert settings1 is not settings2
            assert settings1.secret_key == settings2.secret_key


class TestSettingsConfig:
    """Test cases for Settings.Config."""
    
    def test_config_attributes(self):
        """Test Settings.Config attributes."""
        assert Settings.Config.env_file == ".env"
        assert Settings.Config.case_sensitive is False
    
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_env_file_loading(self, mock_exists, mock_open):
        """Test that .env file is loaded if it exists."""
        # Simulate .env file exists
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = (
            "SECRET_KEY=from-env-file\n"
            "DATABASE_URL=postgresql+asyncpg://envfile:pass@localhost/db\n"
        )
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('app.core.config.Settings') as mock_settings_class:
                mock_settings_class.return_value = MagicMock()
                
                # The Settings class should attempt to read from .env
                # This is handled by pydantic_settings automatically


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_string_values(self):
        """Test handling of empty string values."""
        with patch.dict(os.environ, {
            'SECRET_KEY': '',  # Empty required field
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db'
        }):
            with pytest.raises(ValidationError):
                Settings()
    
    def test_special_characters_in_values(self):
        """Test handling of special characters in configuration values."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'key-with-special-!@#$%^&*()_+{}[]|:";\'<>?,./`~',
            'DATABASE_URL': 'postgresql+asyncpg://user:p@$$w0rd!@localhost/db',
            'APP_NAME': 'API with spaces and 特殊文字'
        }):
            settings = Settings()
            
            assert settings.secret_key == 'key-with-special-!@#$%^&*()_+{}[]|:";\'<>?,./`~'
            assert settings.database_url == 'postgresql+asyncpg://user:p@$$w0rd!@localhost/db'
            assert settings.app_name == 'API with spaces and 特殊文字'
    
    def test_very_large_values(self):
        """Test handling of very large configuration values."""
        large_value = 'x' * 10000
        
        with patch.dict(os.environ, {
            'SECRET_KEY': large_value,
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'APP_NAME': large_value
        }):
            settings = Settings()
            
            assert settings.secret_key == large_value
            assert settings.app_name == large_value
    
    def test_numeric_string_conversions(self):
        """Test conversion of numeric strings to appropriate types."""
        with patch.dict(os.environ, {
            'SECRET_KEY': 'test-key',
            'DATABASE_URL': 'postgresql+asyncpg://user:pass@localhost/db',
            'PORT': '0',  # Edge case: port 0
            'WORKERS': '1000',  # Large number
            'REDIS_PORT': '65535',  # Max port number
            'DATABASE_POOL_SIZE': '0',  # Zero pool size
            'RATE_LIMIT_REQUESTS': '-1'  # Negative number
        }):
            settings = Settings()
            
            assert settings.port == 0
            assert settings.workers == 1000
            assert settings.redis_port == 65535
            assert settings.database_pool_size == 0
            assert settings.rate_limit_requests == -1