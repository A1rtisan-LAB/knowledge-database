"""
SQLite-based test configuration for environments without Docker.
This provides an alternative testing setup using SQLite in-memory database
and mock services for OpenSearch and Redis.
"""

import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.organization import Organization
from app.core.config import settings

# Override settings for SQLite testing
settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
settings.TESTING = True
settings.ENVIRONMENT = "test"

# Create async engine for SQLite
async_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Sync engine for initial setup (if needed)
sync_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each test."""
    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
    
    # Drop tables after test
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def override_get_db(db_session: AsyncSession):
    """Override the database dependency."""
    async def _override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(override_get_db) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest_asyncio.fixture(scope="function")
async def test_organization(db_session: AsyncSession) -> Organization:
    """Create a test organization."""
    org = Organization(
        name="Test Organization",
        description="Organization for testing",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession, test_organization: Organization) -> User:
    """Create a test user."""
    from app.auth.security import get_password_hash
    
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=get_password_hash("testpass123"),
        is_active=True,
        is_superuser=False,
        organization_id=test_organization.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session: AsyncSession, test_organization: Organization) -> User:
    """Create an admin user."""
    from app.auth.security import get_password_hash
    
    user = User(
        email="admin@example.com",
        username="adminuser",
        password_hash=get_password_hash("adminpass123"),
        is_active=True,
        is_superuser=True,
        organization_id=test_organization.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(client: TestClient, test_user: User) -> dict:
    """Get authentication headers for test user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def admin_headers(client: TestClient, admin_user: User) -> dict:
    """Get authentication headers for admin user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "adminuser", "password": "adminpass123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Mock OpenSearch
class MockOpenSearchClient:
    """Mock OpenSearch client for testing."""
    
    def __init__(self):
        self.indices = MagicMock()
        self.indices.exists = MagicMock(return_value=True)
        self.indices.create = MagicMock(return_value={"acknowledged": True})
        self.indices.delete = MagicMock(return_value={"acknowledged": True})
        self.indices.put_mapping = MagicMock(return_value={"acknowledged": True})
        
        self._documents = {}
    
    def index(self, index, body, id=None):
        """Mock index operation."""
        if id is None:
            import uuid
            id = str(uuid.uuid4())
        
        if index not in self._documents:
            self._documents[index] = {}
        
        self._documents[index][id] = body
        return {"_id": id, "_index": index, "result": "created"}
    
    def search(self, index, body):
        """Mock search operation."""
        if index not in self._documents:
            return {"hits": {"total": {"value": 0}, "hits": []}}
        
        # Simple mock search - return all documents
        hits = [
            {
                "_id": doc_id,
                "_source": doc,
                "_score": 1.0
            }
            for doc_id, doc in self._documents.get(index, {}).items()
        ]
        
        return {
            "hits": {
                "total": {"value": len(hits)},
                "hits": hits
            }
        }
    
    def delete(self, index, id):
        """Mock delete operation."""
        if index in self._documents and id in self._documents[index]:
            del self._documents[index][id]
            return {"result": "deleted"}
        return {"result": "not_found"}
    
    def ping(self):
        """Mock ping operation."""
        return True


@pytest.fixture(scope="function")
def mock_opensearch():
    """Mock OpenSearch for testing."""
    with patch("app.services.opensearch.get_opensearch_client") as mock:
        mock.return_value = MockOpenSearchClient()
        yield mock.return_value


# Mock Redis
class MockRedisClient:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self._data = {}
        self._expiry = {}
    
    async def get(self, key):
        """Mock get operation."""
        return self._data.get(key)
    
    async def set(self, key, value, ex=None):
        """Mock set operation."""
        self._data[key] = value
        if ex:
            self._expiry[key] = ex
        return True
    
    async def delete(self, key):
        """Mock delete operation."""
        if key in self._data:
            del self._data[key]
            if key in self._expiry:
                del self._expiry[key]
            return 1
        return 0
    
    async def exists(self, key):
        """Mock exists operation."""
        return key in self._data
    
    async def expire(self, key, seconds):
        """Mock expire operation."""
        if key in self._data:
            self._expiry[key] = seconds
            return True
        return False
    
    async def ttl(self, key):
        """Mock TTL operation."""
        return self._expiry.get(key, -1)
    
    async def incr(self, key):
        """Mock increment operation."""
        if key not in self._data:
            self._data[key] = 0
        self._data[key] = int(self._data[key]) + 1
        return self._data[key]
    
    async def ping(self):
        """Mock ping operation."""
        return True
    
    async def close(self):
        """Mock close operation."""
        pass


@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis for testing."""
    with patch("app.services.redis.get_redis_client") as mock:
        mock.return_value = MockRedisClient()
        yield mock.return_value


# Mock embedding service
class MockEmbeddingService:
    """Mock embedding service for testing."""
    
    async def generate_embedding(self, text: str):
        """Generate a mock embedding."""
        # Return a simple mock embedding vector
        import hashlib
        hash_val = hashlib.md5(text.encode()).hexdigest()
        # Convert hash to a list of floats (mock 384-dimensional vector)
        embedding = [float(int(hash_val[i:i+2], 16)) / 255.0 for i in range(0, min(len(hash_val), 768), 2)]
        # Pad or truncate to 384 dimensions
        if len(embedding) < 384:
            embedding.extend([0.0] * (384 - len(embedding)))
        else:
            embedding = embedding[:384]
        return embedding
    
    async def generate_embeddings(self, texts: list):
        """Generate mock embeddings for multiple texts."""
        return [await self.generate_embedding(text) for text in texts]


@pytest.fixture(scope="function")
def mock_embedding_service():
    """Mock embedding service for testing."""
    with patch("app.services.embeddings.EmbeddingService") as mock:
        mock.return_value = MockEmbeddingService()
        yield mock.return_value


# Event loop fixture
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test data fixtures
@pytest.fixture
def sample_knowledge_item():
    """Sample knowledge item data."""
    return {
        "title": "Test Knowledge Item",
        "content": "This is a test knowledge item content.",
        "content_type": "text",
        "tags": ["test", "sample"],
        "metadata": {"key": "value"},
        "is_published": True
    }


@pytest.fixture
def sample_category():
    """Sample category data."""
    return {
        "name": "Test Category",
        "slug": "test-category",
        "description": "This is a test category"
    }


# Utility functions for testing
async def create_test_knowledge_items(db_session: AsyncSession, user: User, count: int = 5):
    """Create multiple test knowledge items."""
    from app.models.knowledge_item import KnowledgeItem
    
    items = []
    for i in range(count):
        item = KnowledgeItem(
            title=f"Test Item {i}",
            content=f"This is test content for item {i}",
            content_type="text",
            author_id=user.id,
            organization_id=user.organization_id,
            tags=[f"tag{i}", "test"],
            is_published=True
        )
        db_session.add(item)
        items.append(item)
    
    await db_session.commit()
    for item in items:
        await db_session.refresh(item)
    
    return items


async def create_test_categories(db_session: AsyncSession, organization: Organization, count: int = 3):
    """Create multiple test categories."""
    from app.models.category import Category
    
    categories = []
    for i in range(count):
        category = Category(
            name=f"Category {i}",
            slug=f"category-{i}",
            description=f"Description for category {i}",
            organization_id=organization.id
        )
        db_session.add(category)
        categories.append(category)
    
    await db_session.commit()
    for category in categories:
        await db_session.refresh(category)
    
    return categories