"""Tests for AIGenerator tool calling functionality."""

import pytest
from unittest.mock import Mock, MagicMock, patch

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator
from search_tools import ToolManager, CourseSearchTool


class TestAIGeneratorNonToolResponses:
    """Tests for non-tool responses from AIGenerator."""

    def test_simple_text_response(self, mock_text_response):
        """Test handling of simple text responses without tool use."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_text_response(
                "Hello, how can I help?"
            )
            mock_anthropic.return_value = mock_client

            generator = AIGenerator(api_key="test-key", model="test-model")
            response = generator.generate_response(query="Hello")

            assert response == "Hello, how can I help?"
            mock_client.messages.create.assert_called_once()

    def test_response_without_tools(self, mock_text_response):
        """Test response generation when no tools are provided."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_text_response(
                "General knowledge answer"
            )
            mock_anthropic.return_value = mock_client

            generator = AIGenerator(api_key="test-key", model="test-model")
            response = generator.generate_response(
                query="What is Python?", tools=None, tool_manager=None
            )

            assert response == "General knowledge answer"
            # Verify tools parameter not in API call
            call_kwargs = mock_client.messages.create.call_args[1]
            assert "tools" not in call_kwargs


class TestAIGeneratorToolUse:
    """Tests for tool use detection and execution."""

    def test_tool_use_detection(self, mock_tool_use_response, mock_text_response):
        """Test that tool_use stop_reason triggers tool execution."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            # First call returns tool_use, second returns text
            mock_client.messages.create.side_effect = [
                mock_tool_use_response(),
                mock_text_response(
                    "Based on the search results, machine learning is..."
                ),
            ]
            mock_anthropic.return_value = mock_client

            # Set up tool manager
            mock_store = Mock()
            mock_store.search = Mock(
                return_value=Mock(
                    documents=["ML content"],
                    metadata=[{"course_title": "ML Course", "lesson_number": 1}],
                    error=None,
                    is_empty=Mock(return_value=False),
                )
            )
            mock_store.get_lesson_link = Mock(return_value=None)

            tool_manager = ToolManager()
            tool = CourseSearchTool(mock_store)
            tool_manager.register_tool(tool)

            generator = AIGenerator(api_key="test-key", model="test-model")
            response = generator.generate_response(
                query="What is machine learning?",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager,
            )

            # Should have made two API calls
            assert mock_client.messages.create.call_count == 2
            assert "machine learning" in response

    def test_tool_manager_execute_called(
        self, mock_tool_use_response, mock_text_response
    ):
        """Test that tool_manager.execute_tool() is called with correct parameters."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = [
                mock_tool_use_response(
                    tool_name="search_course_content",
                    tool_input={
                        "query": "neural networks",
                        "course_name": "Deep Learning",
                    },
                ),
                mock_text_response("Neural networks are..."),
            ]
            mock_anthropic.return_value = mock_client

            tool_manager = Mock()
            tool_manager.execute_tool = Mock(
                return_value="Search results about neural networks"
            )
            tool_manager.get_tool_definitions = Mock(return_value=[])

            generator = AIGenerator(api_key="test-key", model="test-model")
            generator.generate_response(
                query="Tell me about neural networks",
                tools=[],
                tool_manager=tool_manager,
            )

            tool_manager.execute_tool.assert_called_once_with(
                "search_course_content",
                query="neural networks",
                course_name="Deep Learning",
            )


class TestAIGeneratorMessageSequence:
    """Tests for message sequence building in _handle_tool_execution()."""

    def test_message_sequence_structure(
        self, mock_tool_use_response, mock_text_response
    ):
        """Test that message sequence is built correctly for tool results."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            tool_response = mock_tool_use_response(tool_id="toolu_123")
            mock_client.messages.create.side_effect = [
                tool_response,
                mock_text_response("Final answer"),
            ]
            mock_anthropic.return_value = mock_client

            tool_manager = Mock()
            tool_manager.execute_tool = Mock(return_value="Tool result content")

            generator = AIGenerator(api_key="test-key", model="test-model")
            generator.generate_response(
                query="Test query", tools=[], tool_manager=tool_manager
            )

            # Check the second API call's message structure
            second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
            messages = second_call_kwargs["messages"]

            # Should have: user query, assistant tool_use, user tool_result
            assert len(messages) == 3
            assert messages[0]["role"] == "user"
            assert messages[1]["role"] == "assistant"
            assert messages[2]["role"] == "user"

            # Check tool result structure
            tool_results = messages[2]["content"]
            assert len(tool_results) == 1
            assert tool_results[0]["type"] == "tool_result"
            assert tool_results[0]["tool_use_id"] == "toolu_123"
            assert tool_results[0]["content"] == "Tool result content"


class TestAIGeneratorEmptyToolResults:
    """Tests for handling empty tool results (bug symptom)."""

    def test_empty_tool_result_handling(
        self, mock_tool_use_response, mock_text_response
    ):
        """Test handling when tool returns empty/no results (bug symptom).

        When MAX_RESULTS=0, the search tool returns "No relevant content found".
        This test verifies the AI generator still processes this case.
        """
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = [
                mock_tool_use_response(),
                mock_text_response("I couldn't find relevant information."),
            ]
            mock_anthropic.return_value = mock_client

            tool_manager = Mock()
            # Simulate the bug: tool returns "No relevant content found"
            tool_manager.execute_tool = Mock(return_value="No relevant content found.")

            generator = AIGenerator(api_key="test-key", model="test-model")
            response = generator.generate_response(
                query="What is machine learning?", tools=[], tool_manager=tool_manager
            )

            # The response should still be generated
            assert response == "I couldn't find relevant information."

    def test_tool_result_passed_to_final_call(
        self, mock_tool_use_response, mock_text_response
    ):
        """Test that tool results are correctly passed to the final API call."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = [
                mock_tool_use_response(),
                mock_text_response("Answer based on tool results"),
            ]
            mock_anthropic.return_value = mock_client

            tool_manager = Mock()
            tool_manager.execute_tool = Mock(return_value="Actual search content here")

            generator = AIGenerator(api_key="test-key", model="test-model")
            generator.generate_response(
                query="Test", tools=[], tool_manager=tool_manager
            )

            # Verify tool result content is in the messages
            second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
            messages = second_call_kwargs["messages"]
            tool_result_content = messages[2]["content"][0]["content"]

            assert tool_result_content == "Actual search content here"


class TestAIGeneratorConversationHistory:
    """Tests for conversation history handling."""

    def test_conversation_history_included(self, mock_text_response):
        """Test that conversation history is included in system prompt."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_text_response("Response")
            mock_anthropic.return_value = mock_client

            generator = AIGenerator(api_key="test-key", model="test-model")
            generator.generate_response(
                query="Follow up question",
                conversation_history="User: What is ML?\nAssistant: ML is...",
            )

            call_kwargs = mock_client.messages.create.call_args[1]
            assert "Previous conversation" in call_kwargs["system"]
            assert "What is ML?" in call_kwargs["system"]


class TestAIGeneratorSequentialToolCalling:
    """Tests for sequential tool calling functionality."""

    def test_two_sequential_tool_calls(
        self, mock_tool_use_response, mock_text_response
    ):
        """Test that two sequential tool calls are handled correctly."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            # First call: tool_use (get_course_outline)
            # Second call: tool_use (search_course_content)
            # Third call: text response
            mock_client.messages.create.side_effect = [
                mock_tool_use_response(
                    tool_name="get_course_outline",
                    tool_input={"course_title": "Machine Learning Course"},
                    tool_id="toolu_1",
                ),
                mock_tool_use_response(
                    tool_name="search_course_content",
                    tool_input={"query": "neural networks"},
                    tool_id="toolu_2",
                ),
                mock_text_response(
                    "Final answer combining course outline and search results"
                ),
            ]
            mock_anthropic.return_value = mock_client

            tool_manager = Mock()
            tool_manager.execute_tool = Mock(
                side_effect=[
                    "Course outline: Lesson 1, Lesson 2, Lesson 3",
                    "Neural network content from lesson 2",
                ]
            )

            generator = AIGenerator(api_key="test-key", model="test-model")
            response = generator.generate_response(
                query="What topics are covered in the ML course about neural networks?",
                tools=[
                    {"name": "get_course_outline"},
                    {"name": "search_course_content"},
                ],
                tool_manager=tool_manager,
            )

            # Should have made 3 API calls (initial + 2 tool rounds)
            assert mock_client.messages.create.call_count == 3
            # Tool manager should have been called twice
            assert tool_manager.execute_tool.call_count == 2
            # Final response should be returned
            assert "Final answer" in response

    def test_tools_included_in_follow_up_calls(
        self, mock_tool_use_response, mock_text_response
    ):
        """Test that tools are included in follow-up API calls (not stripped)."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = [
                mock_tool_use_response(tool_id="toolu_1"),
                mock_text_response("Response after tool use"),
            ]
            mock_anthropic.return_value = mock_client

            tool_manager = Mock()
            tool_manager.execute_tool = Mock(return_value="Tool result")

            tools_definition = [
                {"name": "search_course_content", "description": "Search"}
            ]
            generator = AIGenerator(api_key="test-key", model="test-model")
            generator.generate_response(
                query="Test query", tools=tools_definition, tool_manager=tool_manager
            )

            # Check the second API call includes tools
            second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
            assert "tools" in second_call_kwargs
            assert second_call_kwargs["tools"] == tools_definition
            assert second_call_kwargs["tool_choice"] == {"type": "auto"}

    def test_max_rounds_limit(self, mock_tool_use_response, mock_text_response):
        """Test that loop exits after MAX_ROUNDS (2) even if Claude keeps requesting tools."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            # Claude keeps requesting tools indefinitely
            mock_client.messages.create.side_effect = [
                mock_tool_use_response(tool_id="toolu_1"),
                mock_tool_use_response(tool_id="toolu_2"),
                mock_tool_use_response(
                    tool_id="toolu_3"
                ),  # Would be 3rd round, but won't be reached
            ]
            mock_anthropic.return_value = mock_client

            tool_manager = Mock()
            tool_manager.execute_tool = Mock(return_value="Tool result")

            generator = AIGenerator(api_key="test-key", model="test-model")
            # Should not raise, should return after 2 rounds
            response = generator.generate_response(
                query="Test query", tools=[], tool_manager=tool_manager
            )

            # Should have made exactly 3 API calls (initial + 2 rounds)
            assert mock_client.messages.create.call_count == 3
            # Tool manager should have been called twice (once per round)
            assert tool_manager.execute_tool.call_count == 2

    def test_tool_execution_error_handling(
        self, mock_tool_use_response, mock_text_response
    ):
        """Test that tool execution errors are handled gracefully."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = [
                mock_tool_use_response(tool_id="toolu_1"),
                mock_text_response("I encountered an error with the tool"),
            ]
            mock_anthropic.return_value = mock_client

            tool_manager = Mock()
            tool_manager.execute_tool = Mock(
                side_effect=Exception("Database connection failed")
            )

            generator = AIGenerator(api_key="test-key", model="test-model")
            response = generator.generate_response(
                query="Test query", tools=[], tool_manager=tool_manager
            )

            # Should still return a response
            assert "error" in response.lower()

            # Verify error was passed in tool result
            second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
            messages = second_call_kwargs["messages"]
            tool_result = messages[2]["content"][0]
            assert tool_result["is_error"] is True
            assert "Database connection failed" in tool_result["content"]

    def test_early_exit_on_non_tool_response(
        self, mock_tool_use_response, mock_text_response
    ):
        """Test that loop exits early when Claude responds without tool_use."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            # First round: tool_use, then Claude responds with text (no more tools needed)
            mock_client.messages.create.side_effect = [
                mock_tool_use_response(tool_id="toolu_1"),
                mock_text_response("Answer after single tool use"),
            ]
            mock_anthropic.return_value = mock_client

            tool_manager = Mock()
            tool_manager.execute_tool = Mock(return_value="Tool result")

            generator = AIGenerator(api_key="test-key", model="test-model")
            response = generator.generate_response(
                query="Test query", tools=[], tool_manager=tool_manager
            )

            # Should have made exactly 2 API calls
            assert mock_client.messages.create.call_count == 2
            assert response == "Answer after single tool use"

    def test_message_accumulation_across_rounds(
        self, mock_tool_use_response, mock_text_response
    ):
        """Test that messages accumulate correctly across multiple rounds."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = [
                mock_tool_use_response(
                    tool_name="get_course_outline",
                    tool_input={"course_title": "Course A"},
                    tool_id="toolu_1",
                ),
                mock_tool_use_response(
                    tool_name="search_course_content",
                    tool_input={"query": "topic B"},
                    tool_id="toolu_2",
                ),
                mock_text_response("Final combined answer"),
            ]
            mock_anthropic.return_value = mock_client

            tool_manager = Mock()
            tool_manager.execute_tool = Mock(
                side_effect=["Outline result", "Search result"]
            )

            generator = AIGenerator(api_key="test-key", model="test-model")
            generator.generate_response(
                query="Original query", tools=[], tool_manager=tool_manager
            )

            # Check third API call has full message history
            third_call_kwargs = mock_client.messages.create.call_args_list[2][1]
            messages = third_call_kwargs["messages"]

            # Should have: user query, assistant tool_use_1, user tool_result_1,
            #              assistant tool_use_2, user tool_result_2
            assert len(messages) == 5
            assert messages[0]["role"] == "user"  # Original query
            assert messages[1]["role"] == "assistant"  # First tool_use
            assert messages[2]["role"] == "user"  # First tool_result
            assert messages[3]["role"] == "assistant"  # Second tool_use
            assert messages[4]["role"] == "user"  # Second tool_result


class TestAIGeneratorExtractTextResponse:
    """Tests for _extract_text_response helper method."""

    def test_extract_text_from_response(self, mock_text_response):
        """Test extracting text from a normal response."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = Mock()
            generator = AIGenerator(api_key="test-key", model="test-model")

            response = mock_text_response("Expected text content")
            result = generator._extract_text_response(response)

            assert result == "Expected text content"

    def test_extract_text_returns_empty_for_no_text(self):
        """Test that empty string is returned when no text block exists."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = Mock()
            generator = AIGenerator(api_key="test-key", model="test-model")

            # Response with only tool_use, no text
            response = Mock()
            tool_block = Mock()
            tool_block.type = "tool_use"
            # No 'text' attribute
            del tool_block.text
            response.content = [tool_block]

            result = generator._extract_text_response(response)

            assert result == ""
