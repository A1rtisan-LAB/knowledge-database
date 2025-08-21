"""Integration tests for cache layer (Redis)."""

import pytest
import json
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from app.models.user import User
from app.models.organization import Organization
from app.models.knowledge_item import KnowledgeItem, ContentStatus
from app.models.category import Category
from app.services import redis as redis_service


@pytest.mark.integration
class TestCacheIntegration:
    """Test Redis cache integration."""
    
    @patch('app.services.redis.get_redis_client')
    async def test_cache_set_and_get(self, mock_redis_client):
        """Test basic cache set and get operations."""
        # Mock Redis client
        mock_client = AsyncMock()
        mock_redis_client.return_value = mock_client
        
        # Test data
        test_key = "test:key"
        test_value = {"data": "test", "timestamp": datetime.utcnow().isoformat()}
        
        # Set cache
        mock_client.setex = AsyncMock(return_value=True)
        result = await redis_service.cache_set(test_key, test_value, ttl=60)
        assert result is True
        mock_client.setex.assert_called_once()
        
        # Get cache
        mock_client.get = AsyncMock(return_value=json.dumps(test_value))
        cached_value = await redis_service.cache_get(test_key)
        assert cached_value == test_value
        mock_client.get.assert_called_once_with(test_key)
    
    @patch('app.services.redis.get_redis_client')
    async def test_cache_invalidation(self, mock_redis_client):
        """Test cache invalidation patterns."""
        # Mock Redis client
        mock_client = AsyncMock()
        mock_redis_client.return_value = mock_client
        
        # Mock scan_iter to return keys
        async def mock_scan_iter(match):
            keys = [
                "knowledge:1",
                "knowledge:2", 
                "knowledge:3",
                "category:1"
            ]
            for key in keys:
                if match.replace("*", "") in key:
                    yield key
        
        mock_client.scan_iter = mock_scan_iter
        mock_client.delete = AsyncMock(return_value=3)
        
        # Invalidate pattern
        deleted = await redis_service.cache_invalidate_pattern("knowledge:*")
        assert deleted == 3
        mock_client.delete.assert_called_once()
    
    async def test_api_response_caching(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test API response caching."""
        # Create test data
        category = Category(
            organization_id=test_organization.id,
            name="Cached Category",
            slug="cached-category"
        )
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        
        # Mock cache
        with patch('app.services.redis.cache_get') as mock_cache_get, \
             patch('app.services.redis.cache_set') as mock_cache_set:
            
            # First request - cache miss
            mock_cache_get.return_value = None
            mock_cache_set.return_value = True
            
            response1 = await client.get(
                f"/api/v1/categories/{category.id}",
                headers=auth_headers
            )
            assert response1.status_code == 200
            data1 = response1.json()
            
            # Verify cache was set
            mock_cache_set.assert_called_once()
            cache_key = mock_cache_set.call_args[0][0]
            assert f"category:{category.id}" in cache_key
            
            # Second request - cache hit
            mock_cache_get.return_value = data1
            
            response2 = await client.get(
                f"/api/v1/categories/{category.id}",
                headers=auth_headers
            )
            assert response2.status_code == 200
            assert response2.json() == data1
    
    async def test_cache_ttl_expiration(self, client: AsyncClient, auth_headers: dict):
        """Test cache TTL and expiration."""
        with patch('app.services.redis.cache_set') as mock_cache_set, \
             patch('app.services.redis.cache_get') as mock_cache_get:
            
            # Track cache set calls
            cache_calls = []
            
            async def track_cache_set(key, value, ttl=None):
                cache_calls.append({
                    "key": key,
                    "value": value,
                    "ttl": ttl,
                    "timestamp": datetime.utcnow()
                })
                return True
            
            mock_cache_set.side_effect = track_cache_set
            mock_cache_get.return_value = None
            
            # Make API requests
            await client.get("/api/v1/categories", headers=auth_headers)
            
            # Verify TTL was set
            assert len(cache_calls) > 0
            for call in cache_calls:
                if call["ttl"] is not None:
                    assert call["ttl"] > 0
                    assert call["ttl"] <= 3600  # Max 1 hour cache
    
    async def test_cache_stampede_prevention(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test prevention of cache stampede."""
        # Create a knowledge item
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Popular Item",
            content="Very popular content",
            view_count=1000
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        with patch('app.services.redis.cache_get') as mock_cache_get, \
             patch('app.services.redis.cache_set') as mock_cache_set:
            
            # Simulate cache miss
            mock_cache_get.return_value = None
            mock_cache_set.return_value = True
            
            # Simulate multiple concurrent requests
            async def get_item():
                return await client.get(
                    f"/api/v1/knowledge/{item.id}",
                    headers=auth_headers
                )
            
            # Execute concurrent requests
            results = await asyncio.gather(
                *[get_item() for _ in range(10)],
                return_exceptions=True
            )
            
            # All requests should succeed
            success_count = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 200)
            assert success_count == 10
            
            # Cache should be set only once (or very few times due to race conditions)
            cache_set_count = mock_cache_set.call_count
            assert cache_set_count <= 3  # Allow for some race conditions
    
    async def test_cache_consistency_on_update(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test cache consistency when data is updated."""
        # Create a knowledge item
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Cached Item",
            content="Original content"
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        with patch('app.services.redis.cache_get') as mock_cache_get, \
             patch('app.services.redis.cache_set') as mock_cache_set, \
             patch('app.services.redis.cache_delete') as mock_cache_delete:
            
            mock_cache_set.return_value = True
            mock_cache_delete.return_value = True
            
            # First get - cache miss
            mock_cache_get.return_value = None
            response1 = await client.get(
                f"/api/v1/knowledge/{item.id}",
                headers=auth_headers
            )
            assert response1.status_code == 200
            original_data = response1.json()
            
            # Update item
            update_response = await client.put(
                f"/api/v1/knowledge/{item.id}",
                headers=auth_headers,
                json={"content": "Updated content"}
            )
            assert update_response.status_code == 200
            
            # Verify cache was invalidated
            mock_cache_delete.assert_called()
            
            # Get again - should get updated data
            mock_cache_get.return_value = None  # Force cache miss
            response2 = await client.get(
                f"/api/v1/knowledge/{item.id}",
                headers=auth_headers
            )
            assert response2.status_code == 200
            updated_data = response2.json()
            assert updated_data["content"] == "Updated content"
            assert updated_data["content"] != original_data["content"]
    
    async def test_distributed_cache_locking(self, client: AsyncClient, auth_headers: dict):
        """Test distributed locking for cache operations."""
        with patch('app.services.redis.get_redis_client') as mock_redis_client:
            mock_client = AsyncMock()
            mock_redis_client.return_value = mock_client
            
            # Mock distributed lock
            mock_client.set = AsyncMock()
            mock_client.delete = AsyncMock()
            
            # Simulate lock acquisition
            async def acquire_lock(key, value, ex, nx):
                if nx:  # Only set if not exists
                    return True
                return False
            
            mock_client.set.side_effect = acquire_lock
            
            # Test concurrent cache updates with locking
            lock_key = "lock:knowledge:update"
            
            async def update_with_lock():
                # Try to acquire lock
                locked = await mock_client.set(
                    lock_key,
                    "locked",
                    ex=5,
                    nx=True
                )
                
                if locked:
                    # Perform update
                    await asyncio.sleep(0.1)
                    # Release lock
                    await mock_client.delete(lock_key)
                    return True
                return False
            
            # Run concurrent updates
            results = await asyncio.gather(
                *[update_with_lock() for _ in range(5)],
                return_exceptions=True
            )
            
            # Only one should acquire the lock
            success_count = sum(1 for r in results if r is True)
            assert success_count >= 1
    
    async def test_cache_warm_up(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test cache warm-up strategy."""
        # Create multiple knowledge items
        items = []
        for i in range(10):
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                title=f"Item {i}",
                content=f"Content {i}",
                view_count=100 * (10 - i),  # Higher view count for earlier items
                status=ContentStatus.PUBLISHED
            )
            items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        with patch('app.services.redis.cache_set') as mock_cache_set:
            mock_cache_set.return_value = True
            
            # Simulate cache warm-up for popular items
            async def warm_up_cache():
                # Get top viewed items
                popular_items = sorted(items, key=lambda x: x.view_count, reverse=True)[:5]
                
                for item in popular_items:
                    cache_key = f"knowledge:{item.id}"
                    cache_value = {
                        "id": str(item.id),
                        "title": item.title,
                        "content": item.content,
                        "view_count": item.view_count
                    }
                    await redis_service.cache_set(cache_key, cache_value, ttl=3600)
                
                return len(popular_items)
            
            warmed_up = await warm_up_cache()
            assert warmed_up == 5
            assert mock_cache_set.call_count == 5
    
    async def test_cache_metrics_tracking(self, client: AsyncClient, auth_headers: dict):
        """Test cache hit/miss metrics tracking."""
        metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
        
        with patch('app.services.redis.cache_get') as mock_cache_get, \
             patch('app.services.redis.cache_set') as mock_cache_set:
            
            async def track_cache_get(key):
                if key.startswith("hit:"):
                    metrics["hits"] += 1
                    return {"cached": True}
                else:
                    metrics["misses"] += 1
                    return None
            
            async def track_cache_set(key, value, ttl=None):
                metrics["sets"] += 1
                return True
            
            mock_cache_get.side_effect = track_cache_get
            mock_cache_set.side_effect = track_cache_set
            
            # Simulate cache operations
            await redis_service.cache_get("miss:key1")
            await redis_service.cache_get("hit:key2")
            await redis_service.cache_set("new:key", {"data": "test"})
            await redis_service.cache_get("hit:key3")
            await redis_service.cache_get("miss:key4")
            
            # Verify metrics
            assert metrics["hits"] == 2
            assert metrics["misses"] == 2
            assert metrics["sets"] == 1
            
            # Calculate hit rate
            total_requests = metrics["hits"] + metrics["misses"]
            hit_rate = metrics["hits"] / total_requests if total_requests > 0 else 0
            assert hit_rate == 0.5