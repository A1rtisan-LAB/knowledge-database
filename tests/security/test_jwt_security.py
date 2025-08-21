"""Tests for JWT token security enhancements."""

import pytest
import time
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    validate_password_strength
)
from app.core.config import get_settings

settings = get_settings()


class TestJWTSecurity:
    """Test JWT token security features."""
    
    def test_access_token_creation(self):
        """Test access token creation with security claims."""
        data = {"sub": "test-user-id"}
        token = create_access_token(data)
        
        # Decode token
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        
        # Check required claims
        assert "exp" in payload
        assert "iat" in payload
        assert "nbf" in payload
        assert "type" in payload
        assert "jti" in payload
        assert payload["type"] == "access"
        assert payload["sub"] == "test-user-id"
        
        # Check timestamps
        now = datetime.now(timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        nbf = datetime.fromtimestamp(payload["nbf"], tz=timezone.utc)
        
        assert iat <= now
        assert nbf <= now
        assert exp > now
        assert (exp - iat).total_seconds() <= settings.access_token_expire_minutes * 60
    
    def test_refresh_token_creation(self):
        """Test refresh token creation with security claims."""
        data = {"sub": "test-user-id"}
        token = create_refresh_token(data)
        
        # Decode token
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        
        # Check required claims
        assert "exp" in payload
        assert "iat" in payload
        assert "nbf" in payload
        assert "type" in payload
        assert "jti" in payload
        assert "token_family" in payload
        assert payload["type"] == "refresh"
        assert payload["sub"] == "test-user-id"
    
    def test_token_verification_success(self):
        """Test successful token verification."""
        data = {"sub": "test-user-id"}
        token = create_access_token(data)
        
        payload = verify_token(token, token_type="access")
        assert payload is not None
        assert payload["sub"] == "test-user-id"
    
    def test_token_verification_wrong_type(self):
        """Test token verification with wrong type."""
        data = {"sub": "test-user-id"}
        access_token = create_access_token(data)
        
        # Try to verify access token as refresh token
        payload = verify_token(access_token, token_type="refresh")
        assert payload is None
    
    def test_expired_token_rejection(self):
        """Test that expired tokens are rejected."""
        data = {"sub": "test-user-id"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        payload = verify_token(token, token_type="access")
        assert payload is None
    
    def test_token_without_required_claims(self):
        """Test that tokens without required claims are rejected."""
        # Create token manually without required claims
        payload = {
            "sub": "test-user-id",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        }
        # Missing iat, nbf, type, jti
        
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        
        result = verify_token(token, token_type="access")
        assert result is None
    
    def test_token_with_future_nbf(self):
        """Test that tokens with future 'not before' time are rejected."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "test-user-id",
            "exp": now + timedelta(minutes=30),
            "iat": now,
            "nbf": now + timedelta(minutes=5),  # Not valid for 5 minutes
            "type": "access",
            "jti": "test-jti"
        }
        
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        
        result = verify_token(token, token_type="access")
        assert result is None
    
    def test_very_old_token_rejection(self):
        """Test that very old tokens are rejected."""
        # Create token issued 25 hours ago (exceeds 24-hour max age for access tokens)
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        payload = {
            "sub": "test-user-id",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "iat": old_time.timestamp(),
            "nbf": old_time.timestamp(),
            "type": "access",
            "jti": "test-jti"
        }
        
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        
        result = verify_token(token, token_type="access")
        assert result is None
    
    def test_jti_uniqueness(self):
        """Test that JTI (JWT ID) is unique for each token."""
        tokens = []
        jtis = set()
        
        for _ in range(10):
            token = create_access_token({"sub": "test-user-id"})
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            jti = payload["jti"]
            assert jti not in jtis  # Ensure uniqueness
            jtis.add(jti)
    
    def test_token_family_in_refresh_token(self):
        """Test that refresh tokens include token family for rotation."""
        token = create_refresh_token({"sub": "test-user-id"})
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        
        assert "token_family" in payload
        assert len(payload["token_family"]) > 0


class TestPasswordValidation:
    """Test password strength validation."""
    
    def test_strong_password(self):
        """Test validation of strong password."""
        is_valid, message = validate_password_strength("StrongP@ssw0rd123")
        assert is_valid is True
        assert message == ""
    
    def test_password_too_short(self):
        """Test rejection of short password."""
        is_valid, message = validate_password_strength("Short1!")
        assert is_valid is False
        assert "at least 8 characters" in message
    
    def test_password_no_uppercase(self):
        """Test rejection of password without uppercase."""
        is_valid, message = validate_password_strength("weakpassword123!")
        assert is_valid is False
        assert "uppercase letter" in message
    
    def test_password_no_lowercase(self):
        """Test rejection of password without lowercase."""
        is_valid, message = validate_password_strength("STRONGPASSWORD123!")
        assert is_valid is False
        assert "lowercase letter" in message
    
    def test_password_no_digit(self):
        """Test rejection of password without digit."""
        is_valid, message = validate_password_strength("StrongPassword!")
        assert is_valid is False
        assert "digit" in message
    
    def test_password_no_special(self):
        """Test rejection of password without special character."""
        is_valid, message = validate_password_strength("StrongPassword123")
        assert is_valid is False
        assert "special character" in message