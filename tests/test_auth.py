"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient
from app.models.user import User


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    """Test successful login."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["user"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_user: User):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "password123"
        }
    )
    
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user: User):
    """Test token refresh."""
    # First login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    refresh_token = login_response.json()["refresh_token"]
    
    # Refresh token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    """Test refresh with invalid token."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"}
    )
    
    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, auth_headers: dict):
    """Test getting current user info."""
    response = await client.get(
        "/api/v1/auth/me",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert data["role"] == "editor"


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, auth_headers: dict):
    """Test logout."""
    response = await client.post(
        "/api/v1/auth/logout",
        headers=auth_headers
    )
    
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_protected_endpoint_without_auth(client: AsyncClient):
    """Test accessing protected endpoint without authentication."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403  # HTTPBearer returns 403 when no credentials