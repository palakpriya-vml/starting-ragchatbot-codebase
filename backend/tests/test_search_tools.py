import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add backend directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults

class TestCourseSearchTool:
    """Test suite for CourseSearchTool"""

    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.mock_vector_store = Mock()
        self.search_tool = CourseSearchTool(self.mock_vector_store)

    def test_get_tool_definition(self):
        """Test that tool definition is properly structured"""
        definition = self.search_tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["properties"]["query"]["type"] == "string"
        assert "query" in definition["input_schema"]["required"]

    def test_execute_basic_search_success(self):
        """Test successful basic search execution"""
        # Mock successful search results
        mock_results = SearchResults(
            documents=["Sample course content about Python"],
            metadata=[{"course_title": "Python Basics", "lesson_number": 1}],
            distances=[0.5],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("Python basics")

        # Verify vector store was called correctly
        self.mock_vector_store.search.assert_called_once_with(
            query="Python basics",
            course_name=None,
            lesson_number=None
        )

        # Verify result formatting
        assert "Python Basics" in result
        assert "Sample course content about Python" in result
        assert "Lesson 1" in result

    def test_execute_with_course_filter(self):
        """Test search execution with course name filter"""
        mock_results = SearchResults(
            documents=["Advanced Python content"],
            metadata=[{"course_title": "Advanced Python", "lesson_number": 3}],
            distances=[0.3],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("functions", course_name="Advanced Python")

        self.mock_vector_store.search.assert_called_once_with(
            query="functions",
            course_name="Advanced Python",
            lesson_number=None
        )
        assert "Advanced Python" in result

    def test_execute_with_lesson_filter(self):
        """Test search execution with lesson number filter"""
        mock_results = SearchResults(
            documents=["Lesson 2 content"],
            metadata=[{"course_title": "Web Development", "lesson_number": 2}],
            distances=[0.4],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("CSS styling", lesson_number=2)

        self.mock_vector_store.search.assert_called_once_with(
            query="CSS styling",
            course_name=None,
            lesson_number=2
        )
        assert "Lesson 2" in result

    def test_execute_search_error(self):
        """Test handling of search errors"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Database connection failed"
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("test query")

        assert result == "Database connection failed"

    def test_execute_empty_results(self):
        """Test handling of empty search results"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("nonexistent topic")

        assert "No relevant content found" in result

    def test_execute_empty_results_with_filters(self):
        """Test empty results with course and lesson filters"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("test", course_name="Test Course", lesson_number=5)

        assert "No relevant content found in course 'Test Course' in lesson 5" in result

    def test_format_results_with_sources(self):
        """Test that sources are properly tracked"""
        # Mock the get_lesson_link method
        self.mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"

        mock_results = SearchResults(
            documents=["Course content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.2],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("test query")

        # Verify sources are tracked
        assert len(self.search_tool.last_sources) == 1
        source = self.search_tool.last_sources[0]
        assert source['text'] == "Test Course - Lesson 1"
        assert source['link'] == "https://example.com/lesson1"

    def test_multiple_search_results(self):
        """Test handling of multiple search results"""
        mock_results = SearchResults(
            documents=["First result", "Second result"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2}
            ],
            distances=[0.3, 0.4],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("common topic")

        assert "Course A" in result
        assert "Course B" in result
        assert "First result" in result
        assert "Second result" in result
        assert len(self.search_tool.last_sources) == 2


class TestCourseOutlineTool:
    """Test suite for CourseOutlineTool"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_vector_store = Mock()
        self.outline_tool = CourseOutlineTool(self.mock_vector_store)

    def test_get_tool_definition(self):
        """Test outline tool definition"""
        definition = self.outline_tool.get_tool_definition()

        assert definition["name"] == "get_course_outline"
        assert "course_title" in definition["input_schema"]["required"]

    @patch('json.loads')
    def test_execute_success(self, mock_json_loads):
        """Test successful course outline retrieval"""
        # Mock course name resolution
        self.mock_vector_store._resolve_course_name.return_value = "Python Fundamentals"

        # Mock course metadata
        mock_metadata = {
            'course_link': 'https://example.com/python',
            'lessons_json': '[]'  # Will be mocked by json.loads
        }
        mock_catalog_response = {
            'metadatas': [mock_metadata]
        }
        self.mock_vector_store.course_catalog.get.return_value = mock_catalog_response

        # Mock lessons data
        mock_lessons = [
            {"lesson_number": 1, "lesson_title": "Introduction to Python"},
            {"lesson_number": 2, "lesson_title": "Variables and Data Types"}
        ]
        mock_json_loads.return_value = mock_lessons

        result = self.outline_tool.execute("Python")

        assert "Python Fundamentals" in result
        assert "https://example.com/python" in result
        assert "Introduction to Python" in result
        assert "Variables and Data Types" in result
        assert "2 total" in result

    def test_execute_course_not_found(self):
        """Test handling when course is not found"""
        self.mock_vector_store._resolve_course_name.return_value = None

        result = self.outline_tool.execute("Nonexistent Course")

        assert "No course found matching 'Nonexistent Course'" in result

    def test_execute_no_outline_data(self):
        """Test handling when no outline data exists"""
        self.mock_vector_store._resolve_course_name.return_value = "Test Course"
        self.mock_vector_store.course_catalog.get.return_value = {'metadatas': [None]}

        result = self.outline_tool.execute("Test Course")

        assert "No outline data found for course 'Test Course'" in result


class TestToolManager:
    """Test suite for ToolManager"""

    def setup_method(self):
        """Set up test fixtures"""
        self.tool_manager = ToolManager()
        self.mock_tool = Mock()
        self.mock_tool.get_tool_definition.return_value = {
            "name": "test_tool",
            "description": "Test tool"
        }

    def test_register_tool(self):
        """Test tool registration"""
        self.tool_manager.register_tool(self.mock_tool)

        assert "test_tool" in self.tool_manager.tools
        assert self.tool_manager.tools["test_tool"] == self.mock_tool

    def test_get_tool_definitions(self):
        """Test getting all tool definitions"""
        self.tool_manager.register_tool(self.mock_tool)

        definitions = self.tool_manager.get_tool_definitions()

        assert len(definitions) == 1
        assert definitions[0]["name"] == "test_tool"

    def test_execute_tool(self):
        """Test tool execution"""
        self.mock_tool.execute.return_value = "Tool executed successfully"
        self.tool_manager.register_tool(self.mock_tool)

        result = self.tool_manager.execute_tool("test_tool", query="test")

        assert result == "Tool executed successfully"
        self.mock_tool.execute.assert_called_once_with(query="test")

    def test_execute_nonexistent_tool(self):
        """Test executing non-existent tool"""
        result = self.tool_manager.execute_tool("nonexistent_tool")

        assert "Tool 'nonexistent_tool' not found" in result

    def test_get_last_sources(self):
        """Test retrieving sources from tools"""
        mock_tool_with_sources = Mock()
        mock_tool_with_sources.get_tool_definition.return_value = {"name": "source_tool"}
        mock_tool_with_sources.last_sources = [{"text": "test", "link": "test.com"}]

        self.tool_manager.register_tool(mock_tool_with_sources)

        sources = self.tool_manager.get_last_sources()

        assert len(sources) == 1
        assert sources[0]["text"] == "test"

    def test_reset_sources(self):
        """Test resetting sources from all tools"""
        mock_tool_with_sources = Mock()
        mock_tool_with_sources.get_tool_definition.return_value = {"name": "source_tool"}
        mock_tool_with_sources.last_sources = [{"text": "test"}]

        self.tool_manager.register_tool(mock_tool_with_sources)
        self.tool_manager.reset_sources()

        assert mock_tool_with_sources.last_sources == []


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v"])