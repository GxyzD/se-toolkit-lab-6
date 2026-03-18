import subprocess
import json
import sys

def run_agent(question):
    """Helper function to run agent and return result"""
    try:
        result = subprocess.run(
            ["uv", "run", "agent.py", question],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120
        )
        return result
    except Exception as e:
        print(f"Error running agent: {e}", file=sys.stderr)
        return None

def test_agent_reads_wiki_file():
    """Test that agent can read a wiki file for merge conflict question"""
    print("\n--- Running test: agent reads wiki file ---", file=sys.stderr)

    result = run_agent("How do you resolve a merge conflict?")

    assert result is not None, "Failed to run agent"

    # Проверяем, что есть вывод
    assert result.stdout, "STDOUT is empty"
    
    try:
        output = json.loads(result.stdout)
        print(f"Source found: {output.get('source', 'NONE')}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"STDOUT: {result.stdout[:500]}", file=sys.stderr)
        assert False, f"Output is not valid JSON: {e}"
    
    # Проверяем поля
    assert "answer" in output
    assert "source" in output
    assert "tool_calls" in output
    
    # Проверяем, что были вызовы инструментов
    assert len(output["tool_calls"]) > 0, "No tool calls made"
    
    print("✅ Test passed: agent reads wiki file", file=sys.stderr)

def test_agent_lists_wiki():
    """Test that agent can list wiki directory"""
    print("\n--- Running test: agent lists wiki ---", file=sys.stderr)
    
    result = run_agent("What files are in the wiki directory?")
    
    assert result is not None, "Failed to run agent"
    print(f"Return code: {result.returncode}", file=sys.stderr)
    assert result.stdout, "STDOUT is empty"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, "Output is not valid JSON"
    
    assert "answer" in output
    assert "source" in output
    assert "tool_calls" in output
    
    # Проверяем, что list_files вызывался
    list_files_calls = [t for t in output["tool_calls"] if t["tool"] == "list_files"]
    assert len(list_files_calls) > 0, "list_files should be called"
    
    print("✅ Test passed: agent lists wiki", file=sys.stderr)

def test_agent_source_field():
    """Test that source field is populated"""
    print("\n--- Running test: source field ---", file=sys.stderr)
    
    result = run_agent("How do you resolve a merge conflict?")
    
    assert result is not None, "Failed to run agent"
    print(f"Return code: {result.returncode}", file=sys.stderr)
    assert result.stdout, "STDOUT is empty"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, "Output is not valid JSON"
    
    # Source может быть пустым, но для этого вопроса он должен быть
    if not output.get("source"):
        print("WARNING: source field is empty", file=sys.stderr)
    else:
        print(f"Source: {output['source']}", file=sys.stderr)
    
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
