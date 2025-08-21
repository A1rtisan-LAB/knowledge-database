"""Tests for knowledge item endpoints."""

import pytest
from httpx import AsyncClient
from app.models.user import User
from app.models.organization import Organization


@pytest.mark.asyncio
async def test_create_knowledge_item(client: AsyncClient, auth_headers: dict):
    """Test creating a knowledge item."""
    response = await client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={
            "type": "article",
            "slug": "test-article",
            "title_ko": "테스트 글",
            "title_en": "Test Article",
            "content_ko": "이것은 테스트 내용입니다.",
            "content_en": "This is test content.",
            "summary_ko": "테스트 요약",
            "summary_en": "Test summary",
            "tags": ["test", "sample"]
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "test-article"
    assert data["title_en"] == "Test Article"
    assert data["type"] == "article"
    assert data["status"] == "draft"
    assert data["tags"] == ["test", "sample"]


@pytest.mark.asyncio
async def test_create_duplicate_slug(client: AsyncClient, auth_headers: dict):
    """Test creating knowledge item with duplicate slug."""
    # Create first item
    await client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={
            "type": "article",
            "slug": "duplicate-slug",
            "title_ko": "첫번째",
            "title_en": "First",
            "content_ko": "내용",
            "content_en": "Content"
        }
    )
    
    # Try to create duplicate
    response = await client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={
            "type": "article",
            "slug": "duplicate-slug",
            "title_ko": "두번째",
            "title_en": "Second",
            "content_ko": "내용",
            "content_en": "Content"
        }
    )
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_knowledge_items(client: AsyncClient, auth_headers: dict):
    """Test listing knowledge items."""
    # Create some items
    for i in range(3):
        await client.post(
            "/api/v1/knowledge",
            headers=auth_headers,
            json={
                "type": "article",
                "slug": f"article-{i}",
                "title_ko": f"글 {i}",
                "title_en": f"Article {i}",
                "content_ko": f"내용 {i}",
                "content_en": f"Content {i}"
            }
        )
    
    # List items
    response = await client.get(
        "/api/v1/knowledge",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3
    assert "page" in data
    assert "limit" in data
    assert "has_more" in data


@pytest.mark.asyncio
async def test_get_knowledge_item(client: AsyncClient, auth_headers: dict):
    """Test getting a specific knowledge item."""
    # Create item
    create_response = await client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={
            "type": "faq",
            "slug": "test-faq",
            "title_ko": "자주 묻는 질문",
            "title_en": "Frequently Asked Question",
            "content_ko": "답변 내용",
            "content_en": "Answer content"
        }
    )
    item_id = create_response.json()["id"]
    
    # Get item
    response = await client.get(
        f"/api/v1/knowledge/{item_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["slug"] == "test-faq"
    assert data["content_en"] == "Answer content"


@pytest.mark.asyncio
async def test_update_knowledge_item(client: AsyncClient, auth_headers: dict):
    """Test updating a knowledge item."""
    # Create item
    create_response = await client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={
            "type": "guide",
            "slug": "update-test",
            "title_ko": "원래 제목",
            "title_en": "Original Title",
            "content_ko": "원래 내용",
            "content_en": "Original content"
        }
    )
    item_id = create_response.json()["id"]
    
    # Update item
    response = await client.put(
        f"/api/v1/knowledge/{item_id}",
        headers=auth_headers,
        json={
            "title_en": "Updated Title",
            "content_en": "Updated content"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["title_en"] == "Updated Title"
    assert data["content_en"] == "Updated content"
    assert data["title_ko"] == "원래 제목"  # Unchanged


@pytest.mark.asyncio
async def test_publish_knowledge_item(client: AsyncClient, auth_headers: dict):
    """Test publishing a knowledge item."""
    # Create item
    create_response = await client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={
            "type": "article",
            "slug": "publish-test",
            "title_ko": "출판 테스트",
            "title_en": "Publish Test",
            "content_ko": "내용",
            "content_en": "Content"
        }
    )
    item_id = create_response.json()["id"]
    
    # Publish item
    response = await client.post(
        f"/api/v1/knowledge/{item_id}/publish",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "published"
    assert data["published_at"] is not None


@pytest.mark.asyncio
async def test_delete_knowledge_item(client: AsyncClient, auth_headers: dict):
    """Test deleting a knowledge item."""
    # Create item
    create_response = await client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={
            "type": "article",
            "slug": "delete-test",
            "title_ko": "삭제 테스트",
            "title_en": "Delete Test",
            "content_ko": "내용",
            "content_en": "Content"
        }
    )
    item_id = create_response.json()["id"]
    
    # Delete item
    response = await client.delete(
        f"/api/v1/knowledge/{item_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 204
    
    # Verify soft delete by trying to get the item
    get_response = await client.get(
        f"/api/v1/knowledge/{item_id}",
        headers=auth_headers
    )
    # Should still be accessible to editors but with deleted status
    assert get_response.status_code == 200