import subprocess
import json
import sys
import os

def run_agent(question):
    """Helper function to run agent and return result"""
    try:
        result = subprocess.run(
            ["uv", "run", "agent.py", question],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120  # 2 minute timeout
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"Timeout running agent with question: {question}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error running agent: {e}", file=sys.stderr)
        return None

def test_agent_reads_wiki_file():
    """Test that agent can read a wiki file for merge conflict question"""
    print("\n--- Running test: agent reads wiki file ---", file=sys.stderr)
    
    result = run_agent("How do you resolve a merge conflict?")
    
    assert result is not None, "Failed to run agent"
    assert result.returncode == 0, f"Agent failed with code {result.returncode}"
    
    # Print debug info
    if result.stderr:
        print(f"STDERR: {result.stderr[:500]}", file=sys.stderr)
    
    # Check that we got output
    assert result.stdout, "STDOUT is empty"
    
    # Parse JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Raw stdout: {result.stdout[:500]}", file=sys.stderr)
        assert False, f"Output is not valid JSON: {e}"
    
    # Check required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "source" in output, "Missing 'source' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    
    # Check that read_file was called
    tool_calls = output["tool_calls"]
    read_file_calls = [t for t in tool_calls if t["tool"] == "read_file"]
    assert len(read_file_calls) > 0, "read_file should be called"
    
    print("✅ Test passed: agent_reads_wiki_file", file=sys.stderr)

def test_agent_lists_wiki():
    """Test that agent can list wiki directory"""
    print("\n--- Running test: agent lists wiki ---", file=sys.stderr)
    
    result = run_agent("What files are in the wiki directory?")
    
    assert result is not None, "Failed to run agent"
    assert result.returncode == 0, f"Agent failed with code {result.returncode}"
    assert result.stdout, "STDOUT is empty"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Raw stdout: {result.stdout[:500]}", file=sys.stderr)
        assert False, f"Output is not valid JSON: {e}"
    
    # Check required fields
    assert "answer" in output
    assert "source" in output
    assert "tool_calls" in output
    
    # Check that list_files was called
    tool_calls = output["tool_calls"]
    list_files_calls = [t for t in tool_calls if t["tool"] == "list_files"]
    assert len(list_files_calls) > 0, "list_files should be called"
    
    print("✅ Test passed: agent_lists_wiki", file=sys.stderr)

def test_agent_source_field():
    """Test that source field is populated"""
    print("\n--- Running test: source field ---", file=sys.stderr)
    
    result = run_agent("How do you resolve a merge conflict?")
    
    assert result is not None, "Failed to run agent"
    assert result.returncode == 0, f"Agent failed with code {result.returncode}"
    assert result.stdout, "STDOUT is empty"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, "Output is not valid JSON"
    
    # Source should not be empty
    assert output["source"] != "", "Source field should not be empty"
    assert "wiki/" in output["source"] or "git" in output["source"], \
        f"Source should reference wiki file: {output['source']}"
    
    print("✅ Test passed: source field", file=sys.stderr)

if __name__ == "__main__":
    print("Running Task 2 tests...", file=sys.stderr)
    
    tests = [
        test_agent_reads_wiki_file,
        test_agent_lists_wiki,
        test_agent_source_field
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"❌ {test.__name__} FAILED: {e}", file=sys.stderr)
    
    print(f"\nTests complete: {passed} passed, {failed} failed", file=sys.stderr)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n✅ ALL TESTS PASSED!", file=sys.stderr)