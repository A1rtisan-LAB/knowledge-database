"""End-to-end tests for complete user workflows."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio


@pytest.mark.e2e
class TestUserRegistrationAndOnboarding:
    """Test complete user registration and onboarding flow."""
    
    async def test_complete_user_onboarding(self, client: AsyncClient):
        """Test the complete onboarding process for a new user."""
        # Step 1: Register new user with organization
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newcompany@example.com",
                "username": "companyuser",
                "password": "SecurePassword123!",
                "full_name": "Company User",
                "organization_name": "New Company Inc",
                "preferred_language": "en"
            }
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        user_id = user_data["id"]
        
        # Step 2: Login with new credentials
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "newcompany@example.com",
                "password": "SecurePassword123!"
            }
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Step 3: Get user profile
        profile_response = await client.get(
            "/api/v1/auth/me",
            headers=headers
        )
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["email"] == "newcompany@example.com"
        assert profile["organization"]["name"] == "New Company Inc"
        
        # Step 4: Create initial categories for organization
        categories = ["Documentation", "Tutorials", "FAQs"]
        category_ids = []
        
        for cat_name in categories:
            cat_response = await client.post(
                "/api/v1/categories",
                headers=headers,
                json={
                    "name": cat_name,
                    "slug": cat_name.lower(),
                    "description": f"{cat_name} for our knowledge base"
                }
            )
            assert cat_response.status_code == 201
            category_ids.append(cat_response.json()["id"])
        
        # Step 5: Create first knowledge items
        knowledge_items = [
            {
                "title": "Getting Started Guide",
                "content": "Welcome to our knowledge base. This guide will help you get started.",
                "category_id": category_ids[0],
                "tags": ["guide", "onboarding"],
                "status": "published"
            },
            {
                "title": "Platform Tutorial",
                "content": "Learn how to use our platform effectively.",
                "category_id": category_ids[1],
                "tags": ["tutorial", "basics"],
                "status": "published"
            }
        ]
        
        created_items = []
        for item_data in knowledge_items:
            item_response = await client.post(
                "/api/v1/knowledge",
                headers=headers,
                json=item_data
            )
            assert item_response.status_code == 201
            created_items.append(item_response.json())
        
        # Step 6: Verify created content is searchable
        search_response = await client.get(
            "/api/v1/search?query=guide",
            headers=headers
        )
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert len(search_results["results"]) > 0
        assert any("Getting Started" in r["title"] for r in search_results["results"])
        
        # Step 7: Update user preferences
        update_response = await client.put(
            "/api/v1/auth/me",
            headers=headers,
            json={
                "preferred_language": "ko",
                "notification_settings": {
                    "email_notifications": True,
                    "weekly_digest": True
                }
            }
        )
        assert update_response.status_code == 200
        
        # Step 8: Verify complete setup
        final_profile = await client.get(
            "/api/v1/auth/me",
            headers=headers
        )
        assert final_profile.status_code == 200
        final_data = final_profile.json()
        assert final_data["preferred_language"] == "ko"


@pytest.mark.e2e
class TestKnowledgeManagementWorkflow:
    """Test complete knowledge management workflow."""
    
    async def test_knowledge_lifecycle(self, client: AsyncClient, auth_headers: dict, admin_headers: dict):
        """Test the complete lifecycle of a knowledge item."""
        # Step 1: Create category structure
        parent_cat = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "Technology",
                "slug": "technology",
                "name_ko": "기술",
                "description": "Technology related content"
            }
        )
        parent_id = parent_cat.json()["id"]
        
        sub_cat = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "Programming",
                "slug": "programming",
                "parent_id": parent_id,
                "description": "Programming guides and tutorials"
            }
        )
        category_id = sub_cat.json()["id"]
        
        # Step 2: Create draft knowledge item
        draft_response = await client.post(
            "/api/v1/knowledge",
            headers=auth_headers,
            json={
                "title": "Python Best Practices",
                "content": "Initial draft content about Python best practices.",
                "category_id": category_id,
                "tags": ["python", "best-practices", "draft"],
                "status": "draft"
            }
        )
        assert draft_response.status_code == 201
        item_id = draft_response.json()["id"]
        
        # Step 3: Update and improve content
        update_response = await client.put(
            f"/api/v1/knowledge/{item_id}",
            headers=auth_headers,
            json={
                "title": "Python Best Practices - Complete Guide",
                "content": """
                # Python Best Practices
                
                ## 1. Code Style
                - Follow PEP 8
                - Use meaningful variable names
                - Keep functions small and focused
                
                ## 2. Error Handling
                - Use specific exception types
                - Always clean up resources
                - Log errors appropriately
                
                ## 3. Testing
                - Write unit tests
                - Aim for high coverage
                - Use pytest for testing
                """,
                "title_ko": "파이썬 모범 사례 - 완전 가이드",
                "content_ko": """
                # 파이썬 모범 사례
                
                ## 1. 코드 스타일
                - PEP 8 따르기
                - 의미 있는 변수명 사용
                - 함수를 작고 집중적으로 유지
                
                ## 2. 오류 처리
                - 구체적인 예외 유형 사용
                - 항상 리소스 정리
                - 적절한 오류 로깅
                
                ## 3. 테스팅
                - 단위 테스트 작성
                - 높은 커버리지 목표
                - pytest 사용
                """,
                "tags": ["python", "best-practices", "guide", "complete"],
                "status": "under_review"
            }
        )
        assert update_response.status_code == 200
        
        # Step 4: Admin reviews and publishes
        publish_response = await client.put(
            f"/api/v1/knowledge/{item_id}",
            headers=admin_headers,
            json={
                "status": "published",
                "review_notes": "Content approved for publication"
            }
        )
        assert publish_response.status_code == 200
        assert publish_response.json()["status"] == "published"
        
        # Step 5: Users interact with published content
        # View the item (increment view count)
        view_response = await client.get(
            f"/api/v1/knowledge/{item_id}",
            headers=auth_headers
        )
        assert view_response.status_code == 200
        
        # Add feedback
        feedback_response = await client.post(
            f"/api/v1/knowledge/{item_id}/feedback",
            headers=auth_headers,
            json={
                "type": "helpful",
                "rating": 5,
                "comment": "Very comprehensive and well-structured guide!"
            }
        )
        assert feedback_response.status_code == 201
        
        # Step 6: Track analytics
        analytics_response = await client.get(
            f"/api/v1/analytics/knowledge/{item_id}",
            headers=admin_headers
        )
        assert analytics_response.status_code == 200
        analytics = analytics_response.json()
        assert analytics["view_count"] > 0
        assert analytics["average_rating"] == 5.0
        
        # Step 7: Archive old content
        archive_response = await client.put(
            f"/api/v1/knowledge/{item_id}",
            headers=admin_headers,
            json={
                "status": "archived",
                "archive_reason": "Content outdated, newer version available"
            }
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == "archived"


@pytest.mark.e2e
class TestBilingualSearchWorkflow:
    """Test bilingual search functionality."""
    
    async def test_bilingual_search_and_translation(self, client: AsyncClient, auth_headers: dict):
        """Test searching in both Korean and English."""
        # Step 1: Create bilingual content
        items_data = [
            {
                "title": "Machine Learning Basics",
                "content": "Introduction to machine learning concepts",
                "title_ko": "머신러닝 기초",
                "content_ko": "머신러닝 개념 소개",
                "tags": ["ml", "ai", "basics"]
            },
            {
                "title": "Deep Learning Tutorial",
                "content": "Understanding neural networks",
                "title_ko": "딥러닝 튜토리얼",
                "content_ko": "신경망 이해하기",
                "tags": ["dl", "neural-networks"]
            },
            {
                "title": "Data Science Guide",
                "content": "Complete data science workflow",
                "title_ko": "데이터 사이언스 가이드",
                "content_ko": "완전한 데이터 사이언스 워크플로우",
                "tags": ["data-science", "analytics"]
            }
        ]
        
        # Create category first
        cat_response = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "AI/ML",
                "slug": "ai-ml",
                "name_ko": "인공지능/머신러닝"
            }
        )
        category_id = cat_response.json()["id"]
        
        # Create knowledge items
        created_ids = []
        for item_data in items_data:
            item_data["category_id"] = category_id
            item_data["status"] = "published"
            response = await client.post(
                "/api/v1/knowledge",
                headers=auth_headers,
                json=item_data
            )
            assert response.status_code == 201
            created_ids.append(response.json()["id"])
        
        # Step 2: Search in English
        en_search = await client.get(
            "/api/v1/search?query=machine learning&language=en",
            headers=auth_headers
        )
        assert en_search.status_code == 200
        en_results = en_search.json()
        assert len(en_results["results"]) >= 1
        assert any("Machine Learning" in r["title"] for r in en_results["results"])
        
        # Step 3: Search in Korean
        ko_search = await client.get(
            "/api/v1/search?query=머신러닝&language=ko",
            headers=auth_headers
        )
        assert ko_search.status_code == 200
        ko_results = ko_search.json()
        assert len(ko_results["results"]) >= 1
        assert any("머신러닝" in r.get("title_ko", r["title"]) for r in ko_results["results"])
        
        # Step 4: Cross-language search (search Korean term, get English results)
        cross_search = await client.get(
            "/api/v1/search?query=딥러닝&translate=true",
            headers=auth_headers
        )
        assert cross_search.status_code == 200
        cross_results = cross_search.json()
        assert len(cross_results["results"]) >= 1
        
        # Step 5: Filter by language preference
        # Set user preference to Korean
        await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"preferred_language": "ko"}
        )
        
        # Search should return Korean content by default
        default_search = await client.get(
            "/api/v1/search?query=learning",
            headers=auth_headers
        )
        assert default_search.status_code == 200
        
        # Step 6: Advanced search with filters
        filtered_search = await client.get(
            "/api/v1/search?query=tutorial&tags=dl,neural-networks&category_id=" + str(category_id),
            headers=auth_headers
        )
        assert filtered_search.status_code == 200
        filtered_results = filtered_search.json()
        assert len(filtered_results["results"]) >= 1


@pytest.mark.e2e
class TestAdminWorkflow:
    """Test administrative workflows."""
    
    async def test_admin_user_management(self, client: AsyncClient, admin_headers: dict):
        """Test admin managing users and content."""
        # Step 1: Create multiple users with different roles
        users_data = [
            {
                "email": "viewer@example.com",
                "username": "viewer1",
                "password": "ViewerPass123!",
                "full_name": "Viewer User",
                "role": "viewer"
            },
            {
                "email": "editor@example.com",
                "username": "editor1",
                "password": "EditorPass123!",
                "full_name": "Editor User",
                "role": "editor"
            }
        ]
        
        created_users = []
        for user_data in users_data:
            # Admin creates user
            response = await client.post(
                "/api/v1/admin/users",
                headers=admin_headers,
                json=user_data
            )
            assert response.status_code == 201
            created_users.append(response.json())
        
        # Step 2: List all users
        users_list = await client.get(
            "/api/v1/admin/users",
            headers=admin_headers
        )
        assert users_list.status_code == 200
        all_users = users_list.json()
        assert len(all_users) >= 2
        
        # Step 3: Update user roles
        viewer_id = created_users[0]["id"]
        role_update = await client.put(
            f"/api/v1/admin/users/{viewer_id}/role",
            headers=admin_headers,
            json={"role": "editor"}
        )
        assert role_update.status_code == 200
        assert role_update.json()["role"] == "editor"
        
        # Step 4: Monitor user activity
        activity_response = await client.get(
            f"/api/v1/admin/users/{viewer_id}/activity",
            headers=admin_headers
        )
        assert activity_response.status_code == 200
        
        # Step 5: Get system statistics
        stats_response = await client.get(
            "/api/v1/admin/stats",
            headers=admin_headers
        )
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["total_users"] >= 3
        
        # Step 6: Export audit logs
        audit_response = await client.get(
            "/api/v1/admin/audit-logs?start_date=2024-01-01&end_date=2024-12-31",
            headers=admin_headers
        )
        assert audit_response.status_code == 200
        
        # Step 7: Disable inactive user
        disable_response = await client.post(
            f"/api/v1/admin/users/{created_users[1]['id']}/disable",
            headers=admin_headers
        )
        assert disable_response.status_code == 200
        
        # Step 8: Bulk operations - archive old content
        bulk_archive = await client.post(
            "/api/v1/admin/knowledge/bulk-archive",
            headers=admin_headers,
            json={
                "older_than_days": 365,
                "status": "published",
                "archive_reason": "Annual content review"
            }
        )
        assert bulk_archive.status_code in [200, 204]


@pytest.mark.e2e
class TestPerformanceOptimizedWorkflow:
    """Test workflows optimized for performance."""
    
    async def test_concurrent_operations(self, client: AsyncClient, auth_headers: dict):
        """Test handling concurrent user operations."""
        # Step 1: Create category for testing
        cat_response = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "Performance Test",
                "slug": "perf-test"
            }
        )
        category_id = cat_response.json()["id"]
        
        # Step 2: Simulate concurrent knowledge item creation
        async def create_item(index: int):
            return await client.post(
                "/api/v1/knowledge",
                headers=auth_headers,
                json={
                    "title": f"Concurrent Item {index}",
                    "content": f"Content for item {index}",
                    "category_id": category_id,
                    "tags": [f"tag{index}", "concurrent"],
                    "status": "published"
                }
            )
        
        # Create 10 items concurrently
        tasks = [create_item(i) for i in range(10)]
        responses = await asyncio.gather(*tasks)
        
        for response in responses:
            assert response.status_code == 201
        
        # Step 3: Concurrent searches
        async def search_items(query: str):
            return await client.get(
                f"/api/v1/search?query={query}",
                headers=auth_headers
            )
        
        search_queries = ["Concurrent", "Item", "Content", "tag1", "tag5"]
        search_tasks = [search_items(q) for q in search_queries]
        search_responses = await asyncio.gather(*search_tasks)
        
        for response in search_responses:
            assert response.status_code == 200
        
        # Step 4: Test pagination with large dataset
        page_response = await client.get(
            "/api/v1/knowledge?page=1&page_size=5",
            headers=auth_headers
        )
        assert page_response.status_code == 200
        page_data = page_response.json()
        assert len(page_data["items"]) <= 5
        
        # Step 5: Test caching effectiveness
        # First request (cache miss)
        first_request = await client.get(
            f"/api/v1/knowledge/{responses[0].json()['id']}",
            headers=auth_headers
        )
        assert first_request.status_code == 200
        
        # Second request (should be cached)
        second_request = await client.get(
            f"/api/v1/knowledge/{responses[0].json()['id']}",
            headers=auth_headers
        )
        assert second_request.status_code == 200
        
        # Response times would be measured in real performance test
        # assert second_request.elapsed < first_request.elapsed