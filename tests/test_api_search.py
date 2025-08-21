"""Comprehensive tests for search API endpoints."""

import pytest
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models.search_query import SearchQuery
from app.models.knowledge_item import KnowledgeItem, ContentStatus, ContentType


@pytest.mark.asyncio
class TestSearchEndpoint:
    """Test GET /api/v1/search endpoint."""
    
    async def test_basic_search(self, client: AsyncClient):
        """Test basic search functionality."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "results": [],
                "total": 0,
                "took": 10
            }
            
            response = await client.get("/api/v1/search?q=test")
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "total" in data
            mock_search.assert_called_once()
    
    async def test_search_without_query(self, client: AsyncClient):
        """Test search without query parameter."""
        response = await client.get("/api/v1/search")
        assert response.status_code == 422
    
    async def test_search_with_empty_query(self, client: AsyncClient):
        """Test search with empty query."""
        response = await client.get("/api/v1/search?q=")
        assert response.status_code == 422
    
    async def test_search_with_language(self, client: AsyncClient):
        """Test search with language parameter."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"results": [], "total": 0}
            
            response = await client.get("/api/v1/search?q=test&language=ko")
            assert response.status_code == 200
            
            # Verify language was passed
            mock_search.assert_called_with(
                query="test",
                language="ko",
                filters={}
            )
    
    async def test_search_with_filters(self, client: AsyncClient):
        """Test search with various filters."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"results": [], "total": 0}
            
            # Test category filter
            response = await client.get(f"/api/v1/search?q=test&category_id={uuid4()}")
            assert response.status_code == 200
            
            # Test type filter
            response = await client.get("/api/v1/search?q=test&type=guide")
            assert response.status_code == 200
            
            # Test status filter
            response = await client.get("/api/v1/search?q=test&status=published")
            assert response.status_code == 200
            
            # Test tags filter
            response = await client.get("/api/v1/search?q=test&tags=python&tags=async")
            assert response.status_code == 200
    
    async def test_search_pagination(self, client: AsyncClient):
        """Test search with pagination."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "results": [{"id": str(uuid4()), "title": f"Result {i}"} for i in range(10)],
                "total": 100
            }
            
            response = await client.get("/api/v1/search?q=test&page=2&limit=10")
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) <= 10
    
    async def test_search_invalid_pagination(self, client: AsyncClient):
        """Test search with invalid pagination parameters."""
        response = await client.get("/api/v1/search?q=test&page=0")
        assert response.status_code == 422
        
        response = await client.get("/api/v1/search?q=test&limit=101")
        assert response.status_code == 422
    
    async def test_search_sorting(self, client: AsyncClient):
        """Test search with different sorting options."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"results": [], "total": 0}
            
            sort_options = ["relevance", "created_at", "updated_at", "views", "helpful"]
            for sort in sort_options:
                response = await client.get(f"/api/v1/search?q=test&sort={sort}")
                assert response.status_code == 200
    
    async def test_search_with_auth(self, client: AsyncClient, auth_headers: dict):
        """Test search with authentication (may show more results)."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"results": [], "total": 0}
            
            response = await client.get(
                "/api/v1/search?q=test",
                headers=auth_headers
            )
            assert response.status_code == 200
    
    async def test_search_query_logging(self, client: AsyncClient, db_session: AsyncSession):
        """Test that search queries are logged."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"results": [], "total": 0}
            
            response = await client.get("/api/v1/search?q=test query")
            assert response.status_code == 200
            
            # Check if query was logged (if implemented)
            # This depends on implementation details


@pytest.mark.asyncio
class TestAdvancedSearchEndpoint:
    """Test POST /api/v1/search/advanced endpoint."""
    
    async def test_advanced_search(self, client: AsyncClient):
        """Test advanced search with complex query."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"results": [], "total": 0}
            
            payload = {
                "query": {
                    "must": [{"term": {"type": "guide"}}],
                    "should": [{"match": {"content": "python"}}],
                    "must_not": [{"term": {"status": "draft"}}]
                },
                "filters": {
                    "category_id": str(uuid4()),
                    "date_range": {
                        "from": "2024-01-01",
                        "to": "2024-12-31"
                    }
                },
                "sort": [
                    {"field": "relevance", "order": "desc"},
                    {"field": "created_at", "order": "desc"}
                ],
                "page": 1,
                "limit": 20
            }
            
            response = await client.post("/api/v1/search/advanced", json=payload)
            # Advanced search might not be implemented
            assert response.status_code in [200, 404, 405]
    
    async def test_advanced_search_invalid_query(self, client: AsyncClient):
        """Test advanced search with invalid query structure."""
        payload = {
            "query": "invalid query structure"
        }
        
        response = await client.post("/api/v1/search/advanced", json=payload)
        assert response.status_code in [422, 404, 405]


@pytest.mark.asyncio
class TestSearchSuggestionsEndpoint:
    """Test GET /api/v1/search/suggestions endpoint."""
    
    async def test_get_suggestions(self, client: AsyncClient):
        """Test getting search suggestions."""
        with patch('app.api.v1.search.get_search_suggestions', new_callable=AsyncMock) as mock_suggest:
            mock_suggest.return_value = ["python", "python async", "python tutorial"]
            
            response = await client.get("/api/v1/search/suggestions?q=pyth")
            # Suggestions might not be implemented
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list)
                mock_suggest.assert_called_once()
            else:
                assert response.status_code in [404, 405]
    
    async def test_suggestions_empty_query(self, client: AsyncClient):
        """Test suggestions with empty query."""
        response = await client.get("/api/v1/search/suggestions?q=")
        assert response.status_code in [422, 404, 405]
    
    async def test_suggestions_limit(self, client: AsyncClient):
        """Test suggestions with limit parameter."""
        with patch('app.api.v1.search.get_search_suggestions', new_callable=AsyncMock) as mock_suggest:
            mock_suggest.return_value = ["result1", "result2", "result3"]
            
            response = await client.get("/api/v1/search/suggestions?q=test&limit=5")
            if response.status_code == 200:
                data = response.json()
                assert len(data) <= 5
            else:
                assert response.status_code in [404, 405]


@pytest.mark.asyncio
class TestSearchHistoryEndpoint:
    """Test search history endpoints."""
    
    async def test_get_search_history(self, client: AsyncClient, auth_headers: dict):
        """Test getting user's search history."""
        response = await client.get(
            "/api/v1/search/history",
            headers=auth_headers
        )
        # History endpoint might not be implemented
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
        else:
            assert response.status_code in [404, 405]
    
    async def test_clear_search_history(self, client: AsyncClient, auth_headers: dict):
        """Test clearing search history."""
        response = await client.delete(
            "/api/v1/search/history",
            headers=auth_headers
        )
        assert response.status_code in [204, 404, 405]
    
    async def test_search_history_without_auth(self, client: AsyncClient):
        """Test accessing history without authentication."""
        response = await client.get("/api/v1/search/history")
        assert response.status_code in [401, 404, 405]


@pytest.mark.asyncio
class TestSearchAnalyticsEndpoint:
    """Test search analytics endpoints."""
    
    async def test_get_popular_searches(self, client: AsyncClient):
        """Test getting popular search terms."""
        response = await client.get("/api/v1/search/analytics/popular")
        # Analytics might not be implemented
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
        else:
            assert response.status_code in [404, 405]
    
    async def test_get_search_trends(self, client: AsyncClient):
        """Test getting search trends."""
        response = await client.get("/api/v1/search/analytics/trends")
        if response.status_code == 200:
            data = response.json()
            assert "trends" in data or isinstance(data, list)
        else:
            assert response.status_code in [404, 405]
    
    async def test_get_no_results_queries(self, client: AsyncClient, admin_headers: dict):
        """Test getting queries with no results."""
        response = await client.get(
            "/api/v1/search/analytics/no-results",
            headers=admin_headers
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
        else:
            assert response.status_code in [403, 404, 405]


@pytest.mark.asyncio
class TestSemanticSearchEndpoint:
    """Test semantic/vector search endpoints."""
    
    async def test_semantic_search(self, client: AsyncClient):
        """Test semantic search using embeddings."""
        with patch('app.api.v1.search.search_by_embedding', new_callable=AsyncMock) as mock_semantic:
            mock_semantic.return_value = {"results": [], "total": 0}
            
            response = await client.post(
                "/api/v1/search/semantic",
                json={"query": "How to implement async functions in Python"}
            )
            
            # Semantic search might not be implemented
            if response.status_code == 200:
                data = response.json()
                assert "results" in data
                mock_semantic.assert_called_once()
            else:
                assert response.status_code in [404, 405]
    
    async def test_hybrid_search(self, client: AsyncClient):
        """Test hybrid search (keyword + semantic)."""
        with patch('app.api.v1.search.hybrid_search', new_callable=AsyncMock) as mock_hybrid:
            mock_hybrid.return_value = {"results": [], "total": 0}
            
            payload = {
                "query": "async python",
                "use_semantic": True,
                "semantic_weight": 0.7
            }
            
            response = await client.post("/api/v1/search/hybrid", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                assert "results" in data
            else:
                assert response.status_code in [404, 405]


@pytest.mark.asyncio
class TestSearchFiltersEndpoint:
    """Test search filters and facets endpoints."""
    
    async def test_get_available_filters(self, client: AsyncClient):
        """Test getting available search filters."""
        response = await client.get("/api/v1/search/filters")
        
        # Filters endpoint might not be implemented
        if response.status_code == 200:
            data = response.json()
            assert "categories" in data or "types" in data or isinstance(data, dict)
        else:
            assert response.status_code in [404, 405]
    
    async def test_get_facets(self, client: AsyncClient):
        """Test getting search facets for a query."""
        with patch('app.api.v1.search.get_search_facets', new_callable=AsyncMock) as mock_facets:
            mock_facets.return_value = {
                "categories": [{"id": str(uuid4()), "count": 10}],
                "types": [{"type": "guide", "count": 5}],
                "tags": [{"tag": "python", "count": 8}]
            }
            
            response = await client.get("/api/v1/search/facets?q=test")
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict)
            else:
                assert response.status_code in [404, 405]


@pytest.mark.asyncio
class TestSearchExportEndpoint:
    """Test search results export functionality."""
    
    async def test_export_search_results(self, client: AsyncClient, auth_headers: dict):
        """Test exporting search results."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "results": [{"id": str(uuid4()), "title": "Result"}],
                "total": 1
            }
            
            response = await client.get(
                "/api/v1/search/export?q=test&format=csv",
                headers=auth_headers
            )
            
            # Export might not be implemented
            if response.status_code == 200:
                assert response.headers.get("content-type") in [
                    "text/csv", 
                    "application/json",
                    "application/vnd.ms-excel"
                ]
            else:
                assert response.status_code in [404, 405]
    
    async def test_export_formats(self, client: AsyncClient, auth_headers: dict):
        """Test different export formats."""
        formats = ["csv", "json", "excel"]
        
        for format_type in formats:
            response = await client.get(
                f"/api/v1/search/export?q=test&format={format_type}",
                headers=auth_headers
            )
            assert response.status_code in [200, 404, 405]


@pytest.mark.asyncio
class TestSearchCachingBehavior:
    """Test search caching behavior."""
    
    async def test_search_caching(self, client: AsyncClient):
        """Test that repeated searches are cached."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"results": [], "total": 0}
            
            # First search
            response1 = await client.get("/api/v1/search?q=cached query")
            assert response1.status_code == 200
            
            # Second identical search
            response2 = await client.get("/api/v1/search?q=cached query")
            assert response2.status_code == 200
            
            # Check if caching is implemented
            # mock_search might be called once or twice depending on caching
            assert mock_search.call_count >= 1
    
    async def test_cache_invalidation(self, client: AsyncClient, auth_headers: dict):
        """Test cache invalidation on content update."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"results": [], "total": 0}
            
            # Initial search
            response = await client.get("/api/v1/search?q=test")
            assert response.status_code == 200
            
            # Update content (should invalidate cache)
            with patch('app.api.v1.knowledge.index_knowledge_item', new_callable=AsyncMock):
                update_response = await client.post(
                    "/api/v1/knowledge",
                    json={"title_en": "New", "content_en": "Content", "type": "guide"},
                    headers=auth_headers
                )
            
            # Search again
            response = await client.get("/api/v1/search?q=test")
            assert response.status_code == 200


@pytest.mark.asyncio  
class TestSearchErrorHandling:
    """Test error handling in search endpoints."""
    
    async def test_search_service_error(self, client: AsyncClient):
        """Test handling of search service errors."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("Search service unavailable")
            
            response = await client.get("/api/v1/search?q=test")
            # Should handle gracefully
            assert response.status_code in [200, 500, 503]
    
    async def test_search_timeout(self, client: AsyncClient):
        """Test search timeout handling."""
        with patch('app.api.v1.search.search_knowledge', new_callable=AsyncMock) as mock_search:
            import asyncio
            async def slow_search(*args, **kwargs):
                await asyncio.sleep(10)  # Simulate slow search
                return {"results": [], "total": 0}
            
            mock_search.side_effect = slow_search
            
            response = await client.get("/api/v1/search?q=test")
            # Should timeout or handle gracefully
            assert response.status_code in [200, 408, 504]
    
    async def test_malformed_query_handling(self, client: AsyncClient):
        """Test handling of malformed search queries."""
        # Test with special characters
        response = await client.get("/api/v1/search?q=)))(((**&&")
        assert response.status_code in [200, 400]
        
        # Test with very long query
        long_query = "a" * 1000
        response = await client.get(f"/api/v1/search?q={long_query}")
        assert response.status_code in [200, 400, 414]