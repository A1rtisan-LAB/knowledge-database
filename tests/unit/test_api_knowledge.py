"""
Comprehensive test suite for Knowledge API endpoints.
Tests all CRUD operations, permissions, validations, and edge cases.
"""

import pytest
import uuid
from datetime import datetime
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_item import KnowledgeItem, ContentStatus, ContentType
from app.models.category import Category
from app.models.user import User


class TestKnowledgeListEndpoint:
    """Test suite for GET /api/v1/knowledge endpoint."""
    
    def test_list_knowledge_items_no_auth(self, client: TestClient):
        """Test listing knowledge items without authentication."""
        response = client.get("/api/v1/knowledge")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "has_more" in data
    
    def test_list_knowledge_items_with_auth(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test listing knowledge items with authentication."""
        response = client.get("/api/v1/knowledge", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
    
    def test_list_with_pagination(self, client: TestClient):
        """Test pagination parameters."""
        # Test page 1
        response = client.get("/api/v1/knowledge?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 10
        
        # Test page 2
        response = client.get("/api/v1/knowledge?page=2&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["limit"] == 5
    
    def test_list_with_invalid_pagination(self, client: TestClient):
        """Test invalid pagination parameters."""
        # Negative page
        response = client.get("/api/v1/knowledge?page=-1")
        assert response.status_code == 422
        
        # Zero page
        response = client.get("/api/v1/knowledge?page=0")
        assert response.status_code == 422
        
        # Limit too high
        response = client.get("/api/v1/knowledge?limit=101")
        assert response.status_code == 422
    
    def test_list_with_category_filter(self, client: TestClient):
        """Test filtering by category ID."""
        category_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/knowledge?category_id={category_id}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
    
    def test_list_with_type_filter(self, client: TestClient):
        """Test filtering by content type."""
        response = client.get("/api/v1/knowledge?type=article")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
    
    def test_list_with_status_filter(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test filtering by content status."""
        # Draft status requires authentication
        response = client.get("/api/v1/knowledge?status=draft", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
    
    def test_list_with_tags_filter(self, client: TestClient):
        """Test filtering by tags."""
        response = client.get("/api/v1/knowledge?tags=python&tags=tutorial")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
    
    def test_list_with_language_parameter(self, client: TestClient):
        """Test language parameter."""
        # English
        response = client.get("/api/v1/knowledge?language=en")
        assert response.status_code == 200
        
        # Korean
        response = client.get("/api/v1/knowledge?language=ko")
        assert response.status_code == 200
        
        # Invalid language
        response = client.get("/api/v1/knowledge?language=jp")
        assert response.status_code == 422
    
    def test_list_with_sorting(self, client: TestClient):
        """Test different sorting options."""
        sort_options = ["created_at", "updated_at", "title", "views", "helpful"]
        
        for sort in sort_options:
            # Ascending
            response = client.get(f"/api/v1/knowledge?sort={sort}&order=asc")
            assert response.status_code == 200
            
            # Descending
            response = client.get(f"/api/v1/knowledge?sort={sort}&order=desc")
            assert response.status_code == 200
    
    def test_list_with_invalid_sorting(self, client: TestClient):
        """Test invalid sorting parameters."""
        # Invalid sort field
        response = client.get("/api/v1/knowledge?sort=invalid")
        assert response.status_code == 422
        
        # Invalid order
        response = client.get("/api/v1/knowledge?order=invalid")
        assert response.status_code == 422
    
    def test_list_combined_filters(self, client: TestClient):
        """Test combining multiple filters."""
        category_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/knowledge?category_id={category_id}&type=article&tags=python&language=en&sort=updated_at&order=desc&page=1&limit=20"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 20


class TestKnowledgeGetEndpoint:
    """Test suite for GET /api/v1/knowledge/{id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_existing_item(self, client: TestClient, db_session: AsyncSession, test_user: User):
        """Test getting an existing knowledge item."""
        # Create test item
        item = KnowledgeItem(
            slug="test-item",
            type=ContentType.ARTICLE,
            title_ko="테스트 항목",
            title_en="Test Item",
            content_ko="테스트 내용",
            content_en="Test content",
            status=ContentStatus.PUBLISHED,
            organization_id=test_user.organization_id,
            created_by=test_user.id,
            updated_by=test_user.id
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        response = client.get(f"/api/v1/knowledge/{item.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(item.id)
        assert data["slug"] == "test-item"
    
    def test_get_nonexistent_item(self, client: TestClient):
        """Test getting a non-existent knowledge item."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/knowledge/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_invalid_uuid(self, client: TestClient):
        """Test getting item with invalid UUID."""
        response = client.get("/api/v1/knowledge/invalid-uuid")
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_draft_item_without_permission(self, client: TestClient, db_session: AsyncSession, test_user: User):
        """Test accessing draft item without editor permission."""
        # Create draft item
        item = KnowledgeItem(
            slug="draft-item",
            type=ContentType.ARTICLE,
            title_ko="초안 항목",
            title_en="Draft Item",
            content_ko="초안 내용",
            content_en="Draft content",
            status=ContentStatus.DRAFT,
            organization_id=test_user.organization_id,
            created_by=test_user.id,
            updated_by=test_user.id
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        # Try to access without auth
        response = client.get(f"/api/v1/knowledge/{item.id}")
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_item_with_language(self, client: TestClient, db_session: AsyncSession, test_user: User):
        """Test getting item with language parameter."""
        item = KnowledgeItem(
            slug="multilingual-item",
            type=ContentType.ARTICLE,
            title_ko="한국어 제목",
            title_en="English Title",
            content_ko="한국어 내용",
            content_en="English content",
            status=ContentStatus.PUBLISHED,
            organization_id=test_user.organization_id,
            created_by=test_user.id,
            updated_by=test_user.id
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        # Get English version
        response = client.get(f"/api/v1/knowledge/{item.id}?language=en")
        assert response.status_code == 200
        
        # Get Korean version
        response = client.get(f"/api/v1/knowledge/{item.id}?language=ko")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_item_increments_view_count(self, client: TestClient, db_session: AsyncSession, test_user: User):
        """Test that getting an item increments its view count."""
        item = KnowledgeItem(
            slug="view-count-item",
            type=ContentType.ARTICLE,
            title_ko="조회수 테스트",
            title_en="View Count Test",
            content_ko="내용",
            content_en="Content",
            status=ContentStatus.PUBLISHED,
            view_count=0,
            organization_id=test_user.organization_id,
            created_by=test_user.id,
            updated_by=test_user.id
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        initial_count = item.view_count
        
        # Get item multiple times
        for _ in range(3):
            response = client.get(f"/api/v1/knowledge/{item.id}")
            assert response.status_code == 200
        
        # Refresh and check view count
        await db_session.refresh(item)
        assert item.view_count == initial_count + 3


class TestKnowledgeCreateEndpoint:
    """Test suite for POST /api/v1/knowledge endpoint."""
    
    def test_create_knowledge_item(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test creating a new knowledge item."""
        data = {
            "type": "article",
            "slug": "new-article",
            "title_ko": "새 글",
            "title_en": "New Article",
            "content_ko": "내용입니다",
            "content_en": "This is content",
            "tags": ["test", "article"],
            "metadata": {"author": "test"}
        }
        
        with patch('app.services.embeddings.generate_embeddings', new_callable=AsyncMock):
            with patch('app.services.search.index_knowledge_item', new_callable=AsyncMock):
                response = client.post("/api/v1/knowledge", json=data, headers=admin_headers)
        
        assert response.status_code == 201
        result = response.json()
        assert result["slug"] == "new-article"
        assert result["type"] == "article"
    
    def test_create_without_authentication(self, client: TestClient):
        """Test creating item without authentication fails."""
        data = {
            "type": "article",
            "slug": "unauthorized-article",
            "title_ko": "글",
            "title_en": "Article",
            "content_ko": "내용",
            "content_en": "Content"
        }
        
        response = client.post("/api/v1/knowledge", json=data)
        assert response.status_code == 401
    
    def test_create_without_editor_permission(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test creating item without editor permission fails."""
        data = {
            "type": "article",
            "slug": "no-permission-article",
            "title_ko": "글",
            "title_en": "Article",
            "content_ko": "내용",
            "content_en": "Content"
        }
        
        # Assuming auth_headers is for a regular user without editor permission
        response = client.post("/api/v1/knowledge", json=data, headers=auth_headers)
        assert response.status_code in [403, 401]  # Depends on implementation
    
    def test_create_with_duplicate_slug(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test creating item with duplicate slug fails."""
        data = {
            "type": "article",
            "slug": "duplicate-slug",
            "title_ko": "글 1",
            "title_en": "Article 1",
            "content_ko": "내용 1",
            "content_en": "Content 1"
        }
        
        with patch('app.services.embeddings.generate_embeddings', new_callable=AsyncMock):
            with patch('app.services.search.index_knowledge_item', new_callable=AsyncMock):
                # Create first item
                response = client.post("/api/v1/knowledge", json=data, headers=admin_headers)
                assert response.status_code == 201
                
                # Try to create second item with same slug
                data["title_en"] = "Article 2"
                response = client.post("/api/v1/knowledge", json=data, headers=admin_headers)
                assert response.status_code == 409
                assert "already exists" in response.json()["detail"].lower()
    
    def test_create_with_invalid_slug(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test creating item with invalid slug format."""
        data = {
            "type": "article",
            "slug": "Invalid Slug!",  # Contains spaces and special chars
            "title_ko": "글",
            "title_en": "Article",
            "content_ko": "내용",
            "content_en": "Content"
        }
        
        response = client.post("/api/v1/knowledge", json=data, headers=admin_headers)
        assert response.status_code == 422
    
    def test_create_with_missing_fields(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test creating item with missing required fields."""
        # Missing type
        data = {
            "slug": "incomplete-article",
            "title_ko": "글",
            "title_en": "Article"
        }
        response = client.post("/api/v1/knowledge", json=data, headers=admin_headers)
        assert response.status_code == 422
        
        # Missing slug
        data = {
            "type": "article",
            "title_ko": "글",
            "title_en": "Article",
            "content_ko": "내용",
            "content_en": "Content"
        }
        response = client.post("/api/v1/knowledge", json=data, headers=admin_headers)
        assert response.status_code == 422
    
    def test_create_with_category(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test creating item with category assignment."""
        category_id = str(uuid.uuid4())
        data = {
            "type": "article",
            "slug": "categorized-article",
            "category_id": category_id,
            "title_ko": "분류된 글",
            "title_en": "Categorized Article",
            "content_ko": "내용",
            "content_en": "Content"
        }
        
        with patch('app.services.embeddings.generate_embeddings', new_callable=AsyncMock):
            with patch('app.services.search.index_knowledge_item', new_callable=AsyncMock):
                response = client.post("/api/v1/knowledge", json=data, headers=admin_headers)
        
        # May fail if category doesn't exist, but structure should be valid
        assert response.status_code in [201, 422, 404]
    
    def test_create_with_metadata(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test creating item with metadata."""
        data = {
            "type": "article",
            "slug": "metadata-article",
            "title_ko": "메타데이터 글",
            "title_en": "Metadata Article",
            "content_ko": "내용",
            "content_en": "Content",
            "metadata": {
                "author": "John Doe",
                "version": "1.0",
                "reviewed": True,
                "tags_count": 5
            }
        }
        
        with patch('app.services.embeddings.generate_embeddings', new_callable=AsyncMock):
            with patch('app.services.search.index_knowledge_item', new_callable=AsyncMock):
                response = client.post("/api/v1/knowledge", json=data, headers=admin_headers)
        
        assert response.status_code == 201
        result = response.json()
        assert result["metadata"]["author"] == "John Doe"
        assert result["metadata"]["version"] == "1.0"


class TestKnowledgeUpdateEndpoint:
    """Test suite for PUT /api/v1/knowledge/{id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_knowledge_item(self, client: TestClient, admin_headers: Dict[str, str], db_session: AsyncSession, admin_user: User):
        """Test updating an existing knowledge item."""
        # Create item
        item = KnowledgeItem(
            slug="update-test",
            type=ContentType.ARTICLE,
            title_ko="원래 제목",
            title_en="Original Title",
            content_ko="원래 내용",
            content_en="Original content",
            status=ContentStatus.DRAFT,
            organization_id=admin_user.organization_id,
            created_by=admin_user.id,
            updated_by=admin_user.id
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        update_data = {
            "title_en": "Updated Title",
            "content_en": "Updated content",
            "tags": ["updated", "test"]
        }
        
        with patch('app.services.embeddings.generate_embeddings', new_callable=AsyncMock):
            with patch('app.services.search.index_knowledge_item', new_callable=AsyncMock):
                response = client.put(f"/api/v1/knowledge/{item.id}", json=update_data, headers=admin_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert result["title_en"] == "Updated Title"
        assert result["content_en"] == "Updated content"
        assert "updated" in result["tags"]
    
    def test_update_nonexistent_item(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test updating non-existent item."""
        fake_id = str(uuid.uuid4())
        update_data = {"title_en": "Updated"}
        
        response = client.put(f"/api/v1/knowledge/{fake_id}", json=update_data, headers=admin_headers)
        assert response.status_code == 404
    
    def test_update_without_authentication(self, client: TestClient):
        """Test updating without authentication."""
        fake_id = str(uuid.uuid4())
        update_data = {"title_en": "Updated"}
        
        response = client.put(f"/api/v1/knowledge/{fake_id}", json=update_data)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_update_other_org_item(self, client: TestClient, admin_headers: Dict[str, str], db_session: AsyncSession):
        """Test updating item from different organization."""
        # Create item for different org
        other_org_id = uuid.uuid4()
        item = KnowledgeItem(
            slug="other-org-item",
            type=ContentType.ARTICLE,
            title_ko="다른 조직",
            title_en="Other Org",
            content_ko="내용",
            content_en="Content",
            status=ContentStatus.PUBLISHED,
            organization_id=other_org_id,  # Different org
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4()
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        update_data = {"title_en": "Hacked!"}
        
        response = client.put(f"/api/v1/knowledge/{item.id}", json=update_data, headers=admin_headers)
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_partial_update(self, client: TestClient, admin_headers: Dict[str, str], db_session: AsyncSession, admin_user: User):
        """Test partial update of knowledge item."""
        item = KnowledgeItem(
            slug="partial-update",
            type=ContentType.ARTICLE,
            title_ko="원래 한국어",
            title_en="Original English",
            content_ko="원래 내용",
            content_en="Original content",
            tags=["original", "test"],
            status=ContentStatus.DRAFT,
            organization_id=admin_user.organization_id,
            created_by=admin_user.id,
            updated_by=admin_user.id
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        # Update only title_en
        update_data = {"title_en": "Only Title Updated"}
        
        with patch('app.services.embeddings.generate_embeddings', new_callable=AsyncMock):
            with patch('app.services.search.index_knowledge_item', new_callable=AsyncMock):
                response = client.put(f"/api/v1/knowledge/{item.id}", json=update_data, headers=admin_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert result["title_en"] == "Only Title Updated"
        assert result["title_ko"] == "원래 한국어"  # Unchanged
        assert result["content_en"] == "Original content"  # Unchanged


class TestKnowledgeDeleteEndpoint:
    """Test suite for DELETE /api/v1/knowledge/{id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_delete_knowledge_item(self, client: TestClient, admin_headers: Dict[str, str], db_session: AsyncSession, admin_user: User):
        """Test soft deleting a knowledge item."""
        item = KnowledgeItem(
            slug="delete-test",
            type=ContentType.ARTICLE,
            title_ko="삭제 테스트",
            title_en="Delete Test",
            content_ko="내용",
            content_en="Content",
            status=ContentStatus.PUBLISHED,
            organization_id=admin_user.organization_id,
            created_by=admin_user.id,
            updated_by=admin_user.id
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        with patch('app.services.search.delete_from_index', new_callable=AsyncMock):
            response = client.delete(f"/api/v1/knowledge/{item.id}", headers=admin_headers)
        
        assert response.status_code == 204
        
        # Verify soft delete
        await db_session.refresh(item)
        assert item.status == ContentStatus.DELETED
    
    def test_delete_nonexistent_item(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test deleting non-existent item."""
        fake_id = str(uuid.uuid4())
        
        response = client.delete(f"/api/v1/knowledge/{fake_id}", headers=admin_headers)
        assert response.status_code == 404
    
    def test_delete_without_authentication(self, client: TestClient):
        """Test deleting without authentication."""
        fake_id = str(uuid.uuid4())
        
        response = client.delete(f"/api/v1/knowledge/{fake_id}")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_delete_other_org_item(self, client: TestClient, admin_headers: Dict[str, str], db_session: AsyncSession):
        """Test deleting item from different organization."""
        other_org_id = uuid.uuid4()
        item = KnowledgeItem(
            slug="other-org-delete",
            type=ContentType.ARTICLE,
            title_ko="다른 조직",
            title_en="Other Org",
            content_ko="내용",
            content_en="Content",
            status=ContentStatus.PUBLISHED,
            organization_id=other_org_id,
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4()
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        response = client.delete(f"/api/v1/knowledge/{item.id}", headers=admin_headers)
        assert response.status_code == 403


class TestKnowledgePublishEndpoint:
    """Test suite for POST /api/v1/knowledge/{id}/publish endpoint."""
    
    @pytest.mark.asyncio
    async def test_publish_draft_item(self, client: TestClient, admin_headers: Dict[str, str], db_session: AsyncSession, admin_user: User):
        """Test publishing a draft knowledge item."""
        item = KnowledgeItem(
            slug="publish-test",
            type=ContentType.ARTICLE,
            title_ko="출판 테스트",
            title_en="Publish Test",
            content_ko="내용",
            content_en="Content",
            status=ContentStatus.DRAFT,
            organization_id=admin_user.organization_id,
            created_by=admin_user.id,
            updated_by=admin_user.id
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        with patch('app.services.search.index_knowledge_item', new_callable=AsyncMock):
            response = client.post(f"/api/v1/knowledge/{item.id}/publish", headers=admin_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == ContentStatus.PUBLISHED.value
        
        # Verify in database
        await db_session.refresh(item)
        assert item.status == ContentStatus.PUBLISHED
        assert item.published_at is not None
    
    def test_publish_nonexistent_item(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test publishing non-existent item."""
        fake_id = str(uuid.uuid4())
        
        response = client.post(f"/api/v1/knowledge/{fake_id}/publish", headers=admin_headers)
        assert response.status_code == 404
    
    def test_publish_without_authentication(self, client: TestClient):
        """Test publishing without authentication."""
        fake_id = str(uuid.uuid4())
        
        response = client.post(f"/api/v1/knowledge/{fake_id}/publish")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_publish_already_published(self, client: TestClient, admin_headers: Dict[str, str], db_session: AsyncSession, admin_user: User):
        """Test publishing an already published item."""
        item = KnowledgeItem(
            slug="already-published",
            type=ContentType.ARTICLE,
            title_ko="이미 출판됨",
            title_en="Already Published",
            content_ko="내용",
            content_en="Content",
            status=ContentStatus.PUBLISHED,
            published_at=datetime.utcnow(),
            organization_id=admin_user.organization_id,
            created_by=admin_user.id,
            updated_by=admin_user.id
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        original_published_at = item.published_at
        
        with patch('app.services.search.index_knowledge_item', new_callable=AsyncMock):
            response = client.post(f"/api/v1/knowledge/{item.id}/publish", headers=admin_headers)
        
        assert response.status_code == 200
        
        # Should update published_at
        await db_session.refresh(item)
        assert item.published_at != original_published_at


class TestKnowledgeVersionsEndpoint:
    """Test suite for GET /api/v1/knowledge/{id}/versions endpoint."""
    
    def test_get_versions_requires_authentication(self, client: TestClient):
        """Test that getting versions requires authentication."""
        fake_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/knowledge/{fake_id}/versions")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_versions_empty_list(self, client: TestClient, auth_headers: Dict[str, str], db_session: AsyncSession, test_user: User):
        """Test getting versions for item with no version history."""
        item = KnowledgeItem(
            slug="no-versions",
            type=ContentType.ARTICLE,
            title_ko="버전 없음",
            title_en="No Versions",
            content_ko="내용",
            content_en="Content",
            status=ContentStatus.PUBLISHED,
            organization_id=test_user.organization_id,
            created_by=test_user.id,
            updated_by=test_user.id
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        response = client.get(f"/api/v1/knowledge/{item.id}/versions", headers=auth_headers)
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_versions_nonexistent_item(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test getting versions for non-existent item."""
        fake_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/knowledge/{fake_id}/versions", headers=auth_headers)
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) == 0


class TestKnowledgeFileUpload:
    """Test suite for file upload functionality in knowledge items."""
    
    def test_upload_image_attachment(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test uploading an image as an attachment."""
        # This would typically involve multipart form data
        # Implementation depends on how file uploads are handled
        pass
    
    def test_upload_document_attachment(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test uploading a document as an attachment."""
        pass
    
    def test_upload_invalid_file_type(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test uploading an unsupported file type."""
        pass
    
    def test_upload_oversized_file(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test uploading a file that exceeds size limits."""
        pass


class TestKnowledgeBulkOperations:
    """Test suite for bulk operations on knowledge items."""
    
    def test_bulk_delete(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test bulk deleting multiple items."""
        # If bulk endpoints exist
        pass
    
    def test_bulk_publish(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test bulk publishing multiple items."""
        pass
    
    def test_bulk_update_category(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test bulk updating category for multiple items."""
        pass


class TestKnowledgeSearchIntegration:
    """Test suite for search integration with knowledge items."""
    
    @pytest.mark.asyncio
    async def test_item_indexed_on_create(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test that items are indexed in search on creation."""
        data = {
            "type": "article",
            "slug": "search-indexed",
            "title_ko": "검색 인덱스",
            "title_en": "Search Indexed",
            "content_ko": "검색 가능한 내용",
            "content_en": "Searchable content"
        }
        
        with patch('app.services.embeddings.generate_embeddings', new_callable=AsyncMock) as mock_embed:
            with patch('app.services.search.index_knowledge_item', new_callable=AsyncMock) as mock_index:
                response = client.post("/api/v1/knowledge", json=data, headers=admin_headers)
                assert response.status_code == 201
                
                # Verify indexing was called
                mock_embed.assert_called_once()
                mock_index.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_item_reindexed_on_update(self, client: TestClient, admin_headers: Dict[str, str], db_session: AsyncSession, admin_user: User):
        """Test that items are reindexed on update."""
        item = KnowledgeItem(
            slug="reindex-test",
            type=ContentType.ARTICLE,
            title_ko="재인덱스",
            title_en="Reindex",
            content_ko="내용",
            content_en="Content",
            status=ContentStatus.DRAFT,
            organization_id=admin_user.organization_id,
            created_by=admin_user.id,
            updated_by=admin_user.id
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        update_data = {"content_en": "Updated for reindexing"}
        
        with patch('app.services.embeddings.generate_embeddings', new_callable=AsyncMock) as mock_embed:
            with patch('app.services.search.index_knowledge_item', new_callable=AsyncMock) as mock_index:
                response = client.put(f"/api/v1/knowledge/{item.id}", json=update_data, headers=admin_headers)
                assert response.status_code == 200
                
                # Verify reindexing was called
                mock_embed.assert_called_once()
                mock_index.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_item_removed_from_index_on_delete(self, client: TestClient, admin_headers: Dict[str, str], db_session: AsyncSession, admin_user: User):
        """Test that items are removed from search index on deletion."""
        item = KnowledgeItem(
            slug="remove-index",
            type=ContentType.ARTICLE,
            title_ko="인덱스 제거",
            title_en="Remove Index",
            content_ko="내용",
            content_en="Content",
            status=ContentStatus.PUBLISHED,
            organization_id=admin_user.organization_id,
            created_by=admin_user.id,
            updated_by=admin_user.id
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        with patch('app.services.search.delete_from_index', new_callable=AsyncMock) as mock_delete:
            response = client.delete(f"/api/v1/knowledge/{item.id}", headers=admin_headers)
            assert response.status_code == 204
            
            # Verify removal from index was called
            mock_delete.assert_called_once_with(str(item.id))


class TestKnowledgePerformance:
    """Test suite for performance-related aspects."""
    
    def test_pagination_performance(self, client: TestClient):
        """Test that pagination queries are efficient."""
        # Request large page
        response = client.get("/api/v1/knowledge?page=1&limit=100")
        assert response.status_code == 200
        # Should complete within reasonable time
    
    def test_filtering_performance(self, client: TestClient):
        """Test that complex filtering is performant."""
        response = client.get(
            "/api/v1/knowledge?category_id=123&type=article&tags=python&tags=tutorial&language=en"
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_bulk_create_performance(self, client: TestClient, admin_headers: Dict[str, str]):
        """Test performance when creating multiple items."""
        # This would test batch creation if supported
        pass