import pytest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

# Add backend directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rag_system import RAGSystem
from config import Config


class TestRAGSystem:
    """End-to-end test suite for RAGSystem"""

    def setup_method(self):
        """Set up test fixtures with temporary directories"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config()
        self.config.CHROMA_PATH = os.path.join(self.temp_dir, "test_chroma")
        self.config.ANTHROPIC_API_KEY = "test_key"

        # Create mock dependencies to avoid external services
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'):

            self.rag_system = RAGSystem(self.config)

            # Setup mocks for easier testing
            self.mock_doc_processor = self.rag_system.document_processor
            self.mock_vector_store = self.rag_system.vector_store
            self.mock_ai_generator = self.rag_system.ai_generator
            self.mock_session_manager = self.rag_system.session_manager
            self.mock_tool_manager = self.rag_system.tool_manager

    def teardown_method(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_rag_system_initialization(self):
        """Test that RAG system initializes all components"""
        assert self.rag_system.document_processor is not None
        assert self.rag_system.vector_store is not None
        assert self.rag_system.ai_generator is not None
        assert self.rag_system.session_manager is not None
        assert self.rag_system.tool_manager is not None

        # Verify tools are registered
        assert len(self.rag_system.tool_manager.tools) >= 2  # Should have search and outline tools

    def test_add_course_document_success(self):
        """Test successful course document addition"""
        # Mock document processor to return course and chunks
        mock_course = Mock()
        mock_course.title = "Test Course"
        mock_chunks = [Mock(), Mock(), Mock()]  # 3 mock chunks

        self.mock_doc_processor.process_course_document.return_value = (mock_course, mock_chunks)

        # Test document addition
        course, chunk_count = self.rag_system.add_course_document("fake_path.txt")

        # Verify processing pipeline
        self.mock_doc_processor.process_course_document.assert_called_once_with("fake_path.txt")
        self.mock_vector_store.add_course_metadata.assert_called_once_with(mock_course)
        self.mock_vector_store.add_course_content.assert_called_once_with(mock_chunks)

        assert course == mock_course
        assert chunk_count == 3

    def test_add_course_document_failure(self):
        """Test handling of document processing failure"""
        # Mock document processor to raise exception
        self.mock_doc_processor.process_course_document.side_effect = Exception("Processing failed")

        course, chunk_count = self.rag_system.add_course_document("bad_file.txt")

        assert course is None
        assert chunk_count == 0

    def test_add_course_folder_success(self):
        """Test adding multiple course documents from folder"""
        # Create temporary test folder with files
        test_folder = os.path.join(self.temp_dir, "courses")
        os.makedirs(test_folder)

        # Create test files
        with open(os.path.join(test_folder, "course1.txt"), 'w') as f:
            f.write("Course 1 content")
        with open(os.path.join(test_folder, "course2.txt"), 'w') as f:
            f.write("Course 2 content")

        # Mock document processing
        mock_course1 = Mock()
        mock_course1.title = "Course 1"
        mock_course2 = Mock()
        mock_course2.title = "Course 2"

        self.mock_doc_processor.process_course_document.side_effect = [
            (mock_course1, [Mock(), Mock()]),  # 2 chunks
            (mock_course2, [Mock(), Mock(), Mock()])  # 3 chunks
        ]

        # Mock vector store to return no existing courses
        self.mock_vector_store.get_existing_course_titles.return_value = []

        courses, chunks = self.rag_system.add_course_folder(test_folder)

        assert courses == 2
        assert chunks == 5  # 2 + 3 chunks
        assert self.mock_doc_processor.process_course_document.call_count == 2

    def test_add_course_folder_skip_existing(self):
        """Test skipping existing courses when adding from folder"""
        test_folder = os.path.join(self.temp_dir, "courses")
        os.makedirs(test_folder)

        with open(os.path.join(test_folder, "existing_course.txt"), 'w') as f:
            f.write("Existing course content")

        # Mock existing course
        mock_course = Mock()
        mock_course.title = "Existing Course"
        self.mock_doc_processor.process_course_document.return_value = (mock_course, [Mock()])

        # Mock vector store to return existing course
        self.mock_vector_store.get_existing_course_titles.return_value = ["Existing Course"]

        courses, chunks = self.rag_system.add_course_folder(test_folder, clear_existing=False)

        # Should skip processing
        assert courses == 0
        assert chunks == 0
        self.mock_doc_processor.process_course_document.assert_not_called()

    def test_query_without_session(self):
        """Test query processing without existing session"""
        # Mock AI generator response
        self.mock_ai_generator.generate_response.return_value = "Test answer"

        # Mock tool manager sources
        self.mock_tool_manager.get_last_sources.return_value = [
            {"text": "Test Source", "link": "http://test.com"}
        ]

        # Mock session manager
        self.mock_session_manager.create_session.return_value = "new_session_123"
        self.mock_session_manager.get_conversation_history.return_value = None

        answer, sources = self.rag_system.query("What is Python?")

        # Verify AI generator was called correctly
        self.mock_ai_generator.generate_response.assert_called_once()
        call_args = self.mock_ai_generator.generate_response.call_args

        assert "What is Python?" in call_args[1]["query"]
        assert call_args[1]["conversation_history"] is None
        assert call_args[1]["tools"] is not None
        assert call_args[1]["tool_manager"] is not None

        # Verify response handling
        assert answer == "Test answer"
        assert len(sources) == 1
        assert sources[0]["text"] == "Test Source"

    def test_query_with_session(self):
        """Test query processing with existing session"""
        # Mock components
        self.mock_ai_generator.generate_response.return_value = "Contextual answer"
        self.mock_tool_manager.get_last_sources.return_value = []

        conversation_history = "Previous: What is programming?\nAnswer: Programming is..."
        self.mock_session_manager.get_conversation_history.return_value = conversation_history

        answer, sources = self.rag_system.query("What about Python specifically?", "session_456")

        # Verify session handling
        self.mock_session_manager.get_conversation_history.assert_called_once_with("session_456")

        # Verify AI generator got conversation context
        call_args = self.mock_ai_generator.generate_response.call_args
        assert call_args[1]["conversation_history"] == conversation_history

        # Verify session was updated
        self.mock_session_manager.add_exchange.assert_called_once_with(
            "session_456", "What about Python specifically?", "Contextual answer"
        )

    def test_query_tool_execution_flow(self):
        """Test complete query flow with tool execution"""
        # Mock a realistic tool execution scenario
        self.mock_ai_generator.generate_response.return_value = "Python is a programming language..."

        # Mock tool manager with realistic sources
        mock_sources = [
            {"text": "Python Basics - Lesson 1", "link": "http://course.com/python/lesson1"},
            {"text": "Programming Fundamentals", "link": "http://course.com/fundamentals"}
        ]
        self.mock_tool_manager.get_last_sources.return_value = mock_sources

        answer, sources = self.rag_system.query("Tell me about Python programming")

        # Verify tool manager interaction
        self.mock_tool_manager.get_tool_definitions.assert_called_once()
        self.mock_tool_manager.get_last_sources.assert_called_once()
        self.mock_tool_manager.reset_sources.assert_called_once()

        # Verify sources are returned correctly
        assert sources == mock_sources

    def test_get_course_analytics(self):
        """Test course analytics retrieval"""
        # Mock vector store analytics
        self.mock_vector_store.get_course_count.return_value = 5
        self.mock_vector_store.get_existing_course_titles.return_value = [
            "Course A", "Course B", "Course C", "Course D", "Course E"
        ]

        analytics = self.rag_system.get_course_analytics()

        assert analytics["total_courses"] == 5
        assert len(analytics["course_titles"]) == 5
        assert "Course A" in analytics["course_titles"]

    def test_query_error_handling(self):
        """Test error handling in query processing"""
        # Mock AI generator to raise exception
        self.mock_ai_generator.generate_response.side_effect = Exception("AI service unavailable")

        with pytest.raises(Exception) as exc_info:
            self.rag_system.query("Test query")

        assert "AI service unavailable" in str(exc_info.value)

    def test_tool_registration(self):
        """Test that required tools are properly registered"""
        # Get registered tools
        tool_definitions = self.rag_system.tool_manager.get_tool_definitions()
        tool_names = [tool.get("name") for tool in tool_definitions]

        # Verify required tools are present
        expected_tools = ["search_course_content", "get_course_outline"]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_session_management_integration(self):
        """Test session management integration"""
        # Test session creation
        session_id = "test_session_789"

        # Mock session manager responses
        self.mock_session_manager.get_conversation_history.return_value = None
        self.mock_ai_generator.generate_response.return_value = "Session response"
        self.mock_tool_manager.get_last_sources.return_value = []

        # First query - should create/use session
        answer1, sources1 = self.rag_system.query("First question", session_id)

        # Verify session interaction
        self.mock_session_manager.get_conversation_history.assert_called_with(session_id)
        self.mock_session_manager.add_exchange.assert_called_once_with(
            session_id, "First question", "Session response"
        )

        # Second query - should have conversation history
        conversation_history = "User: First question\nAssistant: Session response"
        self.mock_session_manager.get_conversation_history.return_value = conversation_history

        answer2, sources2 = self.rag_system.query("Follow-up question", session_id)

        # Verify history was retrieved for second query
        assert self.mock_session_manager.get_conversation_history.call_count == 2


class TestRAGSystemIntegration:
    """Integration tests that test more realistic scenarios"""

    def setup_method(self):
        """Set up integration test environment"""
        self.config = Config()
        self.config.ANTHROPIC_API_KEY = "test_integration_key"

    @patch('rag_system.AIGenerator')
    @patch('rag_system.VectorStore')
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.SessionManager')
    def test_realistic_query_flow(self, mock_session_mgr, mock_doc_proc, mock_vector_store, mock_ai_gen):
        """Test a realistic end-to-end query flow"""
        # Set up realistic mocks
        rag_system = RAGSystem(self.config)

        # Mock a realistic search scenario
        mock_search_tool = Mock()
        mock_search_tool.execute.return_value = """
        [Python Fundamentals - Lesson 2]
        Variables in Python are used to store data values. Unlike other programming languages,
        Python has no command for declaring a variable. A variable is created when you first assign a value to it.
        """

        # Mock tool manager to use our search tool
        rag_system.tool_manager.execute_tool = Mock(return_value=mock_search_tool.execute.return_value)
        rag_system.tool_manager.get_last_sources = Mock(return_value=[
            {"text": "Python Fundamentals - Lesson 2", "link": "http://course.com/python/lesson2"}
        ])

        # Mock AI to use tool and generate response
        mock_ai_response = """
        In Python, variables are containers for storing data values. You don't need to declare
        variables explicitly - they're created when you assign a value to them. For example:
        x = 5 creates a variable named x with the value 5.
        """
        rag_system.ai_generator.generate_response.return_value = mock_ai_response

        # Execute query
        answer, sources = rag_system.query("How do variables work in Python?")

        # Verify realistic behavior
        assert "variables" in answer.lower()
        assert "python" in answer.lower()
        assert len(sources) > 0
        assert sources[0]["text"] == "Python Fundamentals - Lesson 2"

    def test_error_scenarios(self):
        """Test various error scenarios"""
        # Test with invalid configuration
        invalid_config = Config()
        invalid_config.ANTHROPIC_API_KEY = ""

        with patch('rag_system.AIGenerator') as mock_ai:
            mock_ai.side_effect = Exception("Invalid API key")

            with pytest.raises(Exception):
                RAGSystem(invalid_config)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])