import pytest
import tempfile
import shutil
import os
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys

# Add backend directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Config
from rag_system import RAGSystem


# Pydantic models (duplicated from app.py to avoid import issues)
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    session_id: str

class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_config(temp_dir):
    """Create a mock configuration for testing"""
    config = Config()
    config.CHROMA_PATH = os.path.join(temp_dir, "test_chroma")
    config.ANTHROPIC_API_KEY = "test_key"
    return config


@pytest.fixture
def mock_rag_system(mock_config):
    """Create a mock RAG system with all dependencies mocked"""
    with patch('rag_system.DocumentProcessor') as mock_doc_processor, \
         patch('rag_system.VectorStore') as mock_vector_store, \
         patch('rag_system.AIGenerator') as mock_ai_generator, \
         patch('rag_system.SessionManager') as mock_session_manager:

        rag_system = RAGSystem(mock_config)

        # Setup mock behaviors
        mock_session_manager.return_value.create_session.return_value = "test-session-123"
        mock_session_manager.return_value.clear_session.return_value = None

        rag_system.query = Mock(return_value=(
            "This is a test answer",
            [{"source": "test_doc.pdf", "page": 1, "content": "test content"}]
        ))

        rag_system.get_course_analytics = Mock(return_value={
            "total_courses": 3,
            "course_titles": ["Course 1", "Course 2", "Course 3"]
        })

        rag_system.add_course_folder = Mock(return_value=(3, 150))

        yield rag_system


@pytest.fixture
def test_app(mock_rag_system):
    """Create a FastAPI test app without static file mounting"""
    app = FastAPI(title="Course Materials RAG System Test", root_path="")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Define endpoints inline to avoid import issues
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        from fastapi import HTTPException
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
        from fastapi import HTTPException
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/sessions/{session_id}/clear")
    async def clear_session(session_id: str):
        from fastapi import HTTPException
        try:
            mock_rag_system.session_manager.clear_session(session_id)
            return {"message": "Session cleared successfully", "session_id": session_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"message": "Course Materials RAG System API"}

    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the FastAPI app"""
    return TestClient(test_app)


@pytest.fixture
def sample_query_data():
    """Sample query request data for testing"""
    return {
        "valid_query": {
            "query": "What is machine learning?",
            "session_id": "test-session-123"
        },
        "query_without_session": {
            "query": "Explain neural networks"
        },
        "empty_query": {
            "query": ""
        }
    }


@pytest.fixture
def sample_course_analytics():
    """Sample course analytics data for testing"""
    return {
        "total_courses": 5,
        "course_titles": [
            "Introduction to Machine Learning",
            "Deep Learning Fundamentals",
            "Natural Language Processing",
            "Computer Vision",
            "Reinforcement Learning"
        ]
    }


@pytest.fixture
def mock_sources():
    """Sample source data for testing"""
    return [
        {
            "source": "ml_basics.pdf",
            "page": 1,
            "content": "Machine learning is a subset of artificial intelligence...",
            "relevance_score": 0.95
        },
        {
            "source": "neural_networks.pdf",
            "page": 3,
            "content": "Neural networks are computing systems inspired by biological neural networks...",
            "relevance_score": 0.87
        }
    ]


@pytest.fixture
def mock_environment_variables():
    """Mock environment variables for testing"""
    env_vars = {
        "ANTHROPIC_API_KEY": "test-api-key",
        "CHROMA_PATH": "/tmp/test_chroma",
        "LOG_LEVEL": "DEBUG"
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars