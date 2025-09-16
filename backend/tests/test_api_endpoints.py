import pytest
import json
from fastapi import status
from unittest.mock import Mock, patch


@pytest.mark.api
class TestQueryEndpoint:
    """Test suite for /api/query endpoint"""

    def test_query_with_session_id(self, client, sample_query_data, mock_sources):
        """Test query endpoint with provided session ID"""
        response = client.post(
            "/api/query",
            json=sample_query_data["valid_query"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == sample_query_data["valid_query"]["session_id"]
        assert isinstance(data["sources"], list)
        assert data["answer"] == "This is a test answer"

    def test_query_without_session_id(self, client, sample_query_data):
        """Test query endpoint without session ID (should create new session)"""
        response = client.post(
            "/api/query",
            json=sample_query_data["query_without_session"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] is not None
        assert len(data["session_id"]) > 0

    def test_query_with_empty_query(self, client, sample_query_data):
        """Test query endpoint with empty query string"""
        response = client.post(
            "/api/query",
            json=sample_query_data["empty_query"]
        )

        # Should still return 200 as the RAG system handles empty queries
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

    def test_query_with_invalid_json(self, client):
        """Test query endpoint with malformed JSON"""
        response = client.post(
            "/api/query",
            data="invalid json"
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_missing_required_field(self, client):
        """Test query endpoint missing required query field"""
        response = client.post(
            "/api/query",
            json={"session_id": "test-session"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_rag_system_exception(self, client, mock_rag_system):
        """Test query endpoint when RAG system raises exception"""
        # Mock the RAG system to raise an exception
        mock_rag_system.query.side_effect = Exception("RAG system error")

        response = client.post(
            "/api/query",
            json={"query": "test query"}
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "RAG system error" in response.json()["detail"]

    def test_query_response_schema(self, client, sample_query_data):
        """Test that query response matches expected schema"""
        response = client.post(
            "/api/query",
            json=sample_query_data["valid_query"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response schema
        required_fields = ["answer", "sources", "session_id"]
        for field in required_fields:
            assert field in data

        # Verify types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Verify sources structure if present
        if data["sources"]:
            for source in data["sources"]:
                assert isinstance(source, dict)


@pytest.mark.api
class TestCoursesEndpoint:
    """Test suite for /api/courses endpoint"""

    def test_get_course_stats_success(self, client):
        """Test successful retrieval of course statistics"""
        response = client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "total_courses" in data
        assert "course_titles" in data
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3

    def test_get_course_stats_response_schema(self, client):
        """Test that course stats response matches expected schema"""
        response = client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify required fields
        required_fields = ["total_courses", "course_titles"]
        for field in required_fields:
            assert field in data

        # Verify types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # Verify course titles are strings
        for title in data["course_titles"]:
            assert isinstance(title, str)

    def test_get_course_stats_rag_system_exception(self, client, mock_rag_system):
        """Test courses endpoint when RAG system raises exception"""
        # Mock the RAG system to raise an exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")

        response = client.get("/api/courses")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Analytics error" in response.json()["detail"]


@pytest.mark.api
class TestSessionManagementEndpoint:
    """Test suite for session management endpoints"""

    def test_clear_session_success(self, client):
        """Test successful session clearing"""
        session_id = "test-session-123"
        response = client.delete(f"/api/sessions/{session_id}/clear")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "message" in data
        assert "session_id" in data
        assert data["session_id"] == session_id
        assert "cleared successfully" in data["message"]

    def test_clear_session_with_special_characters(self, client):
        """Test session clearing with special characters in session ID"""
        session_id = "test-session-123!@#$%"
        response = client.delete(f"/api/sessions/{session_id}/clear")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == session_id

    def test_clear_session_rag_system_exception(self, client, mock_rag_system):
        """Test session clearing when RAG system raises exception"""
        # Mock the session manager to raise an exception
        mock_rag_system.session_manager.clear_session.side_effect = Exception("Session error")

        response = client.delete("/api/sessions/test-session/clear")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Session error" in response.json()["detail"]

    def test_clear_empty_session_id(self, client):
        """Test session clearing with empty session ID"""
        response = client.delete("/api/sessions//clear")

        # FastAPI should handle this as a 404 or similar routing error
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]


@pytest.mark.api
class TestRootEndpoint:
    """Test suite for root endpoint"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns welcome message"""
        response = client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "message" in data
        assert "API" in data["message"]


@pytest.mark.api
class TestCORSHeaders:
    """Test suite for CORS headers"""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses"""
        response = client.get("/", headers={"Origin": "http://localhost:3000"})

        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers

    def test_preflight_request(self, client):
        """Test CORS preflight request"""
        response = client.options(
            "/api/query",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]


@pytest.mark.api
class TestErrorHandling:
    """Test suite for error handling across endpoints"""

    def test_method_not_allowed(self, client):
        """Test method not allowed responses"""
        # Test wrong HTTP method on endpoints
        response = client.get("/api/query")  # Should be POST
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        response = client.post("/api/courses")  # Should be GET
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_not_found_endpoint(self, client):
        """Test 404 for non-existent endpoints"""
        response = client.get("/api/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_large_payload_handling(self, client):
        """Test handling of large payloads"""
        large_query = "x" * 10000  # 10KB query
        response = client.post(
            "/api/query",
            json={"query": large_query}
        )

        # Should handle large queries gracefully
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE]


@pytest.mark.api
@pytest.mark.slow
class TestConcurrentRequests:
    """Test suite for concurrent request handling"""

    def test_concurrent_queries(self, client):
        """Test multiple concurrent queries to the same endpoint"""
        import threading
        import time

        results = []

        def make_request():
            response = client.post(
                "/api/query",
                json={"query": f"Test query at {time.time()}"}
            )
            results.append(response.status_code)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert all(status_code == status.HTTP_200_OK for status_code in results)
        assert len(results) == 5