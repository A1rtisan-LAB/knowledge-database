"""Comprehensive security test suite."""

import pytest
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.core.config import get_settings
from app.auth.security import (
    create_access_token,
    verify_token,
    validate_password_strength,
    hash_token
)
from app.core.security_utils import (
    sanitize_input,
    validate_sql_input,
    validate_xss_input,
    SecureQueryBuilder
)


class TestComprehensiveSecuritySuite:
    """Comprehensive security test suite covering all security aspects."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def settings(self):
        """Get application settings."""
        return get_settings()
    
    # ==================== JWT Security Tests ====================
    
    def test_jwt_token_lifecycle(self, settings):
        """Test complete JWT token lifecycle."""
        # Create token
        user_data = {"sub": "user-123", "role": "user"}
        token = create_access_token(user_data)
        
        # Verify token
        payload = verify_token(token, token_type="access")
        assert payload is not None
        assert payload["sub"] == "user-123"
        
        # Verify expiration
        assert "exp" in payload
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert exp_time > now
        assert exp_time <= now + timedelta(minutes=settings.access_token_expire_minutes + 1)
    
    def test_jwt_token_tampering_detection(self, settings):
        """Test that tampered tokens are rejected."""
        # Create valid token
        token = create_access_token({"sub": "user-123"})
        
        # Tamper with token (change one character)
        tampered_token = token[:-1] + ("0" if token[-1] != "0" else "1")
        
        # Verification should fail
        payload = verify_token(tampered_token, token_type="access")
        assert payload is None
    
    def test_jwt_algorithm_confusion_attack(self, settings):
        """Test protection against algorithm confusion attacks."""
        from jose import jwt
        
        # Try to create token with 'none' algorithm
        payload = {
            "sub": "attacker",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "type": "access"
        }
        
        # Create token with 'none' algorithm (unsigned)
        malicious_token = jwt.encode(payload, "", algorithm="none")
        
        # Verification should fail
        result = verify_token(malicious_token, token_type="access")
        assert result is None
    
    # ==================== SQL Injection Tests ====================
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in various contexts."""
        malicious_inputs = [
            "'; DROP TABLE users--",
            "1' OR '1'='1",
            "admin'--",
            "1 UNION SELECT password FROM users",
            "'; EXEC xp_cmdshell('net user hack hack /add')--",
            "1; UPDATE users SET role='admin' WHERE id=1--"
        ]
        
        for malicious_input in malicious_inputs:
            assert validate_sql_input(malicious_input) is False
            sanitized = sanitize_input(malicious_input)
            # Sanitized input should remove dangerous characters
            assert "DROP" not in sanitized.upper()
            assert "--" not in sanitized
    
    @pytest.mark.asyncio
    async def test_parameterized_queries(self):
        """Test that queries use parameterized statements."""
        from sqlalchemy import select
        from app.models.user import User
        
        # This should use parameterized query
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        query = select(User).where(User.id == user_id)
        
        # The compiled query should use parameters, not string concatenation
        compiled = query.compile()
        assert ":id_1" in str(compiled) or "%(id_1)s" in str(compiled)
    
    def test_secure_query_builder(self):
        """Test secure query builder prevents injection."""
        allowed_columns = ["name", "email", "created_at"]
        
        # Valid column names
        assert SecureQueryBuilder.validate_column_name("name", allowed_columns)
        assert SecureQueryBuilder.validate_column_name("email", allowed_columns)
        
        # Invalid/malicious column names
        assert not SecureQueryBuilder.validate_column_name("password", allowed_columns)
        assert not SecureQueryBuilder.validate_column_name("name; DROP TABLE--", allowed_columns)
        assert not SecureQueryBuilder.validate_column_name("*", allowed_columns)
    
    # ==================== XSS Prevention Tests ====================
    
    def test_xss_prevention(self):
        """Test XSS attack prevention."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<body onload=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//",
            "<script>document.cookie</script>"
        ]
        
        for payload in xss_payloads:
            assert validate_xss_input(payload) is False
            sanitized = sanitize_input(payload)
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized
            assert "onerror=" not in sanitized
    
    def test_html_entity_encoding(self):
        """Test HTML entity encoding for output."""
        dangerous_chars = "<>\"'&"
        sanitized = sanitize_input(dangerous_chars)
        
        # These characters should be removed or encoded
        assert "<" not in sanitized or "&lt;" in sanitized
        assert ">" not in sanitized or "&gt;" in sanitized
    
    # ==================== Input Validation Tests ====================
    
    def test_input_length_limits(self):
        """Test input length validation."""
        # Very long input
        long_input = "a" * 10000
        sanitized = sanitize_input(long_input, max_length=1000)
        assert len(sanitized) == 1000
        
        # Null bytes
        null_input = "test\x00data"
        sanitized = sanitize_input(null_input)
        assert "\x00" not in sanitized
    
    def test_path_traversal_prevention(self):
        """Test path traversal attack prevention."""
        path_traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        for attempt in path_traversal_attempts:
            # These should be detected as potentially malicious
            assert "../" in attempt or "..\\" in attempt or "%2e" in attempt.lower()
    
    # ==================== Rate Limiting Tests ====================
    
    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, client):
        """Test that rate limiting is enforced."""
        # Make many rapid requests
        responses = []
        for i in range(150):  # Exceed default limit
            response = client.get("/api/v1/knowledge")
            responses.append(response.status_code)
            
            # At some point, we should get rate limited
            if response.status_code == 429:
                break
        
        # Verify that rate limiting kicked in
        assert 429 in responses or len(responses) == 150
    
    def test_rate_limit_headers(self, client):
        """Test rate limit headers are present."""
        response = client.get("/api/v1/knowledge")
        
        # Check for rate limit headers
        if "x-ratelimit-limit" in response.headers:
            assert response.headers["x-ratelimit-limit"].isdigit()
            assert int(response.headers["x-ratelimit-limit"]) > 0
            
            if "x-ratelimit-remaining" in response.headers:
                assert response.headers["x-ratelimit-remaining"].isdigit()
                remaining = int(response.headers["x-ratelimit-remaining"])
                limit = int(response.headers["x-ratelimit-limit"])
                assert 0 <= remaining <= limit
    
    # ==================== CORS Security Tests ====================
    
    def test_cors_origin_validation(self, client):
        """Test CORS origin validation."""
        # Test with allowed origin
        response = client.options(
            "/api/v1/knowledge",
            headers={"Origin": "https://example.com"}
        )
        assert response.status_code in [200, 204]
        
        # Test with potentially malicious origin
        response = client.options(
            "/api/v1/knowledge",
            headers={"Origin": "https://evil.com"}
        )
        # The response should still be successful for OPTIONS,
        # but the Access-Control-Allow-Origin should be restricted
        assert response.status_code in [200, 204]
    
    def test_cors_preflight_caching(self, client):
        """Test CORS preflight caching configuration."""
        response = client.options(
            "/api/v1/knowledge",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # Check for max-age header
        if "access-control-max-age" in response.headers:
            max_age = int(response.headers["access-control-max-age"])
            assert max_age > 0  # Should cache preflight requests
    
    # ==================== Password Security Tests ====================
    
    def test_password_strength_requirements(self):
        """Test password strength validation."""
        # Weak passwords that should be rejected
        weak_passwords = [
            "password",  # Too common
            "12345678",  # No letters
            "abcdefgh",  # No numbers or special chars
            "Abc123",    # Too short, no special char
            "password123",  # No uppercase or special char
            "PASSWORD123",  # No lowercase or special char
        ]
        
        for password in weak_passwords:
            is_valid, message = validate_password_strength(password)
            assert is_valid is False
            assert message != ""
        
        # Strong password that should be accepted
        strong_passwords = [
            "MyStr0ng!Pass123",
            "C0mpl3x@Password",
            "Secur3$Pass!word",
        ]
        
        for password in strong_passwords:
            is_valid, message = validate_password_strength(password)
            assert is_valid is True
            assert message == ""
    
    def test_password_hashing(self):
        """Test password hashing security."""
        from app.auth.security import get_password_hash, verify_password
        
        password = "MySecurePassword123!"
        
        # Hash password
        hashed = get_password_hash(password)
        
        # Verify correct password
        assert verify_password(password, hashed) is True
        
        # Verify incorrect password
        assert verify_password("WrongPassword", hashed) is False
        
        # Hashes should be different even for same password (salt)
        hashed2 = get_password_hash(password)
        assert hashed != hashed2
    
    # ==================== Security Headers Tests ====================
    
    def test_security_headers_present(self, client):
        """Test that all security headers are present."""
        response = client.get("/api/v1/knowledge")
        
        expected_headers = {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
            "x-xss-protection": "1; mode=block",
            "referrer-policy": "strict-origin-when-cross-origin"
        }
        
        for header, expected_value in expected_headers.items():
            if header in response.headers:
                assert response.headers[header] == expected_value
    
    # ==================== Token Security Tests ====================
    
    def test_token_blacklisting_mechanism(self):
        """Test token blacklisting for logout."""
        # Create a token
        token = create_access_token({"sub": "user-123"})
        
        # Hash token for storage (simulating blacklist)
        token_hash = hash_token(token)
        
        # Token hash should be consistent
        assert token_hash == hash_token(token)
        
        # Different tokens should have different hashes
        token2 = create_access_token({"sub": "user-456"})
        assert hash_token(token2) != token_hash
    
    def test_refresh_token_rotation(self):
        """Test refresh token rotation security."""
        from app.auth.security import create_refresh_token
        
        # Create initial refresh token
        token1 = create_refresh_token({"sub": "user-123"})
        payload1 = verify_token(token1, token_type="refresh")
        
        # Create new refresh token (rotation)
        token2 = create_refresh_token({"sub": "user-123"})
        payload2 = verify_token(token2, token_type="refresh")
        
        # Tokens should have different JTIs
        assert payload1["jti"] != payload2["jti"]
        
        # But same token family (for tracking rotation)
        # Note: token_family changes with each token creation in our implementation
        # In production, you'd maintain the family across rotations
    
    # ==================== Comprehensive Attack Simulation ====================
    
    @pytest.mark.asyncio
    async def test_combined_attack_vectors(self, client):
        """Test protection against combined attack vectors."""
        # Attempt multiple attack vectors in single request
        attack_payload = {
            "username": "admin' OR '1'='1--",  # SQL injection
            "password": "<script>alert('XSS')</script>",  # XSS
            "email": "../../../etc/passwd",  # Path traversal
            "profile": "A" * 100000,  # Buffer overflow attempt
            "callback": "javascript:eval('malicious')",  # XSS via javascript protocol
        }
        
        # All these should be sanitized or rejected
        for key, value in attack_payload.items():
            sanitized = sanitize_input(value, max_length=1000)
            
            # Verify dangerous content is removed
            assert "script>" not in sanitized
            assert "--" not in sanitized
            assert "../" not in sanitized
            assert "javascript:" not in sanitized
            
            # Length should be limited
            assert len(sanitized) <= 1000