"""
Simple test for Bedrock Agent QA
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.bedrock_agent import BedrockAgentQA


def test_simple_navigation():
    """
    Test simple navigation scenario
    """
    print("Testing Bedrock Agent QA...")
    print("=" * 50)
    
    story = """
    Navigate to https://www.google.com
    Take a screenshot of the homepage
    """
    
    agent = BedrockAgentQA()
    
    try:
        print("Starting MCP server...")
        agent.start_mcp_server()
        
        print(f"\nExecuting story:\n{story}\n")
        print("Agent is working...\n")
        
        results = agent.execute_story(story, max_iterations=10)
        
        print("\n" + "=" * 50)
        print("RESULTS")
        print("=" * 50)
        print(f"Status: {results['status']}")
        print(f"Actions taken: {len(results.get('actions_taken', []))}")
        print(f"Screenshots: {len(results.get('screenshots', []))}")
        
        if results.get('summary'):
            print(f"\nSummary: {results['summary']}")
        
        if results.get('error'):
            print(f"\nError: {results['error']}")
        
        print("\n" + "=" * 50)
        
    finally:
        agent.close()


if __name__ == '__main__':
    test_simple_navigation()

