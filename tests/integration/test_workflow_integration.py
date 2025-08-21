"""Comprehensive workflow integration tests."""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from typing import List, Dict, Any

from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.knowledge_item import KnowledgeItem, ContentStatus
from app.models.category import Category
from app.models.feedback import Feedback
from app.models.audit_log import AuditLog, AuditAction


@pytest.mark.integration
class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""
    
    async def test_knowledge_management_workflow(self, client: AsyncClient, db_session: AsyncSession):
        """Test complete knowledge management workflow from creation to archival."""
        # Step 1: Organization setup
        org = Organization(
            name="Knowledge Corp",
            slug="knowledge-corp",
            description="Test organization for knowledge management"
        )
        db_session.add(org)
        await db_session.commit()
        
        # Step 2: User registration and team setup
        users_data = [
            ("admin@corp.com", "admin", UserRole.ADMIN),
            ("editor1@corp.com", "editor1", UserRole.EDITOR),
            ("editor2@corp.com", "editor2", UserRole.EDITOR),
            ("viewer@corp.com", "viewer", UserRole.VIEWER)
        ]
        
        users = []
        for email, username, role in users_data:
            user = User(
                organization_id=org.id,
                email=email,
                username=username,
                full_name=f"{username.title()} User",
                hashed_password="$2b$12$test",
                role=role,
                is_active=True,
                is_verified=True
            )
            users.append(user)
        
        db_session.add_all(users)
        await db_session.commit()
        
        # Step 3: Create category structure
        categories = []
        category_names = ["Engineering", "Product", "Marketing", "Operations"]
        
        for name in category_names:
            category = Category(
                organization_id=org.id,
                name=name,
                slug=name.lower(),
                description=f"{name} knowledge base"
            )
            categories.append(category)
        
        db_session.add_all(categories)
        await db_session.commit()
        
        # Step 4: Create knowledge items with collaboration
        with patch('app.auth.security.verify_password') as mock_verify:
            mock_verify.return_value = True
            
            # Editor 1 creates draft
            editor1_login = await client.post(
                "/api/v1/auth/login",
                json={"email": users[1].email, "password": "password"}
            )
            editor1_headers = {"Authorization": f"Bearer {editor1_login.json()['access_token']}"}
            
            draft_response = await client.post(
                "/api/v1/knowledge",
                headers=editor1_headers,
                json={
                    "title": "API Design Guidelines",
                    "content": "Initial draft of API design guidelines",
                    "category_id": str(categories[0].id),
                    "tags": ["api", "guidelines", "engineering"],
                    "status": "draft"
                }
            )
            
            if draft_response.status_code == 201:
                draft_item = draft_response.json()
                
                # Editor 2 reviews and updates
                editor2_login = await client.post(
                    "/api/v1/auth/login",
                    json={"email": users[2].email, "password": "password"}
                )
                editor2_headers = {"Authorization": f"Bearer {editor2_login.json()['access_token']}"}
                
                review_response = await client.put(
                    f"/api/v1/knowledge/{draft_item['id']}",
                    headers=editor2_headers,
                    json={
                        "content": "Updated API design guidelines with review comments",
                        "status": "under_review"
                    }
                )
                
                # Admin approves and publishes
                admin_login = await client.post(
                    "/api/v1/auth/login",
                    json={"email": users[0].email, "password": "password"}
                )
                admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
                
                publish_response = await client.put(
                    f"/api/v1/knowledge/{draft_item['id']}",
                    headers=admin_headers,
                    json={
                        "status": "published",
                        "published_at": datetime.utcnow().isoformat()
                    }
                )
                
                assert publish_response.status_code == 200
        
        # Step 5: Track usage and feedback
        # Viewer accesses the content
        with patch('app.auth.security.verify_password') as mock_verify:
            mock_verify.return_value = True
            
            viewer_login = await client.post(
                "/api/v1/auth/login",
                json={"email": users[3].email, "password": "password"}
            )
            viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}
            
            # View knowledge item
            view_response = await client.get(
                f"/api/v1/knowledge/{draft_item['id']}",
                headers=viewer_headers
            )
            assert view_response.status_code == 200
            
            # Provide feedback
            feedback_response = await client.post(
                f"/api/v1/knowledge/{draft_item['id']}/feedback",
                headers=viewer_headers,
                json={
                    "type": "helpful",
                    "comment": "Very useful guidelines!"
                }
            )
        
        # Step 6: Analytics and reporting
        analytics_response = await client.get(
            "/api/v1/analytics/knowledge",
            headers=admin_headers,
            params={"period": "month"}
        )
        
        # Step 7: Archive old content
        archive_response = await client.put(
            f"/api/v1/knowledge/{draft_item['id']}",
            headers=admin_headers,
            json={"status": "archived"}
        )
    
    async def test_search_and_discovery_workflow(self, client: AsyncClient, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test complete search and discovery workflow."""
        # Step 1: Create diverse content
        categories = []
        for cat in ["Technical", "Business", "Process"]:
            category = Category(
                organization_id=test_organization.id,
                name=cat,
                slug=cat.lower()
            )
            categories.append(category)
        
        db_session.add_all(categories)
        await db_session.commit()
        
        # Create knowledge items with rich metadata
        items_data = [
            ("Python Best Practices", "Technical guide for Python development", categories[0], ["python", "development", "best-practices"]),
            ("Project Management Guide", "How to manage projects effectively", categories[1], ["management", "projects", "planning"]),
            ("Code Review Process", "Our code review workflow", categories[2], ["process", "review", "development"]),
            ("Python Testing Guide", "Testing strategies for Python", categories[0], ["python", "testing", "quality"]),
            ("Business Strategy 2024", "Our business strategy for 2024", categories[1], ["strategy", "business", "planning"])
        ]
        
        items = []
        for title, content, category, tags in items_data:
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                category_id=category.id,
                title=title,
                content=content,
                tags=tags,
                status=ContentStatus.PUBLISHED
            )
            items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        # Step 2: User searches for content
        with patch('app.auth.security.verify_password') as mock_verify:
            mock_verify.return_value = True
            
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"email": test_user.email, "password": "password"}
            )
            headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
            
            # Search for Python content
            search_response = await client.get(
                "/api/v1/search",
                params={"query": "Python", "limit": 10},
                headers=headers
            )
            
            # Filter by category
            filtered_response = await client.get(
                "/api/v1/knowledge",
                params={"category_id": str(categories[0].id)},
                headers=headers
            )
            
            # Get recommendations based on viewing history
            for item in items[:2]:
                await client.get(f"/api/v1/knowledge/{item.id}", headers=headers)
            
            recommendations_response = await client.get(
                "/api/v1/knowledge/recommendations",
                headers=headers
            )
            
            # Track search analytics
            from app.models.search_query import SearchQuery
            
            search_query = SearchQuery(
                organization_id=test_organization.id,
                user_id=test_user.id,
                query_text="Python",
                result_count=2,
                selected_result_id=items[0].id,
                language="en"
            )
            db_session.add(search_query)
            await db_session.commit()
    
    async def test_content_lifecycle_workflow(self, client: AsyncClient, db_session: AsyncSession, test_organization: Organization):
        """Test complete content lifecycle from creation to deprecation."""
        # Step 1: Create author and reviewer
        author = User(
            organization_id=test_organization.id,
            email="author@test.com",
            username="author",
            full_name="Content Author",
            hashed_password="$2b$12$test",
            role=UserRole.EDITOR,
            is_active=True
        )
        
        reviewer = User(
            organization_id=test_organization.id,
            email="reviewer@test.com",
            username="reviewer",
            full_name="Content Reviewer",
            hashed_password="$2b$12$test",
            role=UserRole.ADMIN,
            is_active=True
        )
        
        db_session.add_all([author, reviewer])
        await db_session.commit()
        
        with patch('app.auth.security.verify_password') as mock_verify:
            mock_verify.return_value = True
            
            # Step 2: Author creates draft
            author_login = await client.post(
                "/api/v1/auth/login",
                json={"email": author.email, "password": "password"}
            )
            author_headers = {"Authorization": f"Bearer {author_login.json()['access_token']}"}
            
            draft_response = await client.post(
                "/api/v1/knowledge",
                headers=author_headers,
                json={
                    "title": "New Feature Documentation",
                    "content": "Documentation for new feature",
                    "status": "draft",
                    "tags": ["feature", "documentation"]
                }
            )
            
            if draft_response.status_code == 201:
                item_id = draft_response.json()["id"]
                
                # Step 3: Submit for review
                submit_response = await client.put(
                    f"/api/v1/knowledge/{item_id}",
                    headers=author_headers,
                    json={"status": "under_review"}
                )
                
                # Step 4: Reviewer reviews and requests changes
                reviewer_login = await client.post(
                    "/api/v1/auth/login",
                    json={"email": reviewer.email, "password": "password"}
                )
                reviewer_headers = {"Authorization": f"Bearer {reviewer_login.json()['access_token']}"}
                
                review_feedback = await client.post(
                    f"/api/v1/knowledge/{item_id}/feedback",
                    headers=reviewer_headers,
                    json={
                        "type": "needs_improvement",
                        "comment": "Please add more examples"
                    }
                )
                
                # Step 5: Author updates based on feedback
                update_response = await client.put(
                    f"/api/v1/knowledge/{item_id}",
                    headers=author_headers,
                    json={
                        "content": "Updated documentation with examples",
                        "status": "under_review"
                    }
                )
                
                # Step 6: Reviewer approves and publishes
                publish_response = await client.put(
                    f"/api/v1/knowledge/{item_id}",
                    headers=reviewer_headers,
                    json={
                        "status": "published",
                        "published_at": datetime.utcnow().isoformat()
                    }
                )
                
                # Step 7: Track metrics over time
                await asyncio.sleep(0.1)  # Simulate time passing
                
                # Update view count
                for _ in range(10):
                    await client.get(f"/api/v1/knowledge/{item_id}", headers=author_headers)
                
                # Step 8: Eventually deprecate
                deprecate_response = await client.put(
                    f"/api/v1/knowledge/{item_id}",
                    headers=reviewer_headers,
                    json={
                        "status": "deprecated",
                        "deprecated_reason": "Replaced by newer documentation"
                    }
                )
    
    async def test_analytics_and_reporting_workflow(self, client: AsyncClient, db_session: AsyncSession, test_organization: Organization):
        """Test analytics collection and reporting workflow."""
        # Step 1: Create users and content
        users = []
        for i in range(5):
            user = User(
                organization_id=test_organization.id,
                email=f"user{i}@test.com",
                username=f"user{i}",
                full_name=f"User {i}",
                hashed_password="$2b$12$test",
                role=UserRole.EDITOR,
                is_active=True
            )
            users.append(user)
        
        db_session.add_all(users)
        await db_session.commit()
        
        # Create knowledge items
        items = []
        for i in range(10):
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=users[i % 5].id,
                title=f"Knowledge Item {i}",
                content=f"Content {i}",
                tags=[f"tag{i % 3}"],
                status=ContentStatus.PUBLISHED,
                view_count=i * 10,
                created_at=datetime.utcnow() - timedelta(days=30-i)
            )
            items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        # Step 2: Simulate user interactions
        with patch('app.auth.security.verify_password') as mock_verify:
            mock_verify.return_value = True
            
            for user in users[:3]:
                login = await client.post(
                    "/api/v1/auth/login",
                    json={"email": user.email, "password": "password"}
                )
                headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
                
                # View items
                for item in items[:5]:
                    await client.get(f"/api/v1/knowledge/{item.id}", headers=headers)
                
                # Add feedback
                feedback = Feedback(
                    organization_id=test_organization.id,
                    user_id=user.id,
                    knowledge_item_id=items[0].id,
                    type=FeedbackType.HELPFUL,
                    comment="Great content!"
                )
                db_session.add(feedback)
            
            await db_session.commit()
            
            # Step 3: Generate analytics reports
            admin_login = await client.post(
                "/api/v1/auth/login",
                json={"email": users[0].email, "password": "password"}
            )
            admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
            
            # Get usage analytics
            usage_analytics = await client.get(
                "/api/v1/analytics/usage",
                params={"period": "month"},
                headers=admin_headers
            )
            
            # Get content analytics
            content_analytics = await client.get(
                "/api/v1/analytics/content",
                params={"period": "month"},
                headers=admin_headers
            )
            
            # Get user analytics
            user_analytics = await client.get(
                "/api/v1/analytics/users",
                params={"period": "month"},
                headers=admin_headers
            )
            
            # Step 4: Export reports
            export_response = await client.post(
                "/api/v1/analytics/export",
                headers=admin_headers,
                json={
                    "format": "csv",
                    "report_type": "comprehensive",
                    "period": "month"
                }
            )
    
    async def test_disaster_recovery_workflow(self, client: AsyncClient, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test disaster recovery and data integrity workflow."""
        # Step 1: Create critical data
        critical_items = []
        for i in range(5):
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                title=f"Critical Document {i}",
                content=f"Critical content {i}",
                tags=["critical", "backup"],
                status=ContentStatus.PUBLISHED
            )
            critical_items.append(item)
        
        db_session.add_all(critical_items)
        await db_session.commit()
        
        # Step 2: Create backup
        backup_data = []
        for item in critical_items:
            backup_data.append({
                "id": str(item.id),
                "title": item.title,
                "content": item.content,
                "tags": item.tags,
                "created_at": item.created_at.isoformat()
            })
        
        # Step 3: Simulate data corruption
        corrupted_item = critical_items[0]
        corrupted_item.content = "CORRUPTED"
        await db_session.commit()
        
        # Step 4: Detect corruption through audit logs
        audit_log = AuditLog(
            organization_id=test_organization.id,
            user_id=test_user.id,
            action=AuditAction.UPDATE,
            resource_type="knowledge_item",
            resource_id=str(corrupted_item.id),
            details={"change": "content_corrupted"}
        )
        db_session.add(audit_log)
        await db_session.commit()
        
        # Step 5: Restore from backup
        for backup_item in backup_data:
            if backup_item["id"] == str(corrupted_item.id):
                corrupted_item.content = backup_item["content"]
                await db_session.commit()
                
                # Log restoration
                restore_log = AuditLog(
                    organization_id=test_organization.id,
                    user_id=test_user.id,
                    action=AuditAction.UPDATE,
                    resource_type="knowledge_item",
                    resource_id=str(corrupted_item.id),
                    details={"action": "restored_from_backup"}
                )
                db_session.add(restore_log)
                await db_session.commit()
        
        # Step 6: Verify data integrity
        await db_session.refresh(corrupted_item)
        assert corrupted_item.content == "Critical content 0"
        
        # Step 7: Run integrity checks
        from sqlalchemy import select, func
        
        # Check for orphaned records
        orphan_check = await db_session.execute(
            select(func.count(KnowledgeItem.id))
            .where(KnowledgeItem.organization_id == test_organization.id)
        )
        total_items = orphan_check.scalar()
        assert total_items == len(critical_items)
        
        # Verify audit trail
        audit_check = await db_session.execute(
            select(AuditLog)
            .where(AuditLog.resource_id == str(corrupted_item.id))
            .order_by(AuditLog.created_at.desc())
        )
        audit_entries = audit_check.scalars().all()
        assert len(audit_entries) >= 2  # Corruption and restoration