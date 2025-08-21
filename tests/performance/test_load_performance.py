"""Performance and load tests for the knowledge database API."""

import pytest
import asyncio
import time
import psutil
import statistics
from typing import List, Dict, Any
from httpx import AsyncClient
from concurrent.futures import ThreadPoolExecutor
import random
import string


@pytest.mark.performance
class TestAPIResponseTimes:
    """Test API response times under normal load."""
    
    async def test_endpoint_response_times(self, client: AsyncClient, auth_headers: dict):
        """Test that key endpoints respond within acceptable time limits."""
        endpoints = [
            ("/api/v1/auth/me", "GET", None),
            ("/api/v1/knowledge", "GET", None),
            ("/api/v1/categories", "GET", None),
            ("/api/v1/search?query=test", "GET", None),
        ]
        
        results = {}
        
        for endpoint, method, data in endpoints:
            times = []
            
            # Make 10 requests to each endpoint
            for _ in range(10):
                start_time = time.time()
                
                if method == "GET":
                    response = await client.get(endpoint, headers=auth_headers)
                elif method == "POST":
                    response = await client.post(endpoint, headers=auth_headers, json=data)
                
                elapsed = (time.time() - start_time) * 1000  # Convert to ms
                times.append(elapsed)
                
                assert response.status_code in [200, 201]
            
            # Calculate statistics
            results[endpoint] = {
                "mean": statistics.mean(times),
                "median": statistics.median(times),
                "p95": statistics.quantiles(times, n=20)[18],  # 95th percentile
                "max": max(times)
            }
            
            # Assert p95 < 200ms requirement
            assert results[endpoint]["p95"] < 200, f"{endpoint} p95 response time {results[endpoint]['p95']}ms exceeds 200ms limit"
        
        # Print results for review
        for endpoint, stats in results.items():
            print(f"\n{endpoint}:")
            print(f"  Mean: {stats['mean']:.2f}ms")
            print(f"  Median: {stats['median']:.2f}ms")
            print(f"  P95: {stats['p95']:.2f}ms")
            print(f"  Max: {stats['max']:.2f}ms")
    
    async def test_search_performance(self, client: AsyncClient, auth_headers: dict):
        """Test search endpoint performance with various query complexities."""
        queries = [
            "simple",
            "machine learning",
            "python programming best practices",
            "머신러닝",  # Korean query
            "complex query with multiple terms and filters"
        ]
        
        results = []
        
        for query in queries:
            start_time = time.time()
            response = await client.get(
                f"/api/v1/search?query={query}",
                headers=auth_headers
            )
            elapsed = (time.time() - start_time) * 1000
            
            assert response.status_code == 200
            results.append({
                "query": query,
                "time_ms": elapsed,
                "result_count": len(response.json().get("results", []))
            })
        
        # All searches should complete under 500ms
        for result in results:
            assert result["time_ms"] < 500, f"Search for '{result['query']}' took {result['time_ms']}ms"
    
    async def test_pagination_performance(self, client: AsyncClient, auth_headers: dict):
        """Test pagination performance with different page sizes."""
        page_sizes = [10, 20, 50, 100]
        
        for page_size in page_sizes:
            start_time = time.time()
            response = await client.get(
                f"/api/v1/knowledge?page=1&page_size={page_size}",
                headers=auth_headers
            )
            elapsed = (time.time() - start_time) * 1000
            
            assert response.status_code == 200
            
            # Larger page sizes should still respond quickly
            if page_size <= 50:
                assert elapsed < 200, f"Page size {page_size} took {elapsed}ms"
            else:
                assert elapsed < 500, f"Page size {page_size} took {elapsed}ms"


@pytest.mark.performance
class TestConcurrentUsers:
    """Test system performance with concurrent users."""
    
    async def test_concurrent_read_operations(self, client: AsyncClient, auth_headers: dict):
        """Test handling multiple concurrent read operations."""
        
        async def read_operation(endpoint: str):
            start_time = time.time()
            response = await client.get(endpoint, headers=auth_headers)
            elapsed = (time.time() - start_time) * 1000
            return {
                "endpoint": endpoint,
                "status": response.status_code,
                "time_ms": elapsed
            }
        
        # Simulate 100 concurrent read requests
        endpoints = [
            "/api/v1/knowledge",
            "/api/v1/categories",
            "/api/v1/auth/me",
            "/api/v1/search?query=test"
        ]
        
        tasks = []
        for _ in range(25):  # 25 iterations × 4 endpoints = 100 requests
            for endpoint in endpoints:
                tasks.append(read_operation(endpoint))
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000
        
        # Analyze results
        successful = sum(1 for r in results if r["status"] == 200)
        avg_time = statistics.mean(r["time_ms"] for r in results)
        p95_time = statistics.quantiles([r["time_ms"] for r in results], n=20)[18]
        
        # Assertions
        assert successful == 100, f"Only {successful}/100 requests succeeded"
        assert avg_time < 500, f"Average response time {avg_time}ms exceeds 500ms"
        assert p95_time < 1000, f"P95 response time {p95_time}ms exceeds 1000ms"
        assert total_time < 10000, f"Total time {total_time}ms exceeds 10 seconds"
        
        print(f"\nConcurrent Read Results:")
        print(f"  Total requests: 100")
        print(f"  Successful: {successful}")
        print(f"  Average time: {avg_time:.2f}ms")
        print(f"  P95 time: {p95_time:.2f}ms")
        print(f"  Total time: {total_time:.2f}ms")
    
    async def test_concurrent_write_operations(self, client: AsyncClient, auth_headers: dict):
        """Test handling multiple concurrent write operations."""
        
        # First create a category
        cat_response = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "Concurrent Test",
                "slug": "concurrent-test"
            }
        )
        category_id = cat_response.json()["id"]
        
        async def write_operation(index: int):
            start_time = time.time()
            response = await client.post(
                "/api/v1/knowledge",
                headers=auth_headers,
                json={
                    "title": f"Concurrent Item {index}",
                    "content": f"Content for concurrent test {index}",
                    "category_id": category_id,
                    "tags": ["concurrent", f"test{index}"],
                    "status": "draft"
                }
            )
            elapsed = (time.time() - start_time) * 1000
            return {
                "index": index,
                "status": response.status_code,
                "time_ms": elapsed
            }
        
        # Simulate 50 concurrent write requests
        tasks = [write_operation(i) for i in range(50)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000
        
        # Analyze results
        successful = sum(1 for r in results if r["status"] == 201)
        avg_time = statistics.mean(r["time_ms"] for r in results)
        
        # Assertions
        assert successful >= 45, f"Only {successful}/50 writes succeeded"
        assert avg_time < 1000, f"Average write time {avg_time}ms exceeds 1000ms"
        assert total_time < 30000, f"Total time {total_time}ms exceeds 30 seconds"
        
        print(f"\nConcurrent Write Results:")
        print(f"  Total requests: 50")
        print(f"  Successful: {successful}")
        print(f"  Average time: {avg_time:.2f}ms")
        print(f"  Total time: {total_time:.2f}ms")
    
    async def test_mixed_load_pattern(self, client: AsyncClient, auth_headers: dict):
        """Test realistic mixed load pattern (80% reads, 20% writes)."""
        
        # Create a category for writes
        cat_response = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "Mixed Load Test",
                "slug": "mixed-load-test"
            }
        )
        category_id = cat_response.json()["id"]
        
        async def mixed_operation(index: int):
            start_time = time.time()
            
            # 80% reads, 20% writes
            if index % 5 == 0:  # Write operation
                response = await client.post(
                    "/api/v1/knowledge",
                    headers=auth_headers,
                    json={
                        "title": f"Mixed Item {index}",
                        "content": f"Mixed content {index}",
                        "category_id": category_id,
                        "status": "published"
                    }
                )
                operation = "write"
            else:  # Read operation
                endpoint = random.choice([
                    "/api/v1/knowledge",
                    "/api/v1/categories",
                    "/api/v1/search?query=test"
                ])
                response = await client.get(endpoint, headers=auth_headers)
                operation = "read"
            
            elapsed = (time.time() - start_time) * 1000
            return {
                "operation": operation,
                "status": response.status_code,
                "time_ms": elapsed
            }
        
        # Simulate 100 mixed operations
        tasks = [mixed_operation(i) for i in range(100)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000
        
        # Analyze results
        reads = [r for r in results if r["operation"] == "read"]
        writes = [r for r in results if r["operation"] == "write"]
        
        read_success = sum(1 for r in reads if r["status"] == 200)
        write_success = sum(1 for r in writes if r["status"] == 201)
        
        print(f"\nMixed Load Results:")
        print(f"  Total operations: 100")
        print(f"  Reads: {len(reads)} (Success: {read_success})")
        print(f"  Writes: {len(writes)} (Success: {write_success})")
        print(f"  Total time: {total_time:.2f}ms")
        
        # Assertions
        assert read_success >= len(reads) * 0.95  # 95% read success
        assert write_success >= len(writes) * 0.90  # 90% write success


@pytest.mark.performance
@pytest.mark.memory
class TestMemoryUsage:
    """Test memory usage under various conditions."""
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    async def test_memory_baseline(self, client: AsyncClient, auth_headers: dict):
        """Test baseline memory usage."""
        initial_memory = self.get_memory_usage()
        
        # Perform some basic operations
        for _ in range(10):
            await client.get("/api/v1/knowledge", headers=auth_headers)
            await client.get("/api/v1/categories", headers=auth_headers)
        
        final_memory = self.get_memory_usage()
        memory_increase = final_memory - initial_memory
        
        print(f"\nBaseline Memory Usage:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")
        
        # Should not increase by more than 50MB for basic operations
        assert memory_increase < 50, f"Memory increased by {memory_increase:.2f} MB"
    
    async def test_memory_under_load(self, client: AsyncClient, auth_headers: dict):
        """Test memory usage under sustained load."""
        initial_memory = self.get_memory_usage()
        
        # Create a category for testing
        cat_response = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "Memory Test",
                "slug": "memory-test"
            }
        )
        category_id = cat_response.json()["id"]
        
        # Generate large content
        large_content = "x" * 10000  # 10KB of content
        
        # Create 100 items with large content
        for i in range(100):
            await client.post(
                "/api/v1/knowledge",
                headers=auth_headers,
                json={
                    "title": f"Memory Test Item {i}",
                    "content": large_content,
                    "category_id": category_id,
                    "status": "published"
                }
            )
            
            # Check memory every 10 items
            if i % 10 == 0:
                current_memory = self.get_memory_usage()
                print(f"  After {i} items: {current_memory:.2f} MB")
                
                # Ensure we're not exceeding 6GB limit
                assert current_memory < 6144, f"Memory usage {current_memory:.2f} MB exceeds 6GB limit"
        
        final_memory = self.get_memory_usage()
        memory_increase = final_memory - initial_memory
        
        print(f"\nMemory Under Load:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")
        
        # Should not exceed reasonable limits
        assert final_memory < 6144, f"Final memory {final_memory:.2f} MB exceeds 6GB limit"
    
    async def test_memory_leak_detection(self, client: AsyncClient, auth_headers: dict):
        """Test for memory leaks in repeated operations."""
        measurements = []
        
        for iteration in range(5):
            memory_before = self.get_memory_usage()
            
            # Perform 100 operations
            for _ in range(100):
                response = await client.get("/api/v1/knowledge", headers=auth_headers)
                assert response.status_code == 200
            
            # Force garbage collection
            import gc
            gc.collect()
            await asyncio.sleep(1)  # Allow cleanup
            
            memory_after = self.get_memory_usage()
            memory_diff = memory_after - memory_before
            measurements.append(memory_diff)
            
            print(f"  Iteration {iteration + 1}: {memory_diff:.2f} MB increase")
        
        # Check if memory is consistently increasing (potential leak)
        avg_increase = statistics.mean(measurements)
        
        print(f"\nMemory Leak Detection:")
        print(f"  Average increase per iteration: {avg_increase:.2f} MB")
        print(f"  Measurements: {measurements}")
        
        # Average increase should be minimal (< 5MB per iteration)
        assert avg_increase < 5, f"Potential memory leak detected: {avg_increase:.2f} MB average increase"


@pytest.mark.performance
class TestDatabasePerformance:
    """Test database query performance."""
    
    async def test_bulk_insert_performance(self, client: AsyncClient, auth_headers: dict):
        """Test bulk insert performance."""
        # Create category
        cat_response = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "Bulk Test",
                "slug": "bulk-test"
            }
        )
        category_id = cat_response.json()["id"]
        
        # Prepare bulk data
        items = []
        for i in range(100):
            items.append({
                "title": f"Bulk Item {i}",
                "content": f"Content for bulk item {i}",
                "category_id": category_id,
                "tags": [f"bulk", f"item{i}"],
                "status": "published"
            })
        
        # Measure bulk insert time
        start_time = time.time()
        
        # Simulate bulk insert (would be better with actual bulk endpoint)
        tasks = []
        for item in items:
            tasks.append(client.post("/api/v1/knowledge", headers=auth_headers, json=item))
        
        results = await asyncio.gather(*tasks)
        
        elapsed = (time.time() - start_time) * 1000
        
        successful = sum(1 for r in results if r.status_code == 201)
        
        print(f"\nBulk Insert Performance:")
        print(f"  Items: 100")
        print(f"  Successful: {successful}")
        print(f"  Total time: {elapsed:.2f}ms")
        print(f"  Per item: {elapsed/100:.2f}ms")
        
        # Should complete within reasonable time
        assert elapsed < 30000, f"Bulk insert took {elapsed}ms (> 30 seconds)"
        assert successful >= 95, f"Only {successful}/100 inserts succeeded"
    
    async def test_complex_query_performance(self, client: AsyncClient, auth_headers: dict):
        """Test performance of complex queries."""
        # Test various complex query scenarios
        queries = [
            # Filter by multiple tags
            "/api/v1/knowledge?tags=python,tutorial&status=published",
            # Date range query
            "/api/v1/knowledge?created_after=2024-01-01&created_before=2024-12-31",
            # Full-text search with filters
            "/api/v1/search?query=python&category=programming&tags=tutorial",
            # Sorting and pagination
            "/api/v1/knowledge?sort_by=created_at&order=desc&page=1&page_size=50"
        ]
        
        results = []
        for query in queries:
            start_time = time.time()
            response = await client.get(query, headers=auth_headers)
            elapsed = (time.time() - start_time) * 1000
            
            results.append({
                "query": query,
                "status": response.status_code,
                "time_ms": elapsed
            })
        
        print(f"\nComplex Query Performance:")
        for result in results:
            print(f"  {result['query'][:50]}...")
            print(f"    Status: {result['status']}, Time: {result['time_ms']:.2f}ms")
        
        # All complex queries should complete under 1 second
        for result in results:
            assert result["status"] == 200
            assert result["time_ms"] < 1000, f"Query took {result['time_ms']}ms"