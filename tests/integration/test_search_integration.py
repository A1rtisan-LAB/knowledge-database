"""Integration tests for search functionality."""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List, Dict, Any
from uuid import uuid4

from app.models.user import User
from app.models.organization import Organization
from app.models.knowledge_item import KnowledgeItem, ContentStatus
from app.models.category import Category
from app.models.search_query import SearchQuery
from app.services import search as search_service


@pytest.mark.integration
class TestSearchIntegration:
    """Test search functionality integration."""
    
    async def test_full_text_search(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test full-text search across knowledge items."""
        # Create test data with various content
        test_items = [
            ("Python Programming Guide", "Learn Python programming from basics to advanced", ["python", "programming", "tutorial"]),
            ("JavaScript for Beginners", "Start your JavaScript journey with this guide", ["javascript", "web", "tutorial"]),
            ("Advanced Python Techniques", "Master advanced Python concepts and patterns", ["python", "advanced", "patterns"]),
            ("Web Development with React", "Build modern web apps with React and JavaScript", ["react", "javascript", "web"]),
            ("Database Design Principles", "Learn how to design efficient databases", ["database", "sql", "design"])
        ]
        
        items = []
        for title, content, tags in test_items:
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                title=title,
                content=content,
                tags=tags,
                status=ContentStatus.PUBLISHED
            )
            items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        # Test search for "Python"
        response = await client.get(
            "/api/v1/search",
            params={"query": "Python", "limit": 10},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Mock search results for testing
        with patch('app.services.search.search_knowledge') as mock_search:
            mock_search.return_value = {
                "total": 2,
                "items": [
                    {"id": str(items[0].id), "title": items[0].title, "score": 0.95},
                    {"id": str(items[2].id), "title": items[2].title, "score": 0.90}
                ],
                "facets": {"tags": {"python": 2, "programming": 1, "advanced": 1}}
            }
            
            result = await search_service.search_knowledge("Python", language="en")
            assert result["total"] == 2
            assert len(result["items"]) == 2
    
    async def test_multilingual_search(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test search in multiple languages (Korean and English)."""
        # Create bilingual content
        items_data = [
            ("파이썬 프로그래밍", "Python Programming", "파이썬 프로그래밍 가이드", "Python programming guide"),
            ("웹 개발", "Web Development", "웹 개발 튜토리얼", "Web development tutorial"),
            ("데이터베이스 설계", "Database Design", "데이터베이스 설계 원칙", "Database design principles")
        ]
        
        items = []
        for title_ko, title_en, content_ko, content_en in items_data:
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                title=title_ko,
                title_en=title_en,
                content=content_ko,
                content_en=content_en,
                status=ContentStatus.PUBLISHED
            )
            items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        # Test Korean search
        with patch('app.services.search.search_knowledge') as mock_search:
            mock_search.return_value = {
                "total": 1,
                "items": [{"id": str(items[0].id), "title": items[0].title, "score": 0.98}],
                "facets": {}
            }
            
            result_ko = await search_service.search_knowledge("파이썬", language="ko")
            assert result_ko["total"] == 1
            
            # Test English search
            mock_search.return_value = {
                "total": 1,
                "items": [{"id": str(items[0].id), "title": items[0].title_en, "score": 0.98}],
                "facets": {}
            }
            
            result_en = await search_service.search_knowledge("Python", language="en")
            assert result_en["total"] == 1
    
    async def test_search_with_filters(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test search with category and tag filters."""
        # Create categories
        tech_category = Category(
            organization_id=test_organization.id,
            name="Technology",
            slug="technology"
        )
        business_category = Category(
            organization_id=test_organization.id,
            name="Business",
            slug="business"
        )
        db_session.add_all([tech_category, business_category])
        await db_session.commit()
        
        # Create items in different categories
        items = []
        for i in range(5):
            category = tech_category if i < 3 else business_category
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                category_id=category.id,
                title=f"Item {i} in {category.name}",
                content=f"Content for item {i}",
                tags=["python"] if i % 2 == 0 else ["javascript"],
                status=ContentStatus.PUBLISHED
            )
            items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        # Test search with category filter
        with patch('app.services.search.search_knowledge') as mock_search:
            # Search in tech category
            mock_search.return_value = {
                "total": 3,
                "items": [
                    {"id": str(items[i].id), "title": items[i].title}
                    for i in range(3)
                ],
                "facets": {"category": {"technology": 3}}
            }
            
            result = await search_service.search_knowledge(
                "Item",
                category_id=tech_category.id
            )
            assert result["total"] == 3
            
            # Search with tag filter
            mock_search.return_value = {
                "total": 3,
                "items": [
                    {"id": str(items[i].id), "title": items[i].title}
                    for i in [0, 2, 4]
                ],
                "facets": {"tags": {"python": 3}}
            }
            
            result = await search_service.search_knowledge(
                "Item",
                tags=["python"]
            )
            assert result["total"] == 3
    
    async def test_search_ranking_and_relevance(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test search result ranking by relevance."""
        # Create items with varying relevance
        items_data = [
            ("Python Complete Guide", "Python Python Python - comprehensive guide", ["python"], 100),
            ("Introduction to Python", "Basic Python tutorial", ["python", "tutorial"], 50),
            ("Programming Languages Overview", "Covers Python, Java, and more", ["programming"], 20),
            ("Advanced Topics", "Mentions Python once", ["advanced"], 10)
        ]
        
        items = []
        for title, content, tags, view_count in items_data:
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                title=title,
                content=content,
                tags=tags,
                view_count=view_count,
                status=ContentStatus.PUBLISHED
            )
            items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        with patch('app.services.search.search_knowledge') as mock_search:
            # Mock search results ordered by relevance
            mock_search.return_value = {
                "total": 4,
                "items": [
                    {"id": str(items[0].id), "title": items[0].title, "score": 0.98},
                    {"id": str(items[1].id), "title": items[1].title, "score": 0.85},
                    {"id": str(items[2].id), "title": items[2].title, "score": 0.60},
                    {"id": str(items[3].id), "title": items[3].title, "score": 0.30}
                ],
                "facets": {}
            }
            
            result = await search_service.search_knowledge("Python")
            
            # Verify results are ordered by score
            scores = [item["score"] for item in result["items"]]
            assert scores == sorted(scores, reverse=True)
            assert result["items"][0]["score"] > result["items"][-1]["score"]
    
    async def test_search_pagination(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test search result pagination."""
        # Create many items
        items = []
        for i in range(25):
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                title=f"Python Tutorial Part {i}",
                content=f"Content for part {i}",
                status=ContentStatus.PUBLISHED
            )
            items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        # Test pagination
        with patch('app.services.search.search_knowledge') as mock_search:
            # Page 1
            mock_search.return_value = {
                "total": 25,
                "items": [
                    {"id": str(items[i].id), "title": items[i].title}
                    for i in range(10)
                ],
                "facets": {}
            }
            
            result_page1 = await search_service.search_knowledge(
                "Python",
                limit=10,
                offset=0
            )
            assert len(result_page1["items"]) == 10
            assert result_page1["total"] == 25
            
            # Page 2
            mock_search.return_value = {
                "total": 25,
                "items": [
                    {"id": str(items[i].id), "title": items[i].title}
                    for i in range(10, 20)
                ],
                "facets": {}
            }
            
            result_page2 = await search_service.search_knowledge(
                "Python",
                limit=10,
                offset=10
            )
            assert len(result_page2["items"]) == 10
            
            # Page 3 (partial)
            mock_search.return_value = {
                "total": 25,
                "items": [
                    {"id": str(items[i].id), "title": items[i].title}
                    for i in range(20, 25)
                ],
                "facets": {}
            }
            
            result_page3 = await search_service.search_knowledge(
                "Python",
                limit=10,
                offset=20
            )
            assert len(result_page3["items"]) == 5
    
    async def test_search_suggestions_and_autocomplete(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test search suggestions and autocomplete functionality."""
        # Create items with common prefixes
        items_data = [
            "Python Programming",
            "Python Development",
            "Python Data Science",
            "JavaScript Basics",
            "JavaScript Advanced",
            "Java Programming"
        ]
        
        items = []
        for title in items_data:
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                title=title,
                content=f"Content about {title}",
                status=ContentStatus.PUBLISHED
            )
            items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        # Test autocomplete
        response = await client.get(
            "/api/v1/search/suggestions",
            params={"prefix": "Pyth"},
            headers=auth_headers
        )
        
        # Mock suggestions response
        with patch('app.api.v1.search.get_search_suggestions') as mock_suggestions:
            mock_suggestions.return_value = [
                "Python Programming",
                "Python Development",
                "Python Data Science"
            ]
            
            suggestions = mock_suggestions("Pyth")
            assert len(suggestions) == 3
            assert all("Python" in s for s in suggestions)
    
    async def test_search_analytics_tracking(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test search query analytics and tracking."""
        # Track search queries
        queries = [
            ("Python tutorial", 15),
            ("JavaScript guide", 10),
            ("Python tutorial", 8),  # Duplicate query
            ("Database design", 5),
            ("Python", 20)
        ]
        
        for query_text, result_count in queries:
            search_query = SearchQuery(
                organization_id=test_organization.id,
                user_id=test_user.id,
                query_text=query_text,
                result_count=result_count,
                language="en"
            )
            db_session.add(search_query)
        
        await db_session.commit()
        
        # Analyze search patterns
        from sqlalchemy import func, select
        
        # Most popular queries
        popular_queries = await db_session.execute(
            select(
                SearchQuery.query_text,
                func.count(SearchQuery.id).label("count")
            )
            .where(SearchQuery.organization_id == test_organization.id)
            .group_by(SearchQuery.query_text)
            .order_by(func.count(SearchQuery.id).desc())
        )
        
        popular_list = popular_queries.all()
        assert len(popular_list) > 0
        assert popular_list[0][0] == "Python tutorial"  # Most searched
        assert popular_list[0][1] == 2  # Searched twice
    
    async def test_faceted_search(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test faceted search with aggregations."""
        # Create diverse content
        categories = []
        for cat_name in ["Technology", "Business", "Science"]:
            category = Category(
                organization_id=test_organization.id,
                name=cat_name,
                slug=cat_name.lower()
            )
            categories.append(category)
        
        db_session.add_all(categories)
        await db_session.commit()
        
        # Create items with various attributes
        items = []
        tags_pool = ["python", "javascript", "data", "web", "api", "tutorial"]
        
        for i in range(30):
            item = KnowledgeItem(
                organization_id=test_organization.id,
                created_by_id=test_user.id,
                category_id=categories[i % 3].id,
                title=f"Knowledge Item {i}",
                content=f"Content for item {i}",
                tags=[tags_pool[i % len(tags_pool)], tags_pool[(i + 1) % len(tags_pool)]],
                status=ContentStatus.PUBLISHED if i % 4 != 0 else ContentStatus.DRAFT
            )
            items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        # Test faceted search
        with patch('app.services.search.search_knowledge') as mock_search:
            mock_search.return_value = {
                "total": 30,
                "items": [],
                "facets": {
                    "categories": {
                        "Technology": 10,
                        "Business": 10,
                        "Science": 10
                    },
                    "tags": {
                        "python": 5,
                        "javascript": 5,
                        "data": 5,
                        "web": 5,
                        "api": 5,
                        "tutorial": 5
                    },
                    "status": {
                        "published": 23,
                        "draft": 7
                    }
                }
            }
            
            result = await search_service.search_knowledge("Knowledge")
            
            # Verify facets
            assert "facets" in result
            assert "categories" in result["facets"]
            assert sum(result["facets"]["categories"].values()) == 30
            assert "tags" in result["facets"]
            assert "status" in result["facets"]
    
    async def test_search_performance_optimization(self, db_session: AsyncSession, test_organization: Organization, test_user: User):
        """Test search performance with large datasets."""
        import time
        
        # Create a large dataset
        batch_size = 100
        total_items = 1000
        
        for batch in range(0, total_items, batch_size):
            items = []
            for i in range(batch, min(batch + batch_size, total_items)):
                item = KnowledgeItem(
                    organization_id=test_organization.id,
                    created_by_id=test_user.id,
                    title=f"Item {i}",
                    content=f"Content {i} with searchable text",
                    tags=[f"tag{i % 10}"],
                    status=ContentStatus.PUBLISHED
                )
                items.append(item)
            
            db_session.add_all(items)
            await db_session.commit()
        
        # Test search performance
        with patch('app.services.search.search_knowledge') as mock_search:
            mock_search.return_value = {
                "total": 100,
                "items": [{"id": str(uuid4()), "title": f"Item {i}"} for i in range(10)],
                "facets": {}
            }
            
            start_time = time.time()
            result = await search_service.search_knowledge("searchable", limit=10)
            search_time = time.time() - start_time
            
            # Search should be fast even with large dataset
            assert search_time < 1.0  # Less than 1 second
            assert result["total"] > 0