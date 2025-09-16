#!/usr/bin/env python3
"""
Debug script to identify the root cause of QUERY FAILED issue
"""

import os
import sys
from config import config
from rag_system import RAGSystem
from document_processor import DocumentProcessor
from vector_store import VectorStore

def test_document_processing():
    """Test if document processing is working"""
    print("=== TESTING DOCUMENT PROCESSING ===")

    doc_processor = DocumentProcessor(config.CHUNK_SIZE, config.CHUNK_OVERLAP)

    # Test with first course file
    docs_path = "../docs"
    if not os.path.exists(docs_path):
        print(f"❌ Docs directory not found: {docs_path}")
        return False

    course_files = [f for f in os.listdir(docs_path) if f.endswith('.txt')]
    if not course_files:
        print("❌ No course files found")
        return False

    test_file = os.path.join(docs_path, course_files[0])
    print(f"Testing file: {test_file}")

    try:
        course, chunks = doc_processor.process_course_document(test_file)
        print(f"✅ Course parsed: {course.title}")
        print(f"✅ Instructor: {course.instructor}")
        print(f"✅ Course link: {course.course_link}")
        print(f"✅ Number of lessons: {len(course.lessons)}")
        print(f"✅ Number of chunks: {len(chunks)}")

        if len(chunks) > 0:
            print(f"✅ First chunk content: {chunks[0].content[:100]}...")

        return True

    except Exception as e:
        print(f"❌ Document processing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_vector_store():
    """Test vector store functionality"""
    print("\n=== TESTING VECTOR STORE ===")

    try:
        vector_store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
        print("✅ Vector store initialized")

        # Check existing data
        course_count = vector_store.get_course_count()
        existing_titles = vector_store.get_existing_course_titles()

        print(f"📊 Current course count: {course_count}")
        print(f"📊 Existing course titles: {existing_titles}")

        if course_count == 0:
            print("⚠️  No courses found in vector store")
            return False

        # Test search
        results = vector_store.search("programming")
        print(f"🔍 Search results for 'programming': {len(results.documents)} documents")
        if results.error:
            print(f"❌ Search error: {results.error}")
            return False

        if len(results.documents) > 0:
            print(f"✅ First result: {results.documents[0][:100]}...")

        return True

    except Exception as e:
        print(f"❌ Vector store test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_rag_system():
    """Test full RAG system"""
    print("\n=== TESTING RAG SYSTEM ===")

    try:
        rag_system = RAGSystem(config)
        print("✅ RAG system initialized")

        # Test analytics
        analytics = rag_system.get_course_analytics()
        print(f"📊 Total courses: {analytics['total_courses']}")
        print(f"📊 Course titles: {analytics['course_titles']}")

        if analytics['total_courses'] == 0:
            print("⚠️  No courses in RAG system")
            return False

        # Test query
        print("🔍 Testing query: 'What is programming?'")
        answer, sources = rag_system.query("What is programming?")
        print(f"📝 Answer: {answer[:200]}...")
        print(f"📚 Sources: {len(sources)} found")

        if not answer or answer == "QUERY FAILED":
            print("❌ Query failed")
            return False

        print("✅ RAG system query successful")
        return True

    except Exception as e:
        print(f"❌ RAG system test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_tool_execution():
    """Test individual tool execution"""
    print("\n=== TESTING TOOL EXECUTION ===")

    try:
        vector_store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)

        # Import and test search tool
        from search_tools import CourseSearchTool
        search_tool = CourseSearchTool(vector_store)

        print("🔧 Testing CourseSearchTool directly...")
        result = search_tool.execute("programming")
        print(f"📝 Tool result: {result[:200]}...")

        if "No relevant content found" in result:
            print("⚠️  Search tool found no content")
            return False

        print("✅ Search tool working")
        return True

    except Exception as e:
        print(f"❌ Tool execution test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def run_diagnostics():
    """Run all diagnostic tests"""
    print("🔍 RUNNING SYSTEM DIAGNOSTICS")
    print("=" * 50)

    # Check environment
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🔑 API key configured: {'Yes' if config.ANTHROPIC_API_KEY else 'No'}")
    print(f"📂 ChromaDB path: {config.CHROMA_PATH}")

    tests = [
        ("Document Processing", test_document_processing),
        ("Vector Store", test_vector_store),
        ("Tool Execution", test_tool_execution),
        ("RAG System", test_rag_system),
    ]

    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {str(e)}")
            results[test_name] = False

    # Summary
    print("\n" + "=" * 50)
    print("📋 DIAGNOSTIC SUMMARY")
    print("=" * 50)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")

    if all(results.values()):
        print("\n🎉 All tests passed! System appears to be working.")
    else:
        print("\n⚠️  Some tests failed. Issues identified above need to be fixed.")

        # Specific recommendations
        if not results.get("Vector Store", True):
            print("\n💡 RECOMMENDATION: Vector store issues detected.")
            print("   - Check if ChromaDB is properly initialized")
            print("   - Verify course data was loaded correctly")

        if not results.get("Document Processing", True):
            print("\n💡 RECOMMENDATION: Document processing issues detected.")
            print("   - Check course file format")
            print("   - Verify document processor parsing logic")

if __name__ == "__main__":
    # Change to backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)

    run_diagnostics()