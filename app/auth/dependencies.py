"""Authentication dependencies for FastAPI routes."""

from typing import Optional
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.models.user import User, UserRole
from app.auth.security import verify_token
from app.services.redis import cache_get, cache_set

logger = structlog.get_logger()

security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token with enhanced security.
    
    Args:
        request: FastAPI request object
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    
    # Check if token is blacklisted
    blacklist_key = f"blacklist:token:{token[:20]}"
    is_blacklisted = await cache_get(blacklist_key)
    if is_blacklisted:
        logger.warning(
            "Attempt to use blacklisted token",
            client_ip=request.client.host if request.client else "unknown"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    payload = verify_token(token, token_type="access")
    
    if payload is None:
        logger.warning(
            "Invalid token attempt",
            client_ip=request.client.host if request.client else "unknown"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    jti = payload.get("jti")
    
    if user_id is None or jti is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check for token reuse (cache JTI for the token lifetime)
    jti_key = f"jti:{jti}"
    jti_exists = await cache_get(jti_key)
    if jti_exists:
        logger.warning(
            "Token reuse detected",
            user_id=user_id,
            jti=jti,
            client_ip=request.client.host if request.client else "unknown"
        )
        # This could indicate token theft
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has already been used",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Mark JTI as used (with expiration matching token lifetime)
    await cache_set(jti_key, "1", ttl=1800)  # 30 minutes for access token
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user account is locked
    if hasattr(user, 'locked_until') and user.locked_until:
        if user.locked_until > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is locked until {user.locked_until.isoformat()}"
            )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise None.
    
    Args:
        credentials: Optional HTTP authorization credentials
        db: Database session
        
    Returns:
        Optional[User]: Current user if authenticated, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_role(*roles: UserRole):
    """
    Dependency factory to require specific user roles.
    
    Args:
        *roles: Required user roles
        
    Returns:
        Dependency function that checks user role
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(roles)}"
            )
        return current_user
    return role_checker


# Pre-defined role dependencies
require_admin = require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN)
require_editor = require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.EDITOR)
require_reviewer = require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.EDITOR, UserRole.REVIEWER)