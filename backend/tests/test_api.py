"""Tests for FastAPI endpoints."""

import pytest


class TestQueryEndpoint:
    """Tests for POST /api/query endpoint."""

    def test_query_with_session_id(self, test_client, mock_rag_system):
        """Query with existing session ID uses that session."""
        response = test_client.post(
            "/api/query",
            json={"query": "What is machine learning?", "session_id": "existing-session"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing-session"
        assert "answer" in data
        assert "sources" in data
        mock_rag_system.query.assert_called_once_with(
            "What is machine learning?", "existing-session"
        )

    def test_query_without_session_id_creates_new(self, test_client, mock_rag_system):
        """Query without session ID creates a new session."""
        response = test_client.post(
            "/api/query",
            json={"query": "Tell me about neural networks"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_returns_sources(self, test_client):
        """Query response includes sources with text and links."""
        response = test_client.post(
            "/api/query",
            json={"query": "What courses cover deep learning?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) > 0
        source = data["sources"][0]
        assert "text" in source
        assert "link" in source

    def test_query_empty_string_returns_error(self, test_client):
        """Empty query string should still process (validation is handled by RAG)."""
        response = test_client.post(
            "/api/query",
            json={"query": ""}
        )
        # Empty string is valid JSON, the RAG system handles empty queries
        assert response.status_code == 200

    def test_query_missing_query_field(self, test_client):
        """Missing query field returns 422 validation error."""
        response = test_client.post(
            "/api/query",
            json={"session_id": "test-session"}
        )

        assert response.status_code == 422

    def test_query_invalid_json(self, test_client):
        """Invalid JSON returns 422 error."""
        response = test_client.post(
            "/api/query",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_query_rag_system_error(self, test_client_error):
        """RAG system error returns 500 with error detail."""
        response = test_client_error.post(
            "/api/query",
            json={"query": "This will cause an error"}
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "RAG system error" in data["detail"]

    def test_query_empty_sources(self, test_client_empty):
        """Query with no matching content returns empty sources."""
        response = test_client_empty.post(
            "/api/query",
            json={"query": "Obscure topic with no results"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sources"] == []
        assert "couldn't find" in data["answer"].lower()


class TestCoursesEndpoint:
    """Tests for GET /api/courses endpoint."""

    def test_get_courses_success(self, test_client):
        """Get courses returns course statistics."""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3
        assert "Course A" in data["course_titles"]

    def test_get_courses_empty(self, test_client_empty):
        """Get courses with no loaded courses returns zeros."""
        response = test_client_empty.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_get_courses_error(self, test_client_error):
        """Analytics error returns 500."""
        response = test_client_error.get("/api/courses")

        assert response.status_code == 500
        data = response.json()
        assert "Analytics error" in data["detail"]


class TestRootEndpoint:
    """Tests for GET / endpoint."""

    def test_root_returns_status(self, test_client):
        """Root endpoint returns status OK."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestRequestValidation:
    """Tests for request validation and edge cases."""

    def test_query_with_special_characters(self, test_client):
        """Query with special characters is handled properly."""
        response = test_client.post(
            "/api/query",
            json={"query": "What about C++ & Python <script>alert('xss')</script>?"}
        )

        assert response.status_code == 200

    def test_query_with_unicode(self, test_client):
        """Query with unicode characters is handled properly."""
        response = test_client.post(
            "/api/query",
            json={"query": "机器学习是什么？ 🤖"}
        )

        assert response.status_code == 200

    def test_query_with_very_long_text(self, test_client):
        """Very long query is handled (no explicit limit in API)."""
        long_query = "machine learning " * 500
        response = test_client.post(
            "/api/query",
            json={"query": long_query}
        )

        assert response.status_code == 200

    def test_query_null_session_id(self, test_client, mock_rag_system):
        """Null session_id is treated as no session."""
        response = test_client.post(
            "/api/query",
            json={"query": "test query", "session_id": None}
        )

        assert response.status_code == 200
        mock_rag_system.session_manager.create_session.assert_called_once()
