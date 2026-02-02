"""Integration tests for RAGSystem."""

import pytest
from unittest.mock import Mock, MagicMock, patch

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system import RAGSystem
from config import Config


class TestRAGSystemQuery:
    """Tests for RAGSystem.query() functionality."""

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_returns_tuple(
        self, mock_session, mock_doc_proc, mock_ai_gen, mock_vs, working_config
    ):
        """Test that query() returns (response, sources) tuple."""
        # Setup mocks
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(return_value="Test response")
        mock_ai_gen.return_value = mock_ai_instance

        mock_vs_instance = Mock()
        mock_vs_instance.search = Mock()
        mock_vs_instance.get_lesson_link = Mock(return_value=None)
        mock_vs.return_value = mock_vs_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session.return_value = mock_session_instance

        system = RAGSystem(working_config)
        result = system.query("What is machine learning?")

        assert isinstance(result, tuple)
        assert len(result) == 2
        response, sources = result
        assert isinstance(response, str)
        assert isinstance(sources, list)

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_with_session(
        self, mock_session, mock_doc_proc, mock_ai_gen, mock_vs, working_config
    ):
        """Test query with session ID for conversation context."""
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(return_value="Response with context")
        mock_ai_gen.return_value = mock_ai_instance

        mock_vs_instance = Mock()
        mock_vs.return_value = mock_vs_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(
            return_value="Previous conversation"
        )
        mock_session.return_value = mock_session_instance

        system = RAGSystem(working_config)
        system.query("Follow up question", session_id="session123")

        mock_session_instance.get_conversation_history.assert_called_with("session123")
        mock_session_instance.add_exchange.assert_called()


class TestRAGSystemSourceManagement:
    """Tests for source retrieval and reset functionality."""

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_sources_retrieved_after_query(
        self, mock_session, mock_doc_proc, mock_ai_gen, mock_vs, working_config
    ):
        """Test that sources are retrieved from tool manager after query."""
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(return_value="Response")
        mock_ai_gen.return_value = mock_ai_instance

        mock_vs_instance = Mock()
        mock_vs_instance.search = Mock()
        mock_vs_instance.get_lesson_link = Mock(return_value="http://example.com")
        mock_vs.return_value = mock_vs_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session.return_value = mock_session_instance

        system = RAGSystem(working_config)

        # Simulate tool having sources
        system.search_tool.last_sources = [
            {"text": "Test Course - Lesson 1", "link": "http://example.com"}
        ]

        response, sources = system.query("Test query")

        assert len(sources) == 1
        assert sources[0]["text"] == "Test Course - Lesson 1"

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_sources_reset_after_query(
        self, mock_session, mock_doc_proc, mock_ai_gen, mock_vs, working_config
    ):
        """Test that sources are reset after retrieval."""
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(return_value="Response")
        mock_ai_gen.return_value = mock_ai_instance

        mock_vs_instance = Mock()
        mock_vs.return_value = mock_vs_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session.return_value = mock_session_instance

        system = RAGSystem(working_config)

        # Simulate tool having sources
        system.search_tool.last_sources = [{"text": "Source", "link": None}]

        system.query("Test query")

        # Sources should be reset
        assert system.search_tool.last_sources == []


class TestRAGSystemBugPropagation:
    """Tests that verify the config bug propagates through the system."""

    def test_config_max_results_zero(self, broken_config):
        """Verify broken config has MAX_RESULTS=0."""
        assert broken_config.MAX_RESULTS == 0

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_vector_store_receives_max_results(
        self, mock_session, mock_doc_proc, mock_ai_gen, mock_vs, broken_config
    ):
        """Test that VectorStore is initialized with config's MAX_RESULTS."""
        mock_vs_instance = Mock()
        mock_vs.return_value = mock_vs_instance
        mock_ai_gen.return_value = Mock()
        mock_session.return_value = Mock()

        system = RAGSystem(broken_config)

        # VectorStore should be called with MAX_RESULTS from config
        mock_vs.assert_called_once()
        call_args = mock_vs.call_args
        # Third argument is max_results
        assert (
            call_args[0][2] == 0
        ), "VectorStore should receive MAX_RESULTS=0 from broken config"

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_working_config_passes_correct_max_results(
        self, mock_session, mock_doc_proc, mock_ai_gen, mock_vs, working_config
    ):
        """Test that working config passes correct MAX_RESULTS to VectorStore."""
        mock_vs_instance = Mock()
        mock_vs.return_value = mock_vs_instance
        mock_ai_gen.return_value = Mock()
        mock_session.return_value = Mock()

        system = RAGSystem(working_config)

        mock_vs.assert_called_once()
        call_args = mock_vs.call_args
        # Third argument is max_results
        assert (
            call_args[0][2] == 5
        ), "VectorStore should receive MAX_RESULTS=5 from working config"


class TestRAGSystemToolIntegration:
    """Tests for tool manager integration."""

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_tools_registered_on_init(
        self, mock_session, mock_doc_proc, mock_ai_gen, mock_vs, working_config
    ):
        """Test that search tools are registered during initialization."""
        mock_vs.return_value = Mock()
        mock_ai_gen.return_value = Mock()
        mock_session.return_value = Mock()

        system = RAGSystem(working_config)

        assert "search_course_content" in system.tool_manager.tools
        assert "get_course_outline" in system.tool_manager.tools

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_tools_passed_to_ai_generator(
        self, mock_session, mock_doc_proc, mock_ai_gen, mock_vs, working_config
    ):
        """Test that tool definitions are passed to AI generator."""
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(return_value="Response")
        mock_ai_gen.return_value = mock_ai_instance

        mock_vs.return_value = Mock()

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session.return_value = mock_session_instance

        system = RAGSystem(working_config)
        system.query("Test query")

        # Check that generate_response was called with tools
        call_kwargs = mock_ai_instance.generate_response.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] is not None
        assert "tool_manager" in call_kwargs
        assert call_kwargs["tool_manager"] is not None


class TestConfigBugVerification:
    """Tests to verify the config bug has been fixed."""

    def test_default_config_has_correct_max_results(self):
        """Test that the default Config has MAX_RESULTS=5 (bug fixed)."""
        from config import config

        assert (
            config.MAX_RESULTS == 5
        ), f"Expected MAX_RESULTS=5, got {config.MAX_RESULTS}. The bug may have regressed!"

    def test_config_class_default_is_five(self):
        """Test that Config class defaults MAX_RESULTS to 5."""
        fresh_config = Config()

        assert (
            fresh_config.MAX_RESULTS == 5
        ), f"Expected MAX_RESULTS=5, got {fresh_config.MAX_RESULTS}. The bug may have regressed!"
