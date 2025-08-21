#!/usr/bin/env python
"""Simple test runner with proper environment setup."""

import os
import sys
from pathlib import Path

# Set test environment variables
os.environ.update({
    "SECRET_KEY": "test-secret-key-for-testing-only",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "CORS_ORIGINS": "http://localhost,http://localhost:3000",
    "CORS_ALLOW_CREDENTIALS": "True",
    "CORS_ALLOW_METHODS": "*",
    "CORS_ALLOW_HEADERS": "*",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRATION_DELTA": "3600",
    "OPENSEARCH_HOST": "localhost",
    "OPENSEARCH_PORT": "9200",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "TESTING": "True",
    "ENVIRONMENT": "test",
    "RATE_LIMIT_ENABLED": "False",
})

# Run pytest
import pytest

if __name__ == "__main__":
    # Run with coverage by default
    args = [
        "tests/",
        "-v",
        "--tb=short",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html",
    ]
    
    # Add any additional arguments
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])
    
    sys.exit(pytest.main(args))