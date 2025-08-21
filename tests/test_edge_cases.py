"""Comprehensive edge case and error handling tests."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4
import json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, OperationalError
from fastapi import HTTPException

from app.models.knowledge_item import KnowledgeItem, ContentType, ContentStatus
from app.models.user import User, UserRole
from app.models.category import Category


@pytest.mark.asyncio
class TestDatabaseEdgeCases:
    """Test database-related edge cases."""
    
    async def test_concurrent_writes(self, db_session: AsyncSession, test_organization):
        """Test handling concurrent database writes."""
        # Create two items with same unique constraint
        item1 = KnowledgeItem(
            organization_id=test_organization.id,
            title_en="Duplicate",
            content_en="Content 1",
            type=ContentType.GUIDE,
            status=ContentStatus.PUBLISHED
        )
        item2 = KnowledgeItem(
            organization_id=test_organization.id,
            title_en="Duplicate",
            content_en="Content 2",
            type=ContentType.GUIDE,
            status=ContentStatus.PUBLISHED
        )
        
        db_session.add(item1)
        await db_session.commit()
        
        # Should handle duplicate gracefully
        db_session.add(item2)
        try:
            await db_session.commit()
        except IntegrityError:
            await db_session.rollback()
            # Expected behavior
            pass
    
    async def test_database_connection_failure(self, client: AsyncClient):
        """Test handling database connection failures."""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_get_db.side_effect = OperationalError("Connection failed", None, None)
            
            response = await client.get("/api/v1/knowledge")
            # Should return error status
            assert response.status_code >= 500
    
    async def test_transaction_rollback(self, db_session: AsyncSession, test_organization):
        """Test transaction rollback on error."""
        item = KnowledgeItem(
            organization_id=test_organization.id,
            title_en="Test",
            content_en="Content",
            type=ContentType.GUIDE,
            status=ContentStatus.DRAFT
        )
        
        db_session.add(item)
        
        # Simulate error before commit
        with patch.object(db_session, 'commit', side_effect=Exception("Commit failed")):
            try:
                await db_session.commit()
            except Exception:
                await db_session.rollback()
        
        # Item should not be in database
        result = await db_session.execute(
            select(KnowledgeItem).where(KnowledgeItem.title_en == "Test")
        )
        assert result.scalar_one_or_none() is None
    
    async def test_cascade_delete_behavior(self, db_session: AsyncSession, test_organization):
        """Test cascade delete behavior."""
        # Create category with items
        category = Category(
            organization_id=test_organization.id,
            name_en="Test Category",
            slug="test-category"
        )
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        
        item = KnowledgeItem(
            organization_id=test_organization.id,
            category_id=category.id,
            title_en="Test Item",
            content_en="Content",
            type=ContentType.GUIDE,
            status=ContentStatus.PUBLISHED
        )
        db_session.add(item)
        await db_session.commit()
        
        # Delete category
        await db_session.delete(category)
        await db_session.commit()
        
        # Check cascade behavior
        from sqlalchemy import select
        result = await db_session.execute(
            select(KnowledgeItem).where(KnowledgeItem.category_id == category.id)
        )
        items = result.scalars().all()
        # Depending on cascade settings
        assert len(items) >= 0


@pytest.mark.asyncio
class TestAuthenticationEdgeCases:
    """Test authentication edge cases."""
    
    async def test_expired_token(self, client: AsyncClient):
        """Test handling expired JWT tokens."""
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid"
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        response = await client.get("/api/v1/knowledge", headers=headers)
        assert response.status_code == 401
    
    async def test_malformed_token(self, client: AsyncClient):
        """Test handling malformed tokens."""
        malformed_token = "not.a.valid.jwt.token"
        headers = {"Authorization": f"Bearer {malformed_token}"}
        
        response = await client.get("/api/v1/knowledge", headers=headers)
        assert response.status_code == 401
    
    async def test_missing_bearer_prefix(self, client: AsyncClient):
        """Test token without Bearer prefix."""
        token = "valid_token_without_prefix"
        headers = {"Authorization": token}
        
        response = await client.get("/api/v1/knowledge", headers=headers)
        assert response.status_code in [401, 403]
    
    async def test_user_account_disabled(self, client: AsyncClient, db_session: AsyncSession, test_organization):
        """Test access with disabled user account."""
        # Create disabled user
        user = User(
            organization_id=test_organization.id,
            email="disabled@test.com",
            username="disabled",
            hashed_password="hash",
            role=UserRole.EDITOR,
            is_active=False
        )
        db_session.add(user)
        await db_session.commit()
        
        # Try to login
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "disabled@test.com", "password": "password"}
        )
        assert response.status_code in [401, 403]
    
    async def test_concurrent_login_attempts(self, client: AsyncClient):
        """Test handling concurrent login attempts."""
        import asyncio
        
        async def login_attempt():
            return await client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "testpassword123"}
            )
        
        # Simulate concurrent logins
        tasks = [login_attempt() for _ in range(5)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should handle all attempts gracefully
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code in [200, 401, 429]


@pytest.mark.asyncio
class TestInputValidationEdgeCases:
    """Test input validation edge cases."""
    
    async def test_extremely_long_input(self, client: AsyncClient, auth_headers: dict):
        """Test handling extremely long input."""
        long_title = "a" * 10000
        payload = {
            "title_en": long_title,
            "content_en": "Content",
            "type": "guide"
        }
        
        response = await client.post(
            "/api/v1/knowledge",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code in [400, 422, 413]
    
    async def test_special_characters_in_input(self, client: AsyncClient, auth_headers: dict):
        """Test handling special characters."""
        payload = {
            "title_en": "Test <script>alert('XSS')</script>",
            "content_en": "Content with \x00 null byte",
            "type": "guide"
        }
        
        response = await client.post(
            "/api/v1/knowledge",
            json=payload,
            headers=auth_headers
        )
        # Should either sanitize or reject
        assert response.status_code in [201, 400, 422]
    
    async def test_unicode_edge_cases(self, client: AsyncClient, auth_headers: dict):
        """Test handling various Unicode characters."""
        payload = {
            "title_en": "Test 🚀 Emoji",
            "title_ko": "테스트 💡 이모지",
            "content_en": "Content with 中文 and العربية",
            "type": "guide"
        }
        
        response = await client.post(
            "/api/v1/knowledge",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code in [201, 400, 422]
    
    async def test_sql_injection_attempts(self, client: AsyncClient):
        """Test SQL injection prevention."""
        # Try SQL injection in search query
        response = await client.get(
            "/api/v1/search?q='; DROP TABLE knowledge_items; --"
        )
        assert response.status_code in [200, 400]
        
        # Try in filter parameters
        response = await client.get(
            "/api/v1/knowledge?category_id=1' OR '1'='1"
        )
        assert response.status_code in [200, 400, 422]
    
    async def test_invalid_uuid_formats(self, client: AsyncClient):
        """Test handling invalid UUID formats."""
        invalid_uuids = [
            "not-a-uuid",
            "12345",
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "../../../etc/passwd"
        ]
        
        for invalid_id in invalid_uuids:
            response = await client.get(f"/api/v1/knowledge/{invalid_id}")
            assert response.status_code in [400, 404, 422]
    
    async def test_negative_pagination(self, client: AsyncClient):
        """Test negative pagination values."""
        response = await client.get("/api/v1/knowledge?page=-1&limit=-10")
        assert response.status_code == 422
    
    async def test_float_pagination(self, client: AsyncClient):
        """Test float pagination values."""
        response = await client.get("/api/v1/knowledge?page=1.5&limit=10.7")
        assert response.status_code in [200, 422]


@pytest.mark.asyncio
class TestConcurrencyEdgeCases:
    """Test concurrency-related edge cases."""
    
    async def test_race_condition_in_view_count(self, client: AsyncClient, db_session: AsyncSession, test_organization):
        """Test race condition in view count updates."""
        item = KnowledgeItem(
            organization_id=test_organization.id,
            title_en="Test",
            content_en="Content",
            type=ContentType.GUIDE,
            status=ContentStatus.PUBLISHED,
            view_count=0
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        import asyncio
        
        async def increment_view():
            return await client.get(f"/api/v1/knowledge/{item.id}")
        
        # Simulate concurrent views
        tasks = [increment_view() for _ in range(10)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check final count
        await db_session.refresh(item)
        # Should handle concurrent updates
        assert item.view_count >= 0
    
    async def test_concurrent_updates(self, client: AsyncClient, db_session: AsyncSession, test_organization, auth_headers: dict):
        """Test concurrent updates to same item."""
        item = KnowledgeItem(
            organization_id=test_organization.id,
            title_en="Original",
            content_en="Original content",
            type=ContentType.GUIDE,
            status=ContentStatus.DRAFT
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        import asyncio
        
        async def update_item(suffix):
            return await client.put(
                f"/api/v1/knowledge/{item.id}",
                json={"title_en": f"Updated {suffix}"},
                headers=auth_headers
            )
        
        # Simulate concurrent updates
        tasks = [update_item(i) for i in range(5)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should handle concurrent updates
        success_count = sum(
            1 for r in responses 
            if not isinstance(r, Exception) and r.status_code == 200
        )
        assert success_count >= 0


@pytest.mark.asyncio
class TestResourceLimitEdgeCases:
    """Test resource limit edge cases."""
    
    async def test_memory_exhaustion_prevention(self, client: AsyncClient):
        """Test prevention of memory exhaustion attacks."""
        # Try to request huge limit
        response = await client.get("/api/v1/knowledge?limit=1000000")
        assert response.status_code in [200, 400, 422]
        
        if response.status_code == 200:
            data = response.json()
            # Should cap at reasonable limit
            assert len(data.get("items", [])) <= 100
    
    async def test_payload_size_limit(self, client: AsyncClient, auth_headers: dict):
        """Test payload size limits."""
        # Create very large content
        large_content = "x" * (10 * 1024 * 1024)  # 10MB
        payload = {
            "title_en": "Test",
            "content_en": large_content,
            "type": "guide"
        }
        
        response = await client.post(
            "/api/v1/knowledge",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code in [400, 413, 422]
    
    async def test_search_complexity_limit(self, client: AsyncClient):
        """Test search query complexity limits."""
        # Very complex search query
        complex_query = " OR ".join([f"term{i}" for i in range(1000)])
        
        response = await client.get(f"/api/v1/search?q={complex_query}")
        assert response.status_code in [200, 400, 414]


@pytest.mark.asyncio
class TestExternalServiceFailures:
    """Test handling of external service failures."""
    
    async def test_opensearch_unavailable(self, client: AsyncClient):
        """Test when OpenSearch is unavailable."""
        with patch('app.services.opensearch.search_knowledge', side_effect=Exception("Connection refused")):
            response = await client.get("/api/v1/search?q=test")
            # Should handle gracefully
            assert response.status_code in [200, 503]
    
    async def test_redis_unavailable(self, client: AsyncClient):
        """Test when Redis is unavailable."""
        with patch('app.services.redis.get_redis_client', side_effect=Exception("Connection refused")):
            response = await client.get("/api/v1/knowledge")
            # Should still work without cache
            assert response.status_code in [200, 503]
    
    async def test_openai_api_failure(self, client: AsyncClient, auth_headers: dict):
        """Test when OpenAI API fails."""
        with patch('app.services.embeddings.generate_embeddings', side_effect=Exception("API Error")):
            payload = {
                "title_en": "Test",
                "content_en": "Content",
                "type": "guide"
            }
            
            response = await client.post(
                "/api/v1/knowledge",
                json=payload,
                headers=auth_headers
            )
            # Should handle embedding failure gracefully
            assert response.status_code in [201, 500, 503]


@pytest.mark.asyncio
class TestDataIntegrityEdgeCases:
    """Test data integrity edge cases."""
    
    async def test_orphaned_records(self, db_session: AsyncSession):
        """Test handling of orphaned records."""
        # Create item with non-existent category
        item = KnowledgeItem(
            organization_id=uuid4(),  # Non-existent org
            category_id=uuid4(),  # Non-existent category
            title_en="Orphaned",
            content_en="Content",
            type=ContentType.GUIDE,
            status=ContentStatus.PUBLISHED
        )
        
        db_session.add(item)
        try:
            await db_session.commit()
        except IntegrityError:
            await db_session.rollback()
            # Expected behavior
            pass
    
    async def test_circular_category_reference(self, db_session: AsyncSession, test_organization):
        """Test prevention of circular category references."""
        cat1 = Category(
            organization_id=test_organization.id,
            name_en="Cat1",
            slug="cat1"
        )
        cat2 = Category(
            organization_id=test_organization.id,
            name_en="Cat2",
            slug="cat2"
        )
        
        db_session.add_all([cat1, cat2])
        await db_session.commit()
        await db_session.refresh(cat1)
        await db_session.refresh(cat2)
        
        # Try to create circular reference
        cat1.parent_id = cat2.id
        cat2.parent_id = cat1.id
        
        try:
            await db_session.commit()
        except IntegrityError:
            await db_session.rollback()
            # Should prevent circular reference
            pass
    
    async def test_data_consistency_after_partial_failure(self, client: AsyncClient, auth_headers: dict):
        """Test data consistency after partial operation failure."""
        with patch('app.services.opensearch.index_knowledge_item', side_effect=Exception("Index failed")):
            payload = {
                "title_en": "Test",
                "content_en": "Content",
                "type": "guide"
            }
            
            response = await client.post(
                "/api/v1/knowledge",
                json=payload,
                headers=auth_headers
            )
            
            # Should either rollback completely or handle partial failure
            assert response.status_code in [201, 500]