"""Shared fixtures for RAG chatbot tests."""

import pytest
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, MagicMock, patch

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vector_store import SearchResults
from config import Config

# API testing imports
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel



# --- SearchResults Factories ---


@pytest.fixture
def empty_search_results():
    """Factory for empty SearchResults."""

    def _factory(error: Optional[str] = None):
        return SearchResults(documents=[], metadata=[], distances=[], error=error)

    return _factory


@pytest.fixture
def valid_search_results():
    """Factory for valid SearchResults with sample data."""

    def _factory(num_results: int = 3):
        documents = [
            f"Sample content {i} about machine learning concepts."
            for i in range(num_results)
        ]
        metadata = [
            {"course_title": f"Course {i}", "lesson_number": i + 1, "chunk_index": i}
            for i in range(num_results)
        ]
        distances = [0.1 * (i + 1) for i in range(num_results)]
        return SearchResults(
            documents=documents, metadata=metadata, distances=distances, error=None
        )

    return _factory


@pytest.fixture
def error_search_results():
    """Factory for error SearchResults."""

    def _factory(error_msg: str = "Search error occurred"):
        return SearchResults.empty(error_msg)

    return _factory


# --- Mock VectorStore ---


@pytest.fixture
def mock_vector_store():
    """Mock VectorStore with configurable behavior."""
    mock = Mock()
    mock.max_results = 5
    mock.search = Mock(
        return_value=SearchResults(
            documents=["Sample document content"],
            metadata=[
                {"course_title": "Test Course", "lesson_number": 1, "chunk_index": 0}
            ],
            distances=[0.1],
            error=None,
        )
    )
    mock.get_lesson_link = Mock(return_value="https://example.com/lesson/1")
    mock.course_catalog = Mock()
    return mock


@pytest.fixture
def mock_vector_store_empty():
    """Mock VectorStore that returns empty results (simulates MAX_RESULTS=0 bug)."""
    mock = Mock()
    mock.max_results = 0
    mock.search = Mock(
        return_value=SearchResults(documents=[], metadata=[], distances=[], error=None)
    )
    mock.get_lesson_link = Mock(return_value=None)
    return mock


# --- Mock Anthropic Client ---


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    mock = Mock()
    return mock


@pytest.fixture
def mock_text_response():
    """Factory for mock text responses from Claude."""

    def _factory(text: str = "This is a test response."):
        response = Mock()
        response.stop_reason = "end_turn"
        content_block = Mock()
        content_block.type = "text"
        content_block.text = text
        response.content = [content_block]
        return response

    return _factory


@pytest.fixture
def mock_tool_use_response():
    """Factory for mock tool_use responses from Claude."""

    def _factory(
        tool_name: str = "search_course_content",
        tool_input: Dict = None,
        tool_id: str = "tool_123",
    ):
        if tool_input is None:
            tool_input = {"query": "machine learning"}

        response = Mock()
        response.stop_reason = "tool_use"

        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.name = tool_name
        tool_block.input = tool_input
        tool_block.id = tool_id

        response.content = [tool_block]
        return response

    return _factory


# --- Config Fixtures ---


@pytest.fixture
def broken_config():
    """Config with MAX_RESULTS=0 (the bug)."""
    config = Config()
    config.MAX_RESULTS = 0
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.CHROMA_PATH = "./test_chroma_db"
    return config


@pytest.fixture
def working_config():
    """Config with MAX_RESULTS=5 (correct value)."""
    config = Config()
    config.MAX_RESULTS = 5
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.CHROMA_PATH = "./test_chroma_db"
    return config


# --- API Testing Fixtures ---

@pytest.fixture
def mock_rag_system():
    """Mock RAGSystem for API testing."""
    mock = Mock()
    mock.session_manager = Mock()
    mock.session_manager.create_session = Mock(return_value="test-session-123")
    mock.query = Mock(return_value=(
        "This is a test response about machine learning.",
        [{"text": "Source 1: ML basics", "link": "https://example.com/ml"}]
    ))
    mock.get_course_analytics = Mock(return_value={
        "total_courses": 3,
        "course_titles": ["Course A", "Course B", "Course C"]
    })
    return mock


@pytest.fixture
def mock_rag_system_error():
    """Mock RAGSystem that raises exceptions."""
    mock = Mock()
    mock.session_manager = Mock()
    mock.session_manager.create_session = Mock(return_value="test-session-123")
    mock.query = Mock(side_effect=Exception("RAG system error"))
    mock.get_course_analytics = Mock(side_effect=Exception("Analytics error"))
    return mock


@pytest.fixture
def mock_rag_system_empty():
    """Mock RAGSystem that returns empty results."""
    mock = Mock()
    mock.session_manager = Mock()
    mock.session_manager.create_session = Mock(return_value="test-session-456")
    mock.query = Mock(return_value=(
        "I couldn't find relevant information.",
        []
    ))
    mock.get_course_analytics = Mock(return_value={
        "total_courses": 0,
        "course_titles": []
    })
    return mock


def create_test_app(mock_rag_system):
    """
    Create a test FastAPI app with API endpoints only (no static files).

    This avoids import issues with the main app.py which mounts static files
    that don't exist in the test environment.
    """
    from pydantic import BaseModel
    from typing import List, Optional

    app = FastAPI(title="Test Course Materials RAG System")

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class SourceItem(BaseModel):
        text: str
        link: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceItem]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"status": "ok", "message": "RAG System API"}

    return app


@pytest.fixture
def test_app(mock_rag_system):
    """Create a test FastAPI app with mocked RAG system."""
    return create_test_app(mock_rag_system)


@pytest.fixture
def test_client(test_app):
    """Create a test client for the FastAPI app."""
    return TestClient(test_app)


@pytest.fixture
def test_client_error(mock_rag_system_error):
    """Create a test client with error-raising RAG system."""
    app = create_test_app(mock_rag_system_error)
    return TestClient(app)


@pytest.fixture
def test_client_empty(mock_rag_system_empty):
    """Create a test client with empty-returning RAG system."""
    app = create_test_app(mock_rag_system_empty)
    return TestClient(app)
