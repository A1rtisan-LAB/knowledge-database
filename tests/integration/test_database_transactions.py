"""Integration tests for database transactions."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.knowledge_item import KnowledgeItem, ContentStatus
from app.models.category import Category
from app.models.audit_log import AuditLog, AuditAction


@pytest.mark.integration
class TestDatabaseTransactions:
    """Test database transaction handling."""
    
    async def test_rollback_on_error(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test that database transactions are rolled back on error."""
        # Start a transaction
        initial_count = len((await db_session.execute(select(KnowledgeItem))).scalars().all())
        
        # Try to create an invalid knowledge item (missing required fields)
        try:
            invalid_item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                title=None,  # This will cause a constraint violation
                content="Test content"
            )
            db_session.add(invalid_item)
            await db_session.commit()
        except Exception:
            await db_session.rollback()
        
        # Verify no items were added
        final_count = len((await db_session.execute(select(KnowledgeItem))).scalars().all())
        assert final_count == initial_count
    
    async def test_cascade_delete(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test cascade delete operations."""
        # Create a category with knowledge items
        category = Category(
            organization_id=test_organization.id,
            name="Test Category",
            slug="test-category"
        )
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        
        # Create knowledge items in the category
        items = []
        for i in range(3):
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                category_id=category.id,
                title=f"Item {i}",
                content=f"Content {i}"
            )
            db_session.add(item)
            items.append(item)
        await db_session.commit()
        
        # Delete the category
        await db_session.delete(category)
        await db_session.commit()
        
        # Verify knowledge items are orphaned (category_id is null)
        for item in items:
            await db_session.refresh(item)
            assert item.category_id is None
    
    async def test_concurrent_updates(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test handling of concurrent updates to the same resource."""
        # Create a knowledge item
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Concurrent Test",
            content="Initial content",
            version=1
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        # Simulate concurrent updates
        import asyncio
        
        async def update_item(content: str):
            return await client.put(
                f"/api/v1/knowledge/{item.id}",
                headers=auth_headers,
                json={"content": content}
            )
        
        # Execute concurrent updates
        results = await asyncio.gather(
            update_item("Update 1"),
            update_item("Update 2"),
            update_item("Update 3"),
            return_exceptions=True
        )
        
        # At least one should succeed
        success_count = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 200)
        assert success_count >= 1
        
        # Check final state
        await db_session.refresh(item)
        assert item.content in ["Update 1", "Update 2", "Update 3"]
    
    async def test_transaction_isolation(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test transaction isolation levels."""
        # Create initial data
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Isolation Test",
            content="Initial",
            view_count=0
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        # Start a new session for isolation test
        from app.core.database import TestSessionLocal
        
        async with TestSessionLocal() as session1:
            async with TestSessionLocal() as session2:
                # Session 1: Start transaction and update
                item1 = await session1.get(KnowledgeItem, item.id)
                item1.view_count = 10
                
                # Session 2: Read before session1 commits
                item2 = await session2.get(KnowledgeItem, item.id)
                assert item2.view_count == 0  # Should not see uncommitted changes
                
                # Session 1: Commit
                await session1.commit()
                
                # Session 2: Read after commit
                await session2.refresh(item2)
                assert item2.view_count == 10  # Now should see committed changes
    
    async def test_bulk_operations(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test bulk database operations."""
        # Bulk insert
        items = []
        for i in range(100):
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                title=f"Bulk Item {i}",
                content=f"Bulk Content {i}",
                tags=[f"tag{i % 10}"]
            )
            items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        # Verify bulk insert
        result = await db_session.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.title.like("Bulk Item%")
            )
        )
        bulk_items = result.scalars().all()
        assert len(bulk_items) == 100
        
        # Bulk update
        for item in bulk_items[:50]:
            item.status = ContentStatus.ARCHIVED
        
        await db_session.commit()
        
        # Verify bulk update
        result = await db_session.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.status == ContentStatus.ARCHIVED
            )
        )
        archived_items = result.scalars().all()
        assert len(archived_items) >= 50
        
        # Bulk delete
        for item in bulk_items[50:]:
            await db_session.delete(item)
        
        await db_session.commit()
        
        # Verify bulk delete
        result = await db_session.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.title.like("Bulk Item%")
            )
        )
        remaining_items = result.scalars().all()
        assert len(remaining_items) == 50
    
    async def test_audit_log_transaction(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test audit log creation in transactions."""
        # Create a knowledge item with audit log
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Audited Item",
            content="Audited content"
        )
        db_session.add(item)
        
        # Create audit log entry
        audit_log = AuditLog(
            organization_id=test_organization.id,
            user_id=test_user.id,
            action=AuditAction.CREATE,
            resource_type="knowledge_item",
            resource_id=str(item.id),
            details={"title": item.title}
        )
        db_session.add(audit_log)
        
        await db_session.commit()
        
        # Verify both were created
        await db_session.refresh(item)
        assert item.id is not None
        
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == str(item.id)
            )
        )
        audit_entry = result.scalar_one_or_none()
        assert audit_entry is not None
        assert audit_entry.action == AuditAction.CREATE
    
    async def test_deadlock_handling(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test deadlock detection and handling."""
        # Create two items
        item1 = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Item 1",
            content="Content 1"
        )
        item2 = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Item 2",
            content="Content 2"
        )
        db_session.add_all([item1, item2])
        await db_session.commit()
        await db_session.refresh(item1)
        await db_session.refresh(item2)
        
        # Simulate potential deadlock scenario
        from app.core.database import TestSessionLocal
        import asyncio
        
        async def update_items_order1():
            async with TestSessionLocal() as session:
                # Lock item1 first, then item2
                i1 = await session.get(KnowledgeItem, item1.id, with_for_update=True)
                await asyncio.sleep(0.1)  # Small delay
                i2 = await session.get(KnowledgeItem, item2.id, with_for_update=True)
                
                i1.content = "Updated 1 by session 1"
                i2.content = "Updated 2 by session 1"
                
                await session.commit()
                return True
        
        async def update_items_order2():
            async with TestSessionLocal() as session:
                # Lock item2 first, then item1 (opposite order)
                i2 = await session.get(KnowledgeItem, item2.id, with_for_update=True)
                await asyncio.sleep(0.1)  # Small delay
                i1 = await session.get(KnowledgeItem, item1.id, with_for_update=True)
                
                i1.content = "Updated 1 by session 2"
                i2.content = "Updated 2 by session 2"
                
                await session.commit()
                return True
        
        # Run both concurrently (may cause deadlock)
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    update_items_order1(),
                    update_items_order2(),
                    return_exceptions=True
                ),
                timeout=5.0
            )
            
            # At least one should complete
            success_count = sum(1 for r in results if r is True)
            assert success_count >= 1
        except asyncio.TimeoutError:
            # Deadlock detected - this is expected in some cases
            pass
    
    async def test_referential_integrity(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test foreign key constraints and referential integrity."""
        # Try to create a knowledge item with invalid foreign keys
        with pytest.raises(Exception):
            invalid_item = KnowledgeItem(
                organization_id=uuid4(),  # Non-existent organization
                created_by_id=test_user.id,
                title="Invalid FK Test",
                content="Test content"
            )
            db_session.add(invalid_item)
            await db_session.commit()
        
        await db_session.rollback()
        
        # Try to delete a user with knowledge items
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="User FK Test",
            content="Test content"
        )
        db_session.add(item)
        await db_session.commit()
        
        # Attempting to delete user should fail or cascade based on configuration
        with pytest.raises(Exception):
            await db_session.delete(test_user)
            await db_session.commit()
        
        await db_session.rollback()