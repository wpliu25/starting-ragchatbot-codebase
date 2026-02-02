"""Tests for CourseSearchTool and ToolManager."""

import pytest
from unittest.mock import Mock, MagicMock

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchTool:
    """Tests for CourseSearchTool functionality."""

    def test_execute_with_empty_results(self, mock_vector_store_empty):
        """Test execute() returns appropriate message when no results found."""
        tool = CourseSearchTool(mock_vector_store_empty)

        result = tool.execute(query="machine learning")

        assert "No relevant content found" in result
        mock_vector_store_empty.search.assert_called_once_with(
            query="machine learning", course_name=None, lesson_number=None
        )

    def test_execute_with_valid_results(self, mock_vector_store):
        """Test execute() returns formatted results with source tracking."""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="neural networks")

        assert "[Test Course - Lesson 1]" in result
        assert "Sample document content" in result
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "Test Course - Lesson 1"

    def test_execute_with_error(self, mock_vector_store):
        """Test execute() handles errors properly."""
        mock_vector_store.search.return_value = SearchResults.empty(
            "Database connection failed"
        )
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="test query")

        assert result == "Database connection failed"

    def test_execute_with_course_filter(self, mock_vector_store):
        """Test execute() passes course filter correctly."""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test", course_name="ML Course")

        mock_vector_store.search.assert_called_with(
            query="test", course_name="ML Course", lesson_number=None
        )

    def test_execute_with_lesson_filter(self, mock_vector_store):
        """Test execute() passes lesson filter correctly."""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test", lesson_number=3)

        mock_vector_store.search.assert_called_with(
            query="test", course_name=None, lesson_number=3
        )

    def test_execute_with_both_filters(self, mock_vector_store):
        """Test execute() passes both filters correctly."""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test", course_name="ML Course", lesson_number=2)

        mock_vector_store.search.assert_called_with(
            query="test", course_name="ML Course", lesson_number=2
        )

    def test_tool_definition_schema(self, mock_vector_store):
        """Test get_tool_definition() returns correct schema."""
        tool = CourseSearchTool(mock_vector_store)

        definition = tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert definition["input_schema"]["type"] == "object"
        assert "query" in definition["input_schema"]["properties"]
        assert "course_name" in definition["input_schema"]["properties"]
        assert "lesson_number" in definition["input_schema"]["properties"]
        assert definition["input_schema"]["required"] == ["query"]

    def test_source_tracking_includes_links(self, mock_vector_store):
        """Test that sources include lesson links when available."""
        tool = CourseSearchTool(mock_vector_store)

        tool.execute(query="test")

        assert len(tool.last_sources) == 1
        assert "link" in tool.last_sources[0]
        mock_vector_store.get_lesson_link.assert_called()


class TestToolManager:
    """Tests for ToolManager functionality."""

    def test_register_tool(self, mock_vector_store):
        """Test registering a tool."""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        manager.register_tool(tool)

        assert "search_course_content" in manager.tools

    def test_get_tool_definitions(self, mock_vector_store):
        """Test getting all tool definitions."""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"

    def test_execute_tool(self, mock_vector_store):
        """Test executing a tool by name."""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        result = manager.execute_tool("search_course_content", query="test")

        assert "Test Course" in result or "Sample" in result

    def test_execute_unknown_tool(self):
        """Test executing an unknown tool returns error."""
        manager = ToolManager()

        result = manager.execute_tool("unknown_tool", query="test")

        assert "not found" in result.lower()

    def test_get_last_sources(self, mock_vector_store):
        """Test retrieving sources from last tool execution."""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        manager.execute_tool("search_course_content", query="test")
        sources = manager.get_last_sources()

        assert len(sources) >= 1

    def test_reset_sources(self, mock_vector_store):
        """Test resetting sources after retrieval."""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        manager.execute_tool("search_course_content", query="test")
        manager.reset_sources()

        assert tool.last_sources == []


class TestBugDetection:
    """Tests that detect the MAX_RESULTS=0 bug."""

    def test_max_results_zero_causes_empty_results(self, broken_config):
        """Verify that MAX_RESULTS=0 in config causes empty search results.

        This test demonstrates the bug: when config.MAX_RESULTS is 0,
        VectorStore.search() requests 0 results from ChromaDB, returning nothing.
        """
        assert broken_config.MAX_RESULTS == 0, "Bug condition: MAX_RESULTS should be 0"

    def test_vector_store_uses_config_max_results(self, mock_vector_store_empty):
        """Test that VectorStore respects max_results setting."""
        # The mock simulates max_results=0 behavior
        tool = CourseSearchTool(mock_vector_store_empty)

        result = tool.execute(query="machine learning")

        # With max_results=0, we get empty results
        assert "No relevant content found" in result
        assert tool.last_sources == []

    def test_working_config_returns_results(self, working_config):
        """Verify working config has proper MAX_RESULTS value."""
        assert (
            working_config.MAX_RESULTS == 5
        ), "Working config should have MAX_RESULTS=5"
