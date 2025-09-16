#!/usr/bin/env python3
"""
Test the actual web API to see what happens when queries are made
"""

import requests
import json
import time

def test_web_api():
    """Test the running web server API"""
    print("🌐 TESTING WEB API")
    print("=" * 50)

    # Test if server is running
    base_url = "http://127.0.0.1:8000"

    try:
        # Test if server is accessible
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Server is accessible (status: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ Server not accessible: {str(e)}")
        return False

    # Test course analytics endpoint
    try:
        response = requests.get(f"{base_url}/api/courses", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Courses API working: {data['total_courses']} courses found")
            print(f"   Course titles: {data['course_titles']}")
        else:
            print(f"❌ Courses API failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Courses API error: {str(e)}")
        return False

    # Test query endpoint with different types of queries
    test_queries = [
        "What is programming?",
        "Tell me about Python",
        "What is the outline of the MCP course?",
        "Explain computer use with Anthropic"
    ]

    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")

        try:
            payload = {
                "query": query,
                "session_id": "test_session_123"
            }

            response = requests.post(
                f"{base_url}/api/query",
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', '')
                sources = data.get('sources', [])

                if answer == "QUERY FAILED" or not answer.strip():
                    print(f"❌ Query failed: {answer}")
                else:
                    print(f"✅ Answer received ({len(answer)} chars)")
                    print(f"   Answer preview: {answer[:150]}...")
                    print(f"   Sources: {len(sources)} found")

                    if sources:
                        for i, source in enumerate(sources[:3]):
                            print(f"     Source {i+1}: {source.get('text', 'No text')}")
                    else:
                        print("   ⚠️  No sources found (possible tool issue)")

            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"   Response: {response.text}")

        except requests.exceptions.Timeout:
            print(f"❌ Query timeout (>30s)")
        except Exception as e:
            print(f"❌ Query error: {str(e)}")

        time.sleep(1)  # Avoid rate limiting

    return True

def test_direct_tool_via_api():
    """Test if we can directly call tools through the API"""
    print(f"\n🔧 TESTING DIRECT TOOL SIMULATION")
    print("=" * 30)

    # This simulates what should happen when AI calls tools
    try:
        from config import config
        from rag_system import RAGSystem

        rag_system = RAGSystem(config)

        # Test search tool directly
        search_result = rag_system.tool_manager.execute_tool(
            "search_course_content",
            query="programming"
        )
        print(f"✅ Direct search tool result: {search_result[:100]}...")

        # Test outline tool directly
        outline_result = rag_system.tool_manager.execute_tool(
            "get_course_outline",
            course_title="MCP"
        )
        print(f"✅ Direct outline tool result: {outline_result[:150]}...")

    except Exception as e:
        print(f"❌ Direct tool test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test web API
    test_web_api()

    # Test direct tool execution
    test_direct_tool_via_api()

    print(f"\n💡 If web API queries are failing but direct tools work,")
    print(f"   the issue is likely with:")
    print(f"   1. Anthropic API key configuration")
    print(f"   2. AI model not calling tools correctly")
    print(f"   3. Tool execution errors in the web context")