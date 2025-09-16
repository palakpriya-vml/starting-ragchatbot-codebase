import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add backend directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_generator import AIGenerator

class TestAIGenerator:
    """Test suite for AIGenerator class"""

    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.api_key = "test_api_key"
        self.model = "claude-sonnet-4-20250514"

        # Mock Anthropic client to avoid actual API calls
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            self.mock_client = Mock()
            mock_anthropic.return_value = self.mock_client
            self.ai_generator = AIGenerator(self.api_key, self.model)

    def test_init(self):
        """Test AIGenerator initialization"""
        assert self.ai_generator.model == self.model
        assert self.ai_generator.base_params["model"] == self.model
        assert self.ai_generator.base_params["temperature"] == 0
        assert self.ai_generator.base_params["max_tokens"] == 800

    def test_generate_response_without_tools(self):
        """Test basic response generation without tools"""
        # Mock response from Anthropic
        mock_response = Mock()
        mock_response.content = [Mock(text="This is a test response")]
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response

        result = self.ai_generator.generate_response("What is Python?")

        # Verify API was called correctly
        self.mock_client.messages.create.assert_called_once()
        call_args = self.mock_client.messages.create.call_args

        assert call_args[1]["messages"][0]["content"] == "What is Python?"
        assert "tools" not in call_args[1]  # No tools should be passed
        assert result == "This is a test response"

    def test_generate_response_with_conversation_history(self):
        """Test response generation with conversation context"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Response with context")]
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response

        conversation_history = "User: Previous question\nAssistant: Previous answer"

        result = self.ai_generator.generate_response(
            "Follow-up question",
            conversation_history=conversation_history
        )

        # Verify system prompt includes conversation history
        call_args = self.mock_client.messages.create.call_args
        system_content = call_args[1]["system"]

        assert "Previous conversation:" in system_content
        assert conversation_history in system_content

    def test_generate_response_with_tools_no_tool_use(self):
        """Test response generation with tools available but not used"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Direct answer without tool use")]
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response

        mock_tools = [{"name": "test_tool", "description": "Test tool"}]

        result = self.ai_generator.generate_response(
            "General question",
            tools=mock_tools
        )

        # Verify tools were passed to API
        call_args = self.mock_client.messages.create.call_args
        assert call_args[1]["tools"] == mock_tools
        assert call_args[1]["tool_choice"] == {"type": "auto"}
        assert result == "Direct answer without tool use"

    def test_generate_response_with_tool_execution(self):
        """Test response generation that triggers tool execution"""
        # Mock initial response with tool use
        mock_initial_response = Mock()
        mock_tool_use_block = Mock()
        mock_tool_use_block.type = "tool_use"
        mock_tool_use_block.name = "search_course_content"
        mock_tool_use_block.id = "tool_123"
        mock_tool_use_block.input = {"query": "Python basics"}
        mock_initial_response.content = [mock_tool_use_block]
        mock_initial_response.stop_reason = "tool_use"

        # Mock final response after tool execution
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final response with tool results")]

        # Set up mock to return different responses for different calls
        self.mock_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response
        ]

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool execution result"

        mock_tools = [{"name": "search_course_content", "description": "Search tool"}]

        result = self.ai_generator.generate_response(
            "What is Python?",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="Python basics"
        )

        # Verify second API call was made with tool results
        assert self.mock_client.messages.create.call_count == 2

        # Check the second call includes tool results
        second_call_args = self.mock_client.messages.create.call_args_list[1]
        messages = second_call_args[1]["messages"]

        # Should have original user message, assistant tool use, and tool results
        assert len(messages) >= 3
        assert messages[-1]["role"] == "user"  # Tool results are sent as user message
        assert messages[-1]["content"][0]["type"] == "tool_result"
        assert messages[-1]["content"][0]["tool_use_id"] == "tool_123"
        assert messages[-1]["content"][0]["content"] == "Tool execution result"

        assert result == "Final response with tool results"

    def test_tool_execution_multiple_tools(self):
        """Test execution of multiple tools in one response"""
        # Mock response with multiple tool uses
        mock_tool_use_1 = Mock()
        mock_tool_use_1.type = "tool_use"
        mock_tool_use_1.name = "search_course_content"
        mock_tool_use_1.id = "tool_1"
        mock_tool_use_1.input = {"query": "Python"}

        mock_tool_use_2 = Mock()
        mock_tool_use_2.type = "tool_use"
        mock_tool_use_2.name = "get_course_outline"
        mock_tool_use_2.id = "tool_2"
        mock_tool_use_2.input = {"course_title": "Python Basics"}

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_use_1, mock_tool_use_2]
        mock_initial_response.stop_reason = "tool_use"

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Response using both tools")]

        self.mock_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response
        ]

        # Mock tool manager with different responses
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Search result",
            "Outline result"
        ]

        result = self.ai_generator.generate_response(
            "Tell me about Python",
            tools=[],
            tool_manager=mock_tool_manager
        )

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="Python")
        mock_tool_manager.execute_tool.assert_any_call("get_course_outline", course_title="Python Basics")

    def test_tool_execution_error_handling(self):
        """Test error handling during tool execution"""
        mock_initial_response = Mock()
        mock_tool_use_block = Mock()
        mock_tool_use_block.type = "tool_use"
        mock_tool_use_block.name = "failing_tool"
        mock_tool_use_block.id = "tool_123"
        mock_tool_use_block.input = {"query": "test"}
        mock_initial_response.content = [mock_tool_use_block]
        mock_initial_response.stop_reason = "tool_use"

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Handled tool error")]

        self.mock_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response
        ]

        # Mock tool manager that returns error
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool 'failing_tool' not found"

        result = self.ai_generator.generate_response(
            "Test query",
            tools=[],
            tool_manager=mock_tool_manager
        )

        # Verify error is passed to final response
        second_call_args = self.mock_client.messages.create.call_args_list[1]
        tool_result_content = second_call_args[1]["messages"][-1]["content"][0]["content"]
        assert tool_result_content == "Tool 'failing_tool' not found"

    def test_system_prompt_content(self):
        """Test that system prompt contains correct instructions"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response

        self.ai_generator.generate_response("Test query")

        call_args = self.mock_client.messages.create.call_args
        system_content = call_args[1]["system"]

        # Verify key instructions are in system prompt
        assert "search_course_content" in system_content
        assert "get_course_outline" in system_content
        assert "Course outline queries" in system_content
        assert "Content-specific queries" in system_content

    def test_handle_tool_execution_no_tool_results(self):
        """Test handling when no tool results are generated"""
        mock_initial_response = Mock()
        mock_initial_response.content = []  # No tool use blocks

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Response without tools")]
        self.mock_client.messages.create.return_value = mock_final_response

        result = self.ai_generator._handle_tool_execution(
            mock_initial_response,
            {"messages": [{"role": "user", "content": "test"}], "system": "test"},
            Mock()
        )

        assert result == "Response without tools"

    @patch('ai_generator.anthropic.Anthropic')
    def test_api_key_configuration(self, mock_anthropic):
        """Test that API key is properly configured"""
        test_key = "test_anthropic_key"
        AIGenerator(test_key, "test-model")

        mock_anthropic.assert_called_once_with(api_key=test_key)


class TestAIGeneratorIntegration:
    """Integration tests for AIGenerator with real-like scenarios"""

    def setup_method(self):
        """Set up integration test fixtures"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            self.mock_client = Mock()
            mock_anthropic.return_value = self.mock_client
            self.ai_generator = AIGenerator("test_key", "test_model")

    def test_realistic_search_flow(self):
        """Test realistic search tool usage flow"""
        # Simulate Claude deciding to use search tool
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.name = "search_course_content"
        mock_tool_use.id = "search_123"
        mock_tool_use.input = {
            "query": "Python variables",
            "course_name": "Python Basics"
        }

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_use]
        mock_initial_response.stop_reason = "tool_use"

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Python variables are containers for storing data...")]

        self.mock_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response
        ]

        # Mock realistic tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = """
        [Python Basics - Lesson 2]
        Variables in Python are used to store data. You can create a variable by assigning a value to a name.
        Example: x = 5
        """

        tools = [{
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "course_name": {"type": "string"}
                }
            }
        }]

        result = self.ai_generator.generate_response(
            "How do variables work in Python?",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Verify the flow worked correctly
        assert mock_tool_manager.execute_tool.called
        assert result == "Python variables are containers for storing data..."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])