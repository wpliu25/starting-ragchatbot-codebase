"""Shared fixtures for RAG chatbot tests."""

import pytest
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, MagicMock

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vector_store import SearchResults
from config import Config

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
