"""Comprehensive unit tests for Search service."""

import pytest
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from app.services import search as search_service
from app.services import opensearch


@pytest.mark.unit
class TestSearchService:
    """Comprehensive test suite for search service functions."""
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return Mock(spec=logging.getLogger())
    
    @pytest.fixture
    def mock_opensearch_client(self):
        """Create mock OpenSearch client."""
        mock_client = Mock()
        mock_client.index = AsyncMock(return_value={"result": "created"})
        mock_client.delete = AsyncMock(return_value={"result": "deleted"})
        mock_client.search = AsyncMock(return_value={
            "hits": {
                "total": {"value": 0},
                "hits": []
            },
            "aggregations": {}
        })
        return mock_client
    
    @pytest.fixture
    def sample_item_data(self):
        """Create sample knowledge item data."""
        return {
            "item_id": uuid4(),
            "title_ko": "테스트 제목",
            "title_en": "Test Title",
            "content_ko": "이것은 테스트 내용입니다. 한국어로 작성된 지식 항목입니다.",
            "content_en": "This is test content. A knowledge item written in English.",
            "tags": ["test", "sample", "knowledge"],
            "category_name": "Test Category"
        }
    
    # Test: index_knowledge_item
    async def test_index_knowledge_item_success(self, mock_logger, sample_item_data):
        """Test successful indexing of a knowledge item."""
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.index_knowledge_item(
                    item_id=sample_item_data["item_id"],
                    title_ko=sample_item_data["title_ko"],
                    title_en=sample_item_data["title_en"],
                    content_ko=sample_item_data["content_ko"],
                    content_en=sample_item_data["content_en"],
                    tags=sample_item_data["tags"],
                    category_name=sample_item_data["category_name"]
                )
                
                assert result is True
                mock_logger.info.assert_called_once()
                assert str(sample_item_data["item_id"]) in mock_logger.info.call_args[0][0]
    
    async def test_index_knowledge_item_without_category(self, mock_logger):
        """Test indexing without category name."""
        item_id = uuid4()
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.index_knowledge_item(
                    item_id=item_id,
                    title_ko="제목",
                    title_en="Title",
                    content_ko="내용",
                    content_en="Content",
                    tags=["tag1", "tag2"],
                    category_name=None
                )
                
                assert result is True
                mock_logger.info.assert_called_once_with(f"Indexing knowledge item {item_id}")
    
    async def test_index_knowledge_item_empty_tags(self, mock_logger):
        """Test indexing with empty tags list."""
        item_id = uuid4()
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.index_knowledge_item(
                    item_id=item_id,
                    title_ko="제목",
                    title_en="Title",
                    content_ko="내용",
                    content_en="Content",
                    tags=[],
                    category_name="Category"
                )
                
                assert result is True
                mock_logger.info.assert_called_once()
    
    async def test_index_knowledge_item_long_content(self, mock_logger):
        """Test indexing with very long content."""
        item_id = uuid4()
        long_content_ko = "한국어 문장. " * 1000
        long_content_en = "English sentence. " * 1000
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.index_knowledge_item(
                    item_id=item_id,
                    title_ko="긴 제목",
                    title_en="Long Title",
                    content_ko=long_content_ko,
                    content_en=long_content_en,
                    tags=["long", "content"],
                    category_name="Long Content Category"
                )
                
                assert result is True
    
    async def test_index_knowledge_item_special_characters(self, mock_logger):
        """Test indexing with special characters."""
        item_id = uuid4()
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.index_knowledge_item(
                    item_id=item_id,
                    title_ko="특수문자 @#$% 제목",
                    title_en="Special chars @#$% title",
                    content_ko="내용 with 😀 émojis",
                    content_en="Content with 😀 émojis",
                    tags=["special", "chars", "@#$"],
                    category_name="Special!Category"
                )
                
                assert result is True
    
    async def test_index_knowledge_item_exception(self, mock_logger):
        """Test indexing when exception occurs."""
        item_id = uuid4()
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', side_effect=Exception("Connection error")):
                result = await search_service.index_knowledge_item(
                    item_id=item_id,
                    title_ko="제목",
                    title_en="Title",
                    content_ko="내용",
                    content_en="Content",
                    tags=["tag"],
                    category_name="Category"
                )
                
                assert result is False
                mock_logger.error.assert_called_once()
                assert "Failed to index knowledge item" in mock_logger.error.call_args[0][0]
    
    async def test_index_knowledge_item_batch(self, mock_logger):
        """Test batch indexing of multiple items."""
        items = [
            {
                "item_id": uuid4(),
                "title_ko": f"제목 {i}",
                "title_en": f"Title {i}",
                "content_ko": f"내용 {i}",
                "content_en": f"Content {i}",
                "tags": [f"tag{i}"],
                "category_name": f"Category {i}"
            }
            for i in range(10)
        ]
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                results = []
                for item in items:
                    result = await search_service.index_knowledge_item(**item)
                    results.append(result)
                
                assert all(results)
                assert mock_logger.info.call_count == 10
    
    # Test: delete_from_index
    async def test_delete_from_index_success(self, mock_logger):
        """Test successful deletion from index."""
        item_id = uuid4()
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.delete_from_index(item_id)
                
                assert result is True
                mock_logger.info.assert_called_once_with(
                    f"Deleting knowledge item {item_id} from index"
                )
    
    async def test_delete_from_index_string_uuid(self, mock_logger):
        """Test deletion with string UUID."""
        item_id = uuid4()
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                # Pass as string instead of UUID object
                result = await search_service.delete_from_index(str(item_id))
                
                assert result is True
                mock_logger.info.assert_called_once()
    
    async def test_delete_from_index_exception(self, mock_logger):
        """Test deletion when exception occurs."""
        item_id = uuid4()
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', side_effect=Exception("Connection error")):
                result = await search_service.delete_from_index(item_id)
                
                assert result is False
                mock_logger.error.assert_called_once()
                assert "Failed to delete knowledge item" in mock_logger.error.call_args[0][0]
    
    async def test_delete_from_index_batch(self, mock_logger):
        """Test batch deletion of multiple items."""
        item_ids = [uuid4() for _ in range(10)]
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                results = []
                for item_id in item_ids:
                    result = await search_service.delete_from_index(item_id)
                    results.append(result)
                
                assert all(results)
                assert mock_logger.info.call_count == 10
    
    # Test: search_knowledge
    async def test_search_knowledge_basic(self, mock_logger):
        """Test basic knowledge search."""
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.search_knowledge(
                    query="test query",
                    language="ko"
                )
                
                assert result["total"] == 0
                assert result["items"] == []
                assert "facets" in result
                mock_logger.info.assert_called_once_with(
                    "Searching knowledge items with query: test query"
                )
    
    async def test_search_knowledge_with_all_parameters(self, mock_logger):
        """Test search with all parameters specified."""
        category_id = uuid4()
        tags = ["python", "testing", "development"]
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.search_knowledge(
                    query="advanced search",
                    language="en",
                    category_id=category_id,
                    tags=tags,
                    limit=20,
                    offset=40
                )
                
                assert result["total"] == 0
                assert result["items"] == []
                assert isinstance(result["facets"], dict)
    
    async def test_search_knowledge_empty_query(self, mock_logger):
        """Test search with empty query."""
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.search_knowledge(
                    query="",
                    language="ko"
                )
                
                assert result["total"] == 0
                assert result["items"] == []
    
    async def test_search_knowledge_different_languages(self, mock_logger):
        """Test search with different language settings."""
        languages = ["ko", "en", "ja", "zh", "es", "fr"]
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                for lang in languages:
                    result = await search_service.search_knowledge(
                        query=f"query in {lang}",
                        language=lang
                    )
                    assert result["total"] == 0
                
                assert mock_logger.info.call_count == len(languages)
    
    async def test_search_knowledge_pagination(self, mock_logger):
        """Test search with various pagination settings."""
        pagination_tests = [
            (10, 0),   # First page
            (10, 10),  # Second page
            (20, 40),  # Third page with larger limit
            (50, 100), # Large offset
            (100, 0),  # Large limit
        ]
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                for limit, offset in pagination_tests:
                    result = await search_service.search_knowledge(
                        query="pagination test",
                        limit=limit,
                        offset=offset
                    )
                    assert result["total"] == 0
                    assert result["items"] == []
    
    async def test_search_knowledge_with_single_tag(self, mock_logger):
        """Test search with single tag filter."""
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.search_knowledge(
                    query="test",
                    tags=["python"]
                )
                
                assert result["total"] == 0
                assert result["items"] == []
    
    async def test_search_knowledge_with_many_tags(self, mock_logger):
        """Test search with many tag filters."""
        many_tags = [f"tag{i}" for i in range(50)]
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.search_knowledge(
                    query="test",
                    tags=many_tags
                )
                
                assert result["total"] == 0
                assert result["items"] == []
    
    async def test_search_knowledge_special_characters_query(self, mock_logger):
        """Test search with special characters in query."""
        special_queries = [
            "test @#$%",
            "한글 테스트 !@#",
            "query with \"quotes\"",
            "slash/test\\back",
            "wildcard*search?",
            "(parentheses) and [brackets]",
        ]
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                for query in special_queries:
                    result = await search_service.search_knowledge(query=query)
                    assert result["total"] == 0
                
                assert mock_logger.info.call_count == len(special_queries)
    
    async def test_search_knowledge_exception(self, mock_logger):
        """Test search when exception occurs."""
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', side_effect=Exception("Search failed")):
                result = await search_service.search_knowledge(
                    query="test query"
                )
                
                assert result["total"] == 0
                assert result["items"] == []
                assert result["facets"] == {}
                mock_logger.error.assert_called_once()
                assert "Search failed" in mock_logger.error.call_args[0][0]
    
    async def test_search_knowledge_unicode_content(self, mock_logger):
        """Test search with various unicode content."""
        unicode_queries = [
            "한국어 검색",
            "日本語の検索",
            "中文搜索",
            "Búsqueda en español",
            "Recherche en français",
            "Поиск на русском",
            "البحث بالعربية",
            "חיפוש בעברית",
        ]
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                for query in unicode_queries:
                    result = await search_service.search_knowledge(query=query)
                    assert result["total"] == 0
                    assert result["items"] == []
    
    # Edge cases and performance tests
    async def test_concurrent_searches(self, mock_logger):
        """Test concurrent search operations."""
        import asyncio
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                # Create concurrent search tasks
                tasks = [
                    search_service.search_knowledge(f"query {i}")
                    for i in range(20)
                ]
                
                results = await asyncio.gather(*tasks)
                
                assert len(results) == 20
                for result in results:
                    assert result["total"] == 0
                    assert result["items"] == []
    
    async def test_mixed_operations(self, mock_logger):
        """Test mixed index, search, and delete operations."""
        item_id = uuid4()
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                # Index
                index_result = await search_service.index_knowledge_item(
                    item_id=item_id,
                    title_ko="제목",
                    title_en="Title",
                    content_ko="내용",
                    content_en="Content",
                    tags=["test"],
                    category_name="Test"
                )
                assert index_result is True
                
                # Search
                search_result = await search_service.search_knowledge("test")
                assert search_result["total"] == 0
                
                # Delete
                delete_result = await search_service.delete_from_index(item_id)
                assert delete_result is True
                
                # Search again
                search_result2 = await search_service.search_knowledge("test")
                assert search_result2["total"] == 0
    
    async def test_search_with_none_parameters(self, mock_logger):
        """Test search with None values for optional parameters."""
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.search_knowledge(
                    query="test",
                    language="ko",
                    category_id=None,
                    tags=None,
                    limit=10,
                    offset=0
                )
                
                assert result["total"] == 0
                assert result["items"] == []
    
    async def test_search_boundary_values(self, mock_logger):
        """Test search with boundary values."""
        boundary_tests = [
            ("", "ko", None, None, 0, 0),      # Zero limit
            ("q", "ko", None, None, -1, 0),    # Negative limit
            ("q", "ko", None, None, 10, -1),   # Negative offset
            ("q", "ko", None, None, 999999, 0), # Very large limit
            ("q", "ko", None, None, 10, 999999), # Very large offset
        ]
        
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                for query, lang, cat_id, tags, limit, offset in boundary_tests:
                    result = await search_service.search_knowledge(
                        query=query,
                        language=lang,
                        category_id=cat_id,
                        tags=tags,
                        limit=limit,
                        offset=offset
                    )
                    assert result["total"] == 0
                    assert result["items"] == []
    
    async def test_search_result_structure(self, mock_logger):
        """Test that search results have expected structure."""
        with patch('app.services.search.logger', mock_logger):
            with patch('app.services.search.get_opensearch_client', return_value=Mock()):
                result = await search_service.search_knowledge("test")
                
                # Verify result structure
                assert isinstance(result, dict)
                assert "total" in result
                assert "items" in result
                assert "facets" in result
                assert isinstance(result["total"], int)
                assert isinstance(result["items"], list)
                assert isinstance(result["facets"], dict)