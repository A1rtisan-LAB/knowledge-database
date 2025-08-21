"""Security utilities for authentication."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import secrets
import hashlib
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with enhanced security.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    
    # Add security claims
    to_encode.update({
        "exp": expire,
        "iat": now,  # Issued at time
        "nbf": now,  # Not before time
        "type": "access",
        "jti": secrets.token_urlsafe(16)  # JWT ID for tracking
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token with enhanced security.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time
        
    Returns:
        str: Encoded JWT refresh token
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.refresh_token_expire_days)
    
    # Add security claims
    to_encode.update({
        "exp": expire,
        "iat": now,  # Issued at time
        "nbf": now,  # Not before time
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),  # JWT ID for tracking
        "token_family": secrets.token_urlsafe(8)  # Token family for refresh token rotation
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token with enhanced validation.
    
    Args:
        token: JWT token to verify
        token_type: Type of token (access or refresh)
        
    Returns:
        Optional[Dict]: Decoded token data if valid, None otherwise
    """
    try:
        # Decode with verification
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[settings.algorithm],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": False,  # We're not using audience
                "require": ["exp", "iat", "nbf", "type", "jti"]
            }
        )
        
        # Verify token type
        if payload.get("type") != token_type:
            return None
        
        # Additional validation for token age (prevent very old tokens)
        iat = payload.get("iat")
        if iat:
            token_age = datetime.now(timezone.utc) - datetime.fromtimestamp(iat, tz=timezone.utc)
            max_age = timedelta(days=30) if token_type == "refresh" else timedelta(hours=24)
            if token_age > max_age:
                return None
        
        return payload
        
    except ExpiredSignatureError:
        # Token has expired
        return None
    except JWTError:
        # Invalid token
        return None


def create_api_key() -> str:
    """
    Create a new secure API key.
    
    Returns:
        str: Generated API key
    """
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """
    Create a secure hash of a token for storage.
    
    Args:
        token: Token to hash
        
    Returns:
        str: Hashed token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    
    return True, ""