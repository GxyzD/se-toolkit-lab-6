import os
import sys
import json
import requests
import re
from pathlib import Path
from dotenv import load_dotenv


# Tool definitions for function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

def safe_path(path):
    """
    Check if path is safe (no directory traversal, inside project)
    Returns: (full_path, error_message)
    """
    project_root = Path.cwd()
    
    # Clean the path
    path = path.strip().replace('\\', '/')
    
    # Block directory traversal
    if '..' in path.split('/'):
        return None, "Access denied: directory traversal (..) is not allowed"
    
    # Get full path
    try:
        full_path = (project_root / path).resolve()
    except Exception as e:
        return None, f"Error resolving path: {str(e)}"
    
    # Check if inside project
    if not str(full_path).startswith(str(project_root)):
        return None, f"Access denied: path is outside project directory"
    
    return full_path, None

def read_file(path):
    """Read file contents safely"""
    full_path, error = safe_path(path)
    if error:
        return error
    
    try:
        if not full_path.exists():
            return f"Error: File not found: {path}"
        
        if not full_path.is_file():
            return f"Error: Not a file: {path}"
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except PermissionError:
        return f"Error: Permission denied reading {path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

def list_files(path):
    """List directory contents safely"""
    full_path, error = safe_path(path)
    if error:
        return error
    
    try:
        if not full_path.exists():
            return f"Error: Path not found: {path}"
        
        if not full_path.is_dir():
            return f"Error: Not a directory: {path}"
        
        entries = list(full_path.iterdir())
        # Sort: directories first (with /), then files
        dirs = [e.name + "/" for e in entries if e.is_dir()]
        files = [e.name for e in entries if e.is_file()]
        
        return "\n".join(sorted(dirs) + sorted(files))
    except PermissionError:
        return f"Error: Permission denied listing {path}"
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def execute_tool(tool_call):
    """Execute a tool call and return result"""
    tool_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])
    
    if tool_name == "read_file":
        return read_file(arguments["path"])
    elif tool_name == "list_files":
        return list_files(arguments["path"])
    else:
        return f"Error: Unknown tool {tool_name}"

# System prompt to guide the LLM
SYSTEM_PROMPT = """You are a documentation assistant for a software engineering course.
You help students answer questions about Git, workflows, and other topics.

You have access to two tools:
1. list_files(path) - lists files in a directory
2. read_file(path) - reads a file's contents

The documentation is stored in the 'wiki/' directory.

STRATEGY:
1. First, use list_files('wiki') to see what documentation is available
2. If the question is about a specific topic, read the most relevant files
3. When you find the answer, include the source file (with section if possible)
4. If you cannot find the answer in the documentation, say so honestly

RULES:
- Always cite your source (file path) in the final answer
- You can make multiple tool calls in one response
- Each tool call must have valid arguments
- When you have enough information, provide the final answer

FORMAT FOR SOURCE:
Include the source as: wiki/filename.md#section
Example: wiki/git-workflow.md#resolving-merge-conflicts"""

def call_llm_with_tools(messages, tools=None):
    """Call LLM with optional tool definitions"""
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')
    
    if not all([api_key, api_base, model]):
        print("ERROR: Missing environment variables", file=sys.stderr)
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    
    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        return None

def has_tool_calls(response):
    """Check if response contains tool calls"""
    if not response or "choices" not in response:
        return False
    message = response["choices"][0].get("message", {})
    return "tool_calls" in message and message["tool_calls"]

def extract_source(messages, tool_calls_log):
    """Extract source reference from conversation"""
    # Look in final assistant message
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            content = msg.get("content", "")
            # Look for wiki/file.md pattern
            import re
            match = re.search(r'(wiki/[\w\-\./]+\.md(?:#[^\s]+)?)', content)
            if match:
                return match.group(1)
            break
    
    # If not found, check read_file calls
    for call in reversed(tool_calls_log):
        if call["tool"] == "read_file" and "wiki/" in call["args"]["path"]:
            return call["args"]["path"]
    
    return ""

def agentic_loop(question, max_turns=10):
    """Main agent loop with tool execution"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    tool_calls_log = []
    
    print(f"\nStarting agentic loop for: {question}", file=sys.stderr)
    
    for turn in range(max_turns):
        print(f"Turn {turn + 1}/{max_turns}", file=sys.stderr)
        
        response = call_llm_with_tools(messages, TOOLS)
        if not response:
            return {
                "answer": "Error: Failed to get response from LLM",
                "source": "",
                "tool_calls": tool_calls_log
            }
        
        message = response["choices"][0]["message"]
        
        if has_tool_calls(response):
            # Add assistant message to conversation
            messages.append({
                "role": "assistant", 
                "content": message.get("content", ""),
                "tool_calls": message["tool_calls"]
            })
            
            # Execute each tool call
            for tool_call in message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                print(f"  Executing: {tool_name}", file=sys.stderr)
                
                result = execute_tool(tool_call)
                
                # Log the call
                tool_calls_log.append({
                    "tool": tool_name,
                    "args": json.loads(tool_call["function"]["arguments"]),
                    "result": result
                })
                
                # Add result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result
                })
        else:
            # No tool calls - final answer
            answer = message.get("content", "")
            source = extract_source(messages, tool_calls_log)
            
            print(f"Final answer received, source: {source}", file=sys.stderr)
            
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log
            }
    
    # Max turns reached
    return {
        "answer": f"Reached maximum of {max_turns} turns",
        "source": "",
        "tool_calls": tool_calls_log
    }

def main():
    """Main CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py <question>", file=sys.stderr)
        print("Example: uv run agent.py 'How do I resolve a merge conflict?'", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]

    # Load environment variables
    load_dotenv('.env.agent.secret')

    # Run agentic loop
    result = agentic_loop(question)

    # Output only JSON to stdout
    # Use UTF-8 encoding to support Unicode characters on Windows
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    sys.stdout.flush()  # Force flush for Windows

if __name__ == "__main__":
    main()