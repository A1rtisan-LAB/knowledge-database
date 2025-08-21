"""Authentication API endpoints."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.models.user import User
from app.models.organization import Organization
from app.auth.security import verify_password, get_password_hash, create_access_token, create_refresh_token, verify_token
from app.auth.dependencies import get_current_user
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, TokenResponse, UserResponse

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """
    User login endpoint.
    
    Args:
        request: Login credentials
        db: Database session
        
    Returns:
        LoginResponse: Access and refresh tokens with user info
    """
    # Find user by email and organization
    query = select(User).where(
        and_(
            User.email == request.email,
            User.is_active == True
        )
    )
    
    if request.organization_slug:
        query = query.join(Organization).where(Organization.slug == request.organization_slug)
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        user=UserResponse.from_orm(user)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    Args:
        request: Refresh token
        db: Database session
        
    Returns:
        TokenResponse: New access and refresh tokens
    """
    payload = verify_token(request.refresh_token, token_type="refresh")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    
    # Verify user still exists and is active
    result = await db.execute(
        select(User).where(
            and_(
                User.id == user_id,
                User.is_active == True
            )
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer"
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    User logout endpoint.
    
    Note: This is a placeholder. In production, you might want to:
    - Invalidate the token in a blacklist
    - Clear server-side session
    - Log the logout event
    """
    # Token invalidation would be implemented here
    # For now, the client should discard the token
    return None


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserResponse: Current user information
    """
    return UserResponse.from_orm(current_user)