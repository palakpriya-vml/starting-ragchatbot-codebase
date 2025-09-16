import pytest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

# Add backend directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vector_store import VectorStore, SearchResults
from document_processor import DocumentProcessor
from models import Course, Lesson, CourseChunk
from config import Config


class TestVectorStoreDataIntegrity:
    """Test actual vector store functionality and data integrity"""

    def setup_method(self):
        """Set up test environment with temporary ChromaDB"""
        self.temp_dir = tempfile.mkdtemp()
        self.chroma_path = os.path.join(self.temp_dir, "test_chroma")

        # Create vector store with test configuration
        self.vector_store = VectorStore(
            chroma_path=self.chroma_path,
            embedding_model="all-MiniLM-L6-v2",
            max_results=5
        )

    def teardown_method(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_vector_store_initialization(self):
        """Test that vector store initializes correctly"""
        assert self.vector_store.client is not None
        assert self.vector_store.course_catalog is not None
        assert self.vector_store.course_content is not None
        assert self.vector_store.max_results == 5

    def test_add_course_metadata(self):
        """Test adding course metadata to catalog"""
        # Create test course
        lessons = [
            Lesson(lesson_number=1, title="Introduction", lesson_link="http://test.com/lesson1"),
            Lesson(lesson_number=2, title="Basics", lesson_link="http://test.com/lesson2")
        ]
        course = Course(
            title="Test Course",
            instructor="Test Instructor",
            course_link="http://test.com/course",
            lessons=lessons
        )

        # Add to vector store
        self.vector_store.add_course_metadata(course)

        # Verify course was added
        existing_titles = self.vector_store.get_existing_course_titles()
        assert "Test Course" in existing_titles
        assert len(existing_titles) == 1

        # Test course count
        assert self.vector_store.get_course_count() == 1

    def test_add_course_content_chunks(self):
        """Test adding course content chunks"""
        chunks = [
            CourseChunk(
                course_title="Python Basics",
                lesson_number=1,
                chunk_index=0,
                content="This is the first chunk about Python basics."
            ),
            CourseChunk(
                course_title="Python Basics",
                lesson_number=1,
                chunk_index=1,
                content="This is the second chunk covering variables in Python."
            ),
            CourseChunk(
                course_title="Python Basics",
                lesson_number=2,
                chunk_index=2,
                content="This chunk covers functions and their usage."
            )
        ]

        # Add chunks to vector store
        self.vector_store.add_course_content(chunks)

        # Test search functionality
        results = self.vector_store.search("Python variables")

        assert not results.is_empty()
        assert len(results.documents) > 0
        assert "variables" in results.documents[0].lower()

    def test_search_functionality(self):
        """Test vector store search capabilities"""
        # Add test data first
        self._add_test_data()

        # Test basic search
        results = self.vector_store.search("Python programming")
        assert not results.is_empty()
        assert len(results.documents) > 0

        # Test search with course filter
        results = self.vector_store.search("programming", course_name="Python Course")
        assert not results.is_empty()

        # Test search with lesson filter
        results = self.vector_store.search("basics", lesson_number=1)
        assert not results.is_empty()

        # Test search with both filters
        results = self.vector_store.search("variables", course_name="Python Course", lesson_number=1)
        assert not results.is_empty()

    def test_search_with_invalid_course(self):
        """Test search behavior with non-existent course"""
        self._add_test_data()

        results = self.vector_store.search("anything", course_name="Nonexistent Course")
        assert results.error is not None
        assert "No course found matching" in results.error

    def test_course_name_resolution(self):
        """Test fuzzy course name matching"""
        self._add_test_data()

        # Test exact match
        resolved = self.vector_store._resolve_course_name("Python Course")
        assert resolved == "Python Course"

        # Test partial match
        resolved = self.vector_store._resolve_course_name("Python")
        assert resolved == "Python Course"

        # Test no match
        resolved = self.vector_store._resolve_course_name("Nonexistent")
        assert resolved is None

    def test_get_course_link(self):
        """Test retrieving course links"""
        self._add_test_data()

        course_link = self.vector_store.get_course_link("Python Course")
        assert course_link == "http://test.com/python-course"

        # Test non-existent course
        course_link = self.vector_store.get_course_link("Nonexistent Course")
        assert course_link is None

    def test_get_lesson_link(self):
        """Test retrieving lesson links"""
        self._add_test_data()

        lesson_link = self.vector_store.get_lesson_link("Python Course", 1)
        assert lesson_link == "http://test.com/lesson1"

        lesson_link = self.vector_store.get_lesson_link("Python Course", 2)
        assert lesson_link == "http://test.com/lesson2"

        # Test non-existent lesson
        lesson_link = self.vector_store.get_lesson_link("Python Course", 99)
        assert lesson_link is None

    def test_get_all_courses_metadata(self):
        """Test retrieving all courses metadata"""
        self._add_test_data()

        metadata = self.vector_store.get_all_courses_metadata()
        assert len(metadata) == 1
        assert metadata[0]["title"] == "Python Course"
        assert metadata[0]["instructor"] == "John Doe"
        assert "lessons" in metadata[0]
        assert len(metadata[0]["lessons"]) == 2

    def test_clear_all_data(self):
        """Test clearing all vector store data"""
        self._add_test_data()

        # Verify data exists
        assert self.vector_store.get_course_count() > 0

        # Clear data
        self.vector_store.clear_all_data()

        # Verify data is cleared
        assert self.vector_store.get_course_count() == 0
        assert len(self.vector_store.get_existing_course_titles()) == 0

    def _add_test_data(self):
        """Helper method to add consistent test data"""
        # Add course metadata
        lessons = [
            Lesson(lesson_number=1, title="Python Basics", lesson_link="http://test.com/lesson1"),
            Lesson(lesson_number=2, title="Advanced Python", lesson_link="http://test.com/lesson2")
        ]
        course = Course(
            title="Python Course",
            instructor="John Doe",
            course_link="http://test.com/python-course",
            lessons=lessons
        )
        self.vector_store.add_course_metadata(course)

        # Add content chunks
        chunks = [
            CourseChunk(
                course_title="Python Course",
                lesson_number=1,
                chunk_index=0,
                content="Python is a programming language that is easy to learn and powerful."
            ),
            CourseChunk(
                course_title="Python Course",
                lesson_number=1,
                chunk_index=1,
                content="Variables in Python are used to store data values and can be of different types."
            ),
            CourseChunk(
                course_title="Python Course",
                lesson_number=2,
                chunk_index=2,
                content="Functions in Python are defined using the def keyword and can accept parameters."
            )
        ]
        self.vector_store.add_course_content(chunks)


class TestDocumentProcessorIntegrity:
    """Test document processor functionality"""

    def setup_method(self):
        """Set up document processor tests"""
        self.doc_processor = DocumentProcessor(chunk_size=500, chunk_overlap=50)
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_process_course_document_structure(self):
        """Test that document processor creates correct structure"""
        # Create test document
        test_content = """Course Title: Test Programming Course
Course Link: http://example.com/course
Course Instructor: Jane Smith

Lesson 1: Introduction to Programming
Lesson Link: http://example.com/lesson1

This is the first lesson content about programming basics.
Programming is the process of creating instructions for computers.

Lesson 2: Variables and Data Types
Lesson Link: http://example.com/lesson2

This lesson covers variables and different data types in programming.
Variables are containers for storing data values.
"""
        test_file = os.path.join(self.temp_dir, "test_course.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)

        # Process document
        course, chunks = self.doc_processor.process_course_document(test_file)

        # Verify course structure
        assert course.title == "Test Programming Course"
        assert course.instructor == "Jane Smith"
        assert course.course_link == "http://example.com/course"
        assert len(course.lessons) == 2

        # Verify lessons
        assert course.lessons[0].lesson_number == 1
        assert course.lessons[0].title == "Introduction to Programming"
        assert course.lessons[0].lesson_link == "http://example.com/lesson1"

        assert course.lessons[1].lesson_number == 2
        assert course.lessons[1].title == "Variables and Data Types"
        assert course.lessons[1].lesson_link == "http://example.com/lesson2"

        # Verify chunks
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.course_title == "Test Programming Course"
            assert chunk.lesson_number in [1, 2]
            assert len(chunk.content) > 0

    def test_chunk_size_limits(self):
        """Test that chunks respect size limits"""
        # Create large test document
        large_content = """
COURSE: Large Course
INSTRUCTOR: Test Instructor
COURSE LINK: http://test.com

LESSON 1: Long Lesson
LESSON LINK: http://test.com/lesson1

""" + "This is a very long lesson content. " * 100  # Create large content

        test_file = os.path.join(self.temp_dir, "large_course.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(large_content)

        course, chunks = self.doc_processor.process_course_document(test_file)

        # Verify chunks are properly sized
        for chunk in chunks:
            # Allow some flexibility due to overlap and word boundaries
            assert len(chunk.content) <= self.doc_processor.chunk_size + 100


class TestRealDataIntegration:
    """Test with actual course files if they exist"""

    def setup_method(self):
        """Set up for real data tests"""
        self.docs_path = "/home/palakpriya/Claude Code/my-python-project/starting-ragchatbot-codebase/docs"
        self.temp_dir = tempfile.mkdtemp()

        if os.path.exists(self.docs_path):
            self.vector_store = VectorStore(
                chroma_path=os.path.join(self.temp_dir, "real_test_chroma"),
                embedding_model="all-MiniLM-L6-v2",
                max_results=5
            )
            self.doc_processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    def teardown_method(self):
        """Clean up"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_real_course_loading(self):
        """Test loading actual course files"""
        if not os.path.exists(self.docs_path):
            pytest.skip("Course docs directory not found")

        course_files = [f for f in os.listdir(self.docs_path) if f.endswith('.txt')]
        if not course_files:
            pytest.skip("No course files found in docs directory")

        # Process first course file
        test_file = os.path.join(self.docs_path, course_files[0])

        try:
            course, chunks = self.doc_processor.process_course_document(test_file)

            # Verify course was processed
            assert course is not None
            assert course.title != ""
            assert len(course.lessons) > 0
            assert len(chunks) > 0

            # Add to vector store
            self.vector_store.add_course_metadata(course)
            self.vector_store.add_course_content(chunks)

            # Test search with real data
            results = self.vector_store.search("programming")
            assert not results.is_empty()

        except Exception as e:
            pytest.fail(f"Failed to process real course file: {str(e)}")

    def test_all_courses_processing(self):
        """Test processing all available course files"""
        if not os.path.exists(self.docs_path):
            pytest.skip("Course docs directory not found")

        course_files = [f for f in os.listdir(self.docs_path) if f.endswith('.txt')]
        if not course_files:
            pytest.skip("No course files found")

        processed_courses = 0
        total_chunks = 0

        for filename in course_files:
            filepath = os.path.join(self.docs_path, filename)
            try:
                course, chunks = self.doc_processor.process_course_document(filepath)
                if course and chunks:
                    self.vector_store.add_course_metadata(course)
                    self.vector_store.add_course_content(chunks)
                    processed_courses += 1
                    total_chunks += len(chunks)
            except Exception as e:
                print(f"Failed to process {filename}: {str(e)}")

        # Verify processing results
        assert processed_courses > 0, "No courses were successfully processed"
        assert total_chunks > 0, "No chunks were created"
        assert self.vector_store.get_course_count() == processed_courses

        print(f"Successfully processed {processed_courses} courses with {total_chunks} total chunks")


class TestDataConsistencyChecks:
    """Tests to verify data consistency and integrity"""

    def setup_method(self):
        """Set up consistency test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.vector_store = VectorStore(
            chroma_path=os.path.join(self.temp_dir, "consistency_test"),
            embedding_model="all-MiniLM-L6-v2",
            max_results=10
        )

    def teardown_method(self):
        """Clean up"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_metadata_chunk_consistency(self):
        """Test that course metadata matches content chunks"""
        # Add course with specific lessons
        lessons = [
            Lesson(lesson_number=1, title="Lesson 1", lesson_link="http://test.com/l1"),
            Lesson(lesson_number=2, title="Lesson 2", lesson_link="http://test.com/l2")
        ]
        course = Course(
            title="Consistency Test Course",
            instructor="Test",
            course_link="http://test.com/course",
            lessons=lessons
        )
        self.vector_store.add_course_metadata(course)

        # Add chunks for these lessons
        chunks = [
            CourseChunk(course_title="Consistency Test Course", lesson_number=1, chunk_index=0, content="Lesson 1 content"),
            CourseChunk(course_title="Consistency Test Course", lesson_number=1, chunk_index=1, content="More lesson 1 content"),
            CourseChunk(course_title="Consistency Test Course", lesson_number=2, chunk_index=2, content="Lesson 2 content"),
            CourseChunk(course_title="Consistency Test Course", lesson_number=3, chunk_index=3, content="Lesson 3 content")  # No metadata for lesson 3
        ]
        self.vector_store.add_course_content(chunks)

        # Search for content and verify metadata consistency
        results = self.vector_store.search("content", course_name="Consistency Test Course")

        for doc, metadata in zip(results.documents, results.metadata):
            course_title = metadata.get("course_title")
            lesson_number = metadata.get("lesson_number")

            assert course_title == "Consistency Test Course"
            assert lesson_number in [1, 2, 3]  # Should have valid lesson numbers

    def test_search_result_quality(self):
        """Test that search results are relevant and properly ranked"""
        # Add diverse content
        chunks = [
            CourseChunk(course_title="Test Course", lesson_number=1, chunk_index=0, content="Python programming is powerful and easy to learn"),
            CourseChunk(course_title="Test Course", lesson_number=1, chunk_index=1, content="Java is a robust object-oriented programming language"),
            CourseChunk(course_title="Test Course", lesson_number=2, chunk_index=2, content="Data structures are fundamental to programming"),
            CourseChunk(course_title="Test Course", lesson_number=2, chunk_index=3, content="Algorithms help solve computational problems efficiently")
        ]

        self.vector_store.add_course_content(chunks)

        # Test targeted search
        results = self.vector_store.search("Python programming")

        # First result should be most relevant
        assert "Python" in results.documents[0]

        # Test different search
        results = self.vector_store.search("data structures")
        assert "Data structures" in results.documents[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])