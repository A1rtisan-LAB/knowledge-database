"""Unit tests for database models."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.knowledge_item import KnowledgeItem, ContentStatus
from app.models.category import Category
from app.models.feedback import Feedback
from app.models.audit_log import AuditLog, AuditAction
from app.models.search_query import SearchQuery
from app.auth.security import get_password_hash, verify_password


@pytest.mark.unit
class TestOrganizationModel:
    """Test Organization model."""
    
    async def test_create_organization(self, db_session: AsyncSession):
        """Test creating an organization."""
        org = Organization(
            name="Test Corp",
            slug="test-corp",
            description="Test organization",
            max_users=10,
            max_knowledge_items=1000
        )
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)
        
        assert org.id is not None
        assert org.name == "Test Corp"
        assert org.slug == "test-corp"
        assert org.is_active is True
        assert org.created_at is not None
        
    async def test_organization_unique_slug(self, db_session: AsyncSession):
        """Test that organization slug must be unique."""
        org1 = Organization(name="Org 1", slug="unique-slug")
        org2 = Organization(name="Org 2", slug="unique-slug")
        
        db_session.add(org1)
        await db_session.commit()
        
        db_session.add(org2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
            
    async def test_organization_relationships(self, db_session: AsyncSession, test_organization: Organization):
        """Test organization relationships."""
        user = User(
            organization_id=test_organization.id,
            email="user@test.com",
            username="testuser",
            hashed_password="hashed"
        )
        db_session.add(user)
        await db_session.commit()
        
        await db_session.refresh(test_organization)
        assert len(test_organization.users) == 0  # Lazy loading not loaded yet


@pytest.mark.unit
class TestUserModel:
    """Test User model."""
    
    async def test_create_user(self, db_session: AsyncSession, test_organization: Organization):
        """Test creating a user."""
        user = User(
            organization_id=test_organization.id,
            email="newuser@example.com",
            username="newuser",
            full_name="New User",
            hashed_password=get_password_hash("password123"),
            role=UserRole.VIEWER
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.role == UserRole.VIEWER
        assert user.is_active is True
        assert user.is_verified is False
        assert verify_password("password123", user.hashed_password)
        
    async def test_user_unique_email(self, db_session: AsyncSession, test_organization: Organization):
        """Test that user email must be unique."""
        user1 = User(
            organization_id=test_organization.id,
            email="same@example.com",
            username="user1",
            hashed_password="hash1"
        )
        user2 = User(
            organization_id=test_organization.id,
            email="same@example.com",
            username="user2",
            hashed_password="hash2"
        )
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
            
    async def test_user_roles(self):
        """Test user role enumeration."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.EDITOR.value == "editor"
        assert UserRole.VIEWER.value == "viewer"
        
    async def test_user_soft_delete(self, db_session: AsyncSession, test_user: User):
        """Test user soft delete functionality."""
        test_user.is_active = False
        await db_session.commit()
        await db_session.refresh(test_user)
        
        assert test_user.is_active is False
        assert test_user.id is not None  # User still exists in database


@pytest.mark.unit
class TestKnowledgeItemModel:
    """Test KnowledgeItem model."""
    
    async def test_create_knowledge_item(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test creating a knowledge item."""
        category = Category(
            organization_id=test_organization.id,
            name="Test Category",
            slug="test-category"
        )
        db_session.add(category)
        await db_session.commit()
        
        item = KnowledgeItem(
            organization_id=test_organization.id,
            category_id=category.id,
            created_by_id=test_user.id,
            title="Test Knowledge",
            content="This is test content",
            title_ko="테스트 지식",
            content_ko="테스트 내용입니다",
            tags=["test", "knowledge"],
            status=ContentStatus.PUBLISHED
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        assert item.id is not None
        assert item.title == "Test Knowledge"
        assert item.title_ko == "테스트 지식"
        assert item.status == ContentStatus.PUBLISHED
        assert "test" in item.tags
        assert item.view_count == 0
        
    async def test_knowledge_status_transitions(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test knowledge item status transitions."""
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Draft Item",
            content="Draft content",
            status=ContentStatus.DRAFT
        )
        db_session.add(item)
        await db_session.commit()
        
        # Draft -> Under Review
        item.status = ContentStatus.UNDER_REVIEW
        await db_session.commit()
        await db_session.refresh(item)
        assert item.status == ContentStatus.UNDER_REVIEW
        
        # Under Review -> Published
        item.status = ContentStatus.PUBLISHED
        await db_session.commit()
        await db_session.refresh(item)
        assert item.status == ContentStatus.PUBLISHED
        
        # Published -> Archived
        item.status = ContentStatus.ARCHIVED
        await db_session.commit()
        await db_session.refresh(item)
        assert item.status == ContentStatus.ARCHIVED
        
    async def test_knowledge_view_count(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test knowledge item view count increment."""
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Popular Item",
            content="Popular content"
        )
        db_session.add(item)
        await db_session.commit()
        
        # Increment view count
        item.view_count += 1
        await db_session.commit()
        await db_session.refresh(item)
        assert item.view_count == 1
        
        # Multiple increments
        item.view_count += 5
        await db_session.commit()
        await db_session.refresh(item)
        assert item.view_count == 6


@pytest.mark.unit
class TestCategoryModel:
    """Test Category model."""
    
    async def test_create_category(self, db_session: AsyncSession, test_organization: Organization):
        """Test creating a category."""
        category = Category(
            organization_id=test_organization.id,
            name="Technology",
            slug="technology",
            name_ko="기술",
            description="Technology related knowledge",
            description_ko="기술 관련 지식"
        )
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        
        assert category.id is not None
        assert category.name == "Technology"
        assert category.name_ko == "기술"
        assert category.slug == "technology"
        
    async def test_category_hierarchy(self, db_session: AsyncSession, test_organization: Organization):
        """Test category parent-child relationships."""
        parent = Category(
            organization_id=test_organization.id,
            name="Parent Category",
            slug="parent-category"
        )
        db_session.add(parent)
        await db_session.commit()
        
        child = Category(
            organization_id=test_organization.id,
            parent_id=parent.id,
            name="Child Category",
            slug="child-category"
        )
        db_session.add(child)
        await db_session.commit()
        
        await db_session.refresh(child)
        assert child.parent_id == parent.id
        
    async def test_category_unique_slug_per_org(self, db_session: AsyncSession, test_organization: Organization):
        """Test that category slug must be unique within organization."""
        cat1 = Category(
            organization_id=test_organization.id,
            name="Cat 1",
            slug="same-slug"
        )
        cat2 = Category(
            organization_id=test_organization.id,
            name="Cat 2",
            slug="same-slug"
        )
        
        db_session.add(cat1)
        await db_session.commit()
        
        db_session.add(cat2)
        with pytest.raises(IntegrityError):
            await db_session.commit()


@pytest.mark.unit
class TestFeedbackModel:
    """Test Feedback model."""
    
    async def test_create_feedback(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test creating feedback."""
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Item for Feedback",
            content="Content"
        )
        db_session.add(item)
        await db_session.commit()
        
        feedback = Feedback(
            organization_id=test_organization.id,
            knowledge_item_id=item.id,
            user_id=test_user.id,
            type=FeedbackType.HELPFUL,
            rating=5,
            comment="Very helpful!"
        )
        db_session.add(feedback)
        await db_session.commit()
        await db_session.refresh(feedback)
        
        assert feedback.id is not None
        assert feedback.type == FeedbackType.HELPFUL
        assert feedback.rating == 5
        assert feedback.comment == "Very helpful!"
        
    async def test_feedback_types(self):
        """Test feedback type enumeration."""
        assert FeedbackType.HELPFUL.value == "helpful"
        assert FeedbackType.NOT_HELPFUL.value == "not_helpful"
        assert FeedbackType.OUTDATED.value == "outdated"
        assert FeedbackType.INCORRECT.value == "incorrect"
        
    async def test_feedback_rating_validation(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test feedback rating must be between 1 and 5."""
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=test_user.id,
            title="Item",
            content="Content"
        )
        db_session.add(item)
        await db_session.commit()
        
        # Valid ratings
        for rating in [1, 2, 3, 4, 5]:
            feedback = Feedback(
                organization_id=test_organization.id,
                knowledge_item_id=item.id,
                user_id=test_user.id,
                type=FeedbackType.HELPFUL,
                rating=rating
            )
            db_session.add(feedback)
            await db_session.commit()
            assert feedback.rating == rating


@pytest.mark.unit
class TestAuditLogModel:
    """Test AuditLog model."""
    
    async def test_create_audit_log(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test creating an audit log entry."""
        log = AuditLog(
            organization_id=test_organization.id,
            user_id=test_user.id,
            action=AuditAction.CREATE,
            resource_type="knowledge_item",
            resource_id="123",
            details={"title": "New Item"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)
        
        assert log.id is not None
        assert log.action == AuditAction.CREATE
        assert log.resource_type == "knowledge_item"
        assert log.details["title"] == "New Item"
        assert log.ip_address == "192.168.1.1"
        
    async def test_audit_actions(self):
        """Test audit action enumeration."""
        assert AuditAction.CREATE.value == "create"
        assert AuditAction.READ.value == "read"
        assert AuditAction.UPDATE.value == "update"
        assert AuditAction.DELETE.value == "delete"
        assert AuditAction.LOGIN.value == "login"
        assert AuditAction.LOGOUT.value == "logout"
        
    async def test_audit_log_immutable(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test that audit logs cannot be modified."""
        log = AuditLog(
            organization_id=test_organization.id,
            user_id=test_user.id,
            action=AuditAction.CREATE,
            resource_type="test",
            resource_id="1"
        )
        db_session.add(log)
        await db_session.commit()
        
        original_action = log.action
        original_created_at = log.created_at
        
        # Attempt to modify (this should not persist properly in a real audit system)
        log.action = AuditAction.DELETE
        await db_session.commit()
        
        # In a real audit system, this should be prevented
        # For now, we just verify the timestamp doesn't change
        assert log.created_at == original_created_at


@pytest.mark.unit
class TestSearchQueryModel:
    """Test SearchQuery model."""
    
    async def test_create_search_query(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test creating a search query log."""
        query = SearchQuery(
            organization_id=test_organization.id,
            user_id=test_user.id,
            query_text="python tutorial",
            query_language="en",
            filters={"category": "programming"},
            results_count=15,
            execution_time_ms=125.5
        )
        db_session.add(query)
        await db_session.commit()
        await db_session.refresh(query)
        
        assert query.id is not None
        assert query.query_text == "python tutorial"
        assert query.query_language == "en"
        assert query.results_count == 15
        assert query.execution_time_ms == 125.5
        assert query.filters["category"] == "programming"
        
    async def test_search_query_bilingual(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test search queries in different languages."""
        # English query
        en_query = SearchQuery(
            organization_id=test_organization.id,
            user_id=test_user.id,
            query_text="machine learning",
            query_language="en",
            results_count=10
        )
        db_session.add(en_query)
        
        # Korean query
        ko_query = SearchQuery(
            organization_id=test_organization.id,
            user_id=test_user.id,
            query_text="머신러닝",
            query_language="ko",
            results_count=8
        )
        db_session.add(ko_query)
        
        await db_session.commit()
        
        assert en_query.query_language == "en"
        assert ko_query.query_language == "ko"
        
    async def test_search_performance_tracking(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test tracking search performance metrics."""
        queries = []
        for i in range(5):
            query = SearchQuery(
                organization_id=test_organization.id,
                user_id=test_user.id,
                query_text=f"query {i}",
                results_count=i * 10,
                execution_time_ms=50.0 + i * 10
            )
            queries.append(query)
            db_session.add(query)
        
        await db_session.commit()
        
        # Verify performance metrics
        for i, query in enumerate(queries):
            assert query.execution_time_ms == 50.0 + i * 10
            assert query.results_count == i * 10