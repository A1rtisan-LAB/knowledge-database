"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.knowledge_item import KnowledgeItem, ContentStatus
from app.models.category import Category


@pytest.mark.integration
class TestAuthEndpoints:
    """Test authentication API endpoints."""
    
    async def test_register_user(self, client: AsyncClient):
        """Test user registration endpoint."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePass123!",
                "full_name": "New User",
                "organization_name": "New Org"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "id" in data
        assert "access_token" not in data  # Token only on login
        
    async def test_login_success(self, client: AsyncClient, test_user: User):
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
        assert data["token_type"] == "bearer"
        
    async def test_login_invalid_credentials(self, client: AsyncClient, test_user: User):
        """Test login with invalid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
        
    async def test_refresh_token(self, client: AsyncClient, test_user: User):
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
        
    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict):
        """Test getting current user info."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"
        
    async def test_update_user_profile(self, client: AsyncClient, auth_headers: dict):
        """Test updating user profile."""
        response = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={
                "full_name": "Updated Name",
                "preferred_language": "ko"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["preferred_language"] == "ko"
        
    async def test_change_password(self, client: AsyncClient, auth_headers: dict):
        """Test changing password."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "NewSecurePass456!"
            }
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"


@pytest.mark.integration
class TestKnowledgeEndpoints:
    """Test knowledge item API endpoints."""
    
    async def test_create_knowledge_item(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test creating a knowledge item."""
        # First create a category
        category_response = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "Tech",
                "slug": "tech",
                "description": "Technology"
            }
        )
        category_id = category_response.json()["id"]
        
        # Create knowledge item
        response = await client.post(
            "/api/v1/knowledge",
            headers=auth_headers,
            json={
                "title": "API Testing Guide",
                "content": "How to test APIs effectively",
                "category_id": category_id,
                "tags": ["testing", "api", "guide"],
                "status": "published"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "API Testing Guide"
        assert data["category_id"] == category_id
        assert "testing" in data["tags"]
        
    async def test_get_knowledge_item(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test getting a knowledge item."""
        # Create item directly in DB
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Test Item",
            content="Test content",
            status=ContentStatus.PUBLISHED
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        # Get via API
        response = await client.get(
            f"/api/v1/knowledge/{item.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Item"
        assert data["content"] == "Test content"
        
    async def test_update_knowledge_item(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test updating a knowledge item."""
        # Create item
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Original Title",
            content="Original content"
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        # Update via API
        response = await client.put(
            f"/api/v1/knowledge/{item.id}",
            headers=auth_headers,
            json={
                "title": "Updated Title",
                "content": "Updated content",
                "tags": ["updated"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["content"] == "Updated content"
        
    async def test_delete_knowledge_item(self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession, test_organization: Organization, admin_user: User):
        """Test deleting a knowledge item (admin only)."""
        # Create item
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=admin_user.id,
            title="To Delete",
            content="Will be deleted"
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        # Delete via API
        response = await client.delete(
            f"/api/v1/knowledge/{item.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 204
        
        # Verify deletion
        get_response = await client.get(
            f"/api/v1/knowledge/{item.id}",
            headers=admin_headers
        )
        assert get_response.status_code == 404
        
    async def test_list_knowledge_items(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test listing knowledge items with pagination."""
        # Create multiple items
        for i in range(15):
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                title=f"Item {i}",
                content=f"Content {i}",
                status=ContentStatus.PUBLISHED
            )
            db_session.add(item)
        await db_session.commit()
        
        # Get first page
        response = await client.get(
            "/api/v1/knowledge?page=1&page_size=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 15
        assert data["page"] == 1
        assert data["pages"] == 2
        
    async def test_search_knowledge(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test searching knowledge items."""
        # Create items with different content
        items_data = [
            ("Python Tutorial", "Learn Python programming"),
            ("JavaScript Guide", "Master JavaScript"),
            ("Python Advanced", "Advanced Python concepts")
        ]
        
        for title, content in items_data:
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                title=title,
                content=content,
                status=ContentStatus.PUBLISHED
            )
            db_session.add(item)
        await db_session.commit()
        
        # Search for Python
        response = await client.get(
            "/api/v1/search?query=Python",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert all("Python" in r["title"] for r in data["results"])


@pytest.mark.integration
class TestCategoryEndpoints:
    """Test category API endpoints."""
    
    async def test_create_category(self, client: AsyncClient, auth_headers: dict):
        """Test creating a category."""
        response = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "Development",
                "slug": "development",
                "name_ko": "개발",
                "description": "Development resources",
                "description_ko": "개발 자료"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Development"
        assert data["name_ko"] == "개발"
        
    async def test_get_category(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization):
        """Test getting a category."""
        category = Category(
            organization_id=test_organization.id,
            name="Test Category",
            slug="test-category"
        )
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        
        response = await client.get(
            f"/api/v1/categories/{category.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Category"
        
    async def test_list_categories(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization):
        """Test listing categories."""
        # Create categories
        for i in range(5):
            category = Category(
                organization_id=test_organization.id,
                name=f"Category {i}",
                slug=f"category-{i}"
            )
            db_session.add(category)
        await db_session.commit()
        
        response = await client.get(
            "/api/v1/categories",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5
        
    async def test_update_category(self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession, test_organization: Organization):
        """Test updating a category (admin only)."""
        category = Category(
            organization_id=test_organization.id,
            name="Original",
            slug="original"
        )
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        
        response = await client.put(
            f"/api/v1/categories/{category.id}",
            headers=admin_headers,
            json={
                "name": "Updated",
                "description": "Updated description"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        
    async def test_delete_category(self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession, test_organization: Organization):
        """Test deleting a category (admin only)."""
        category = Category(
            organization_id=test_organization.id,
            name="To Delete",
            slug="to-delete"
        )
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        
        response = await client.delete(
            f"/api/v1/categories/{category.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 204


@pytest.mark.integration
class TestAdminEndpoints:
    """Test admin API endpoints."""
    
    async def test_list_users(self, client: AsyncClient, admin_headers: dict):
        """Test listing users (admin only)."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
    async def test_get_user_details(self, client: AsyncClient, admin_headers: dict, test_user: User):
        """Test getting user details (admin only)."""
        response = await client.get(
            f"/api/v1/admin/users/{test_user.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        
    async def test_update_user_role(self, client: AsyncClient, admin_headers: dict, test_user: User):
        """Test updating user role (admin only)."""
        response = await client.put(
            f"/api/v1/admin/users/{test_user.id}/role",
            headers=admin_headers,
            json={"role": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        
    async def test_disable_user(self, client: AsyncClient, admin_headers: dict, test_user: User):
        """Test disabling a user (admin only)."""
        response = await client.post(
            f"/api/v1/admin/users/{test_user.id}/disable",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        
    async def test_get_system_stats(self, client: AsyncClient, admin_headers: dict):
        """Test getting system statistics (admin only)."""
        response = await client.get(
            "/api/v1/admin/stats",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_knowledge_items" in data
        assert "total_categories" in data
        
    async def test_non_admin_access_denied(self, client: AsyncClient, auth_headers: dict):
        """Test non-admin user cannot access admin endpoints."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert "Not enough permissions" in response.json()["detail"]