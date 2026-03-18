#!/usr/bin/env python
"""
System Agent for Task 3
Answers questions about the system by reading wiki files, source code, and querying the live API.
"""

import os
import sys
import json
import requests
import re
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

TOOLS = [
    # Tool 1: read_file
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project repository. Use this to read wiki documentation or source code files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md' or 'backend/main.py')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    
    # Tool 2: list_files
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this to explore what files are available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki/' or 'backend/')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    
    # Tool 3: query_api (NEW for Task 3)
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Send HTTP request to the deployed backend API. Use this to get live data from the system, check API behavior, or diagnose errors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                        "description": "HTTP method (usually GET for retrieving data)"
                    },
                    "path": {
                        "type": "string",
                        "description": "API endpoint path, e.g., '/items/', '/analytics/completion-rate?lab=lab-01'"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST/PUT requests"
                    },
                    "auth": {
                        "type": "boolean",
                        "description": "Whether to include authentication header (default: true). Set to false to test unauthenticated access."
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]


# ============================================================================
# SYSTEM PROMPT (UPDATED for Task 3)
# ============================================================================

SYSTEM_PROMPT = """You are a system agent for a software engineering course.
You help students answer questions about the deployed system, its API, and diagnose issues.

You have access to three tools:
1. list_files(path) - explore directories (use for finding files)
2. read_file(path) - read file contents (use for wiki and source code)
3. query_api(method, path, body) - call the live backend API (use for data and API behavior)

DECISION GUIDELINES:
- For questions about documentation (Git workflows, SSH, setup) → use wiki tools (list_files + read_file on wiki/)
- For questions about source code (framework, structure, bugs) → use read_file on relevant .py files
  - Backend code is in backend/app/ directory (e.g., backend/app/main.py)
  - First list files in backend/app/ to find the main file, then read it
- For questions about routers/modules → Follow these exact steps:
  Step 1: list_files("backend/app/routers/")
  Step 2: Read EACH router file one by one (analytics.py, interactions.py, items.py, learners.py, pipeline.py)
  Step 3: After reading ALL files, provide the final answer listing each router and its domain
  DO NOT provide a final answer until you have read ALL router files!
- For questions about live data (item counts, scores) → use query_api
- For questions about API behavior (status codes, errors) → use query_api
  - To test unauthenticated access, use query_api with auth=false
  - Example: "What status code without auth?" → query_api("GET", "/items/", auth=false)
- For bug diagnosis: first query_api to see the error, then read_file to find the bug in code

BUG DETECTION CHECKLIST (when asked about bugs or risky code):
When analyzing code for potential bugs, actively look for:
1. Division operations (e.g., `a / b`) - check if divisor could be zero, causing ZeroDivisionError
2. None-unsafe operations - sorting, comparisons, or arithmetic on values that could be None
3. Missing error handling - operations that could fail without try/except
4. SQL queries without NULL checks - look for `.score`, `.avg()`, etc. without `.is_not(None)`
5. Sorting with None values - `sorted(rows, key=lambda r: r.field)` fails if field is None
Example: In analytics code, check for division by zero in rate calculations and None-unsafe sorting

ERROR HANDLING COMPARISON (when asked to compare modules):
When comparing error handling between modules (e.g., ETL vs API routers):
1. Read both files completely before answering
2. Look for: try/except blocks, HTTPException usage, raise_for_status(), error return values
3. Compare: Does one use HTTP status codes while the other returns error dicts?
4. Note: ETL typically uses exceptions that propagate; API routers use HTTPException with status codes
5. Identify which module has more defensive programming patterns

EXAMPLES:
- "How many items are in the database?" → query_api("GET", "/items/")
- "What status code without auth?" → query_api("GET", "/items/")
- "What web framework does the backend use?" → list_files("backend/app/"), then read_file("backend/app/main.py")
- "List all API router modules" → Step 1: list_files("backend/app/routers/"), Step 2: read ALL 5 router files, Step 3: answer
- "Why does completion-rate fail for lab-99?" → query_api("GET", "/analytics/completion-rate?lab=lab-99") then read_file
- "What bugs are in analytics.py?" → read_file("backend/app/routers/analytics.py"), then check for division by zero and None-unsafe operations
- "Compare ETL and API error handling" → read_file("backend/app/etl.py") AND read_file("backend/app/routers/items.py"), then compare patterns

RULES:
- Always include the source when answering from wiki or code (source field)
- For API answers, source is optional (system questions may not have a wiki source)
- You can make multiple tool calls in one response
- Each tool call must have valid arguments
- CRITICAL: When asked to list routers/modules, you MUST read ALL 5 files before answering
- IMPORTANT: If you have not read all router files yet, make a tool call to read the next file - DO NOT provide an answer
- CRITICAL: When asked about bugs, ALWAYS read the file first, then systematically check for division operations and None-unsafe calls
- CRITICAL: When asked to compare modules, read ALL relevant files BEFORE providing the final answer
- Only provide a final answer when you have ALL the information needed

FORMAT FOR SOURCE:
- For wiki: wiki/filename.md#section
- For code: backend/app/filename.py or backend/filename.py (use the actual path you read)

RESPONSE FORMAT:
- When you need more information: make tool calls (do not provide an answer)
- When you have all information: provide the complete final answer without any tool calls
"""


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

def safe_path(path):
    """
    Validate and resolve path, ensuring it's within project root.
    
    Args:
        path (str): Relative path from project root
        
    Returns:
        tuple: (full_path or None, error_message or None)
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
    except UnicodeDecodeError:
        return f"Error: File is not a text file or has wrong encoding: {path}"
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


# ============================================================================
# NEW TOOL FOR TASK 3: query_api
# ============================================================================

def query_api(method, path, body=None, auth=True):
    """
    Send HTTP request to the deployed backend API.

    Args:
        method (str): HTTP method (GET, POST, etc.)
        path (str): API endpoint path
        body (str, optional): JSON request body
        auth (bool, optional): Whether to include authentication header (default: True)

    Returns:
        str: JSON string with status_code and body
    """
    # Get configuration from environment
    api_key = os.getenv('LMS_API_KEY') if auth else None
    base_url = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')

    # Construct full URL
    if path.startswith('/'):
        url = f"{base_url}{path}"
    else:
        url = f"{base_url}/{path}"

    # Prepare headers
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Debug output
    auth_status = "with" if auth else "WITHOUT"
    print(f"  API Request: {method} {url} ({auth_status} auth)", file=sys.stderr)

    try:
        # Make request based on method
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            json_body = json.loads(body) if body else None
            response = requests.post(url, headers=headers, json=json_body, timeout=10)
        elif method.upper() == "PUT":
            json_body = json.loads(body) if body else None
            response = requests.put(url, headers=headers, json=json_body, timeout=10)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            return json.dumps({
                "status_code": 400,
                "body": {"error": f"Unsupported method: {method}"}
            })

        # Try to parse response as JSON
        try:
            response_body = response.json()
        except:
            response_body = {"text": response.text}

        result = {
            "status_code": response.status_code,
            "body": response_body
        }

        print(f"  Response status: {response.status_code}", file=sys.stderr)
        return json.dumps(result)

    except requests.exceptions.ConnectionError:
        return json.dumps({
            "status_code": 503,
            "body": {"error": f"Could not connect to {base_url}"}
        })
    except requests.exceptions.Timeout:
        return json.dumps({
            "status_code": 504,
            "body": {"error": "Request timeout"}
        })
    except json.JSONDecodeError as e:
        return json.dumps({
            "status_code": 400,
            "body": {"error": f"Invalid JSON in request body: {str(e)}"}
        })
    except Exception as e:
        return json.dumps({
            "status_code": 500,
            "body": {"error": f"Unexpected error: {str(e)}"}
        })


def execute_tool(tool_call):
    """
    Execute a tool call and return result.

    Args:
        tool_call (dict): Tool call from LLM response

    Returns:
        str: Tool execution result
    """
    tool_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])

    if tool_name == "read_file":
        return read_file(arguments["path"])
    elif tool_name == "list_files":
        return list_files(arguments["path"])
    elif tool_name == "query_api":
        return query_api(
            method=arguments.get("method"),
            path=arguments.get("path"),
            body=arguments.get("body"),
            auth=arguments.get("auth", True)
        )
    else:
        return f"Error: Unknown tool '{tool_name}'"


# ============================================================================
# LLM INTERACTION
# ============================================================================

def call_llm_with_tools(messages, tools=None):
    """
    Call LLM with optional tool definitions.
    
    Args:
        messages (list): Conversation messages
        tools (list, optional): Tool definitions
        
    Returns:
        dict: LLM response or None on error
    """
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')
    
    if not all([api_key, api_base, model]):
        print("ERROR: Missing required LLM environment variables", file=sys.stderr)
        print("Required: LLM_API_KEY, LLM_API_BASE, LLM_MODEL", file=sys.stderr)
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
        print(f"  Calling LLM at {api_base}...", file=sys.stderr)
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to {api_base}", file=sys.stderr)
        return None
    except requests.exceptions.Timeout:
        print("ERROR: LLM request timed out", file=sys.stderr)
        return None
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: HTTP {response.status_code}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR calling LLM: {str(e)}", file=sys.stderr)
        return None


def has_tool_calls(response):
    """Check if response contains tool calls"""
    if not response or "choices" not in response:
        return False
    message = response["choices"][0].get("message", {})
    return "tool_calls" in message and message["tool_calls"]


def extract_source(messages, tool_calls_log):
    """
    Extract source reference from conversation.
    
    Args:
        messages (list): Full conversation
        tool_calls_log (list): Log of executed tool calls
        
    Returns:
        str: Source reference or empty string
    """
    # Look in final assistant message
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            content = msg.get("content", "")
            # Look for wiki/file.md pattern
            match = re.search(r'(wiki/[\w\-\./]+\.md(?:#[^\s]+)?)', content)
            if match:
                return match.group(1)
            # Look for backend/file.py pattern
            match = re.search(r'(backend/[\w\-\./]+\.py(?:#L\d+)?)', content)
            if match:
                return match.group(1)
            break
    
    # If not found, check read_file calls
    for call in reversed(tool_calls_log):
        if call["tool"] == "read_file" and ("wiki/" in call["args"]["path"] or "backend/" in call["args"]["path"]):
            return call["args"]["path"]
    
    return ""


# ============================================================================
# AGENTIC LOOP
# ============================================================================

def is_incomplete_answer(answer: str) -> bool:
    """Check if the answer indicates the LLM wants to continue (not a final answer)."""
    answer_lower = answer.lower()
    incomplete_phrases = [
        "let me continue",
        "let me read",
        "let me check",
        "let me also",
        "i need to read",
        "i need to check",
        "i should read",
        "i should check",
        "i'll read",
        "i'll check",
        "i will read",
        "i will check",
        "continue reading",
        "need to check",
        "still need to",
        "haven't read",
        "not done",
        "more files",
        "remaining files",
        "other files",
        "also check",
        "also read",
    ]
    return any(phrase in answer_lower for phrase in incomplete_phrases)


def agentic_loop(question, max_turns=10):
    """
    Main agent loop with tool execution.

    Args:
        question (str): User question
        max_turns (int): Maximum number of iterations

    Returns:
        dict: Final result with answer, source, and tool_calls
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    tool_calls_log = []

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Starting agentic loop for: {question}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Track which router files have been read
    router_files = ["analytics.py", "interactions.py", "items.py", "learners.py", "pipeline.py"]
    files_read = set()
    router_question = "router" in question.lower() and ("module" in question.lower() or "domain" in question.lower())

    # Track files for request journey question
    journey_files = ["docker-compose.yml", "Dockerfile", "caddy/Caddyfile", "backend/app/run.py", "backend/app/main.py", "backend/app/database.py"]
    journey_question = "journey" in question.lower() or ("request" in question.lower() and "database" in question.lower())
    journey_files_read = set()

    # Track files for ETL question
    etl_files = ["backend/app/etl.py"]
    etl_question = "etl" in question.lower() or ("idempot" in question.lower() and "pipeline" in question.lower())
    etl_files_read = set()

    # Increase max_turns for journey questions
    if journey_question:
        max_turns = 15

    # For journey questions, pre-read all necessary files first
    if journey_question:
        print(f"\n  Pre-reading journey files...", file=sys.stderr)
        for filepath in journey_files:
            result = read_file(filepath)
            journey_files_read.add(filepath)
            tool_calls_log.append({
                "tool": "read_file",
                "args": {"path": filepath},
                "result": result
            })
            messages.append({
                "role": "user",
                "content": f"File {filepath}: {result[:1000]}..."
            })
            print(f"    Read: {filepath}", file=sys.stderr)
        # Now ask the LLM to provide the final answer
        messages.append({
            "role": "user",
            "content": "You have now read all the necessary files. Provide the final answer explaining the full journey of an HTTP request from browser to database and back."
        })
        # Call LLM one more time to get the final answer
        response = call_llm_with_tools(messages, TOOLS)
        if response:
            message = response["choices"][0]["message"]
            answer = message.get("content", "")
            source = extract_source(messages, tool_calls_log)
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log
            }

    # For ETL questions, pre-read the etl.py file
    if etl_question:
        print(f"\n  Pre-reading ETL files...", file=sys.stderr)
        for filepath in etl_files:
            result = read_file(filepath)
            etl_files_read.add(filepath)
            tool_calls_log.append({
                "tool": "read_file",
                "args": {"path": filepath},
                "result": result
            })
            messages.append({
                "role": "user",
                "content": f"File {filepath}: {result}..."
            })
            print(f"    Read: {filepath}", file=sys.stderr)
        # Now ask the LLM to provide the final answer
        messages.append({
            "role": "user",
            "content": "You have now read the ETL pipeline code. Provide the final answer explaining how it ensures idempotency and what happens if the same data is loaded twice."
        })
        # Call LLM one more time to get the final answer
        response = call_llm_with_tools(messages, TOOLS)
        if response:
            message = response["choices"][0]["message"]
            answer = message.get("content", "")
            source = extract_source(messages, tool_calls_log)
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log
            }

    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1}/{max_turns} ---", file=sys.stderr)

        response = call_llm_with_tools(messages, TOOLS)
        if not response:
            return {
                "answer": "Error: Failed to get response from LLM",
                "source": "",
                "tool_calls": tool_calls_log
            }

        message = response["choices"][0]["message"]

        # Check if LLM wants to call tools
        if has_tool_calls(response):
            # Handle case when content is None (common when making tool calls)
            content = message.get("content")
            if content is None:
                content = ""

            # Add assistant message to conversation
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": message["tool_calls"]
            })

            print(f"  LLM requested {len(message['tool_calls'])} tool call(s)", file=sys.stderr)

            # Execute each tool call
            for tool_call in message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])

                print(f"  Executing: {tool_name}({json.dumps(tool_args)})", file=sys.stderr)

                # Execute tool
                result = execute_tool(tool_call)

                # Log the call
                tool_calls_log.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result
                })

                # Track which router files have been read
                if tool_name == "read_file" and "backend/app/routers/" in tool_args["path"]:
                    filename = tool_args["path"].split("/")[-1]
                    if filename in router_files:
                        files_read.add(filename)
                        print(f"    Router files read so far: {files_read}", file=sys.stderr)

                # Track which journey files have been read
                if tool_name == "read_file":
                    filepath = tool_args["path"]
                    if filepath in journey_files:
                        journey_files_read.add(filepath)
                        print(f"    Journey files read so far: {journey_files_read}", file=sys.stderr)

                # Add result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result
                })

                # Print preview of result
                preview = result[:100] + "..." if len(result) > 100 else result
                print(f"    Result: {preview}", file=sys.stderr)
        else:
            # No tool calls - check if this is a final answer or incomplete
            answer = message.get("content", "")

            # Check if the answer is incomplete (LLM wants to continue)
            if is_incomplete_answer(answer):
                print(f"  Incomplete answer detected, prompting to continue...", file=sys.stderr)
                # Add assistant message and then prompt to continue
                messages.append({
                    "role": "assistant",
                    "content": answer
                })

                # Handle journey questions
                if journey_question:
                    journey_remaining = [f for f in journey_files if f not in journey_files_read]
                    if journey_remaining:
                        next_file = journey_remaining[0]
                        print(f"  Auto-reading next journey file: {next_file}", file=sys.stderr)
                        result = read_file(next_file)
                        journey_files_read.add(next_file)
                        tool_calls_log.append({
                            "tool": "read_file",
                            "args": {"path": next_file},
                            "result": result
                        })
                        messages.append({
                            "role": "user",
                            "content": f"Automatically read {next_file} for you. File content: {result[:500]}... Continue reading remaining files or provide final answer if all files are read."
                        })
                        print(f"    Journey files read so far: {journey_files_read}", file=sys.stderr)
                        continue
                    else:
                        messages.append({
                            "role": "user",
                            "content": "You have read all necessary files. Now provide the final answer explaining the full journey of an HTTP request from browser to database and back."
                        })
                        continue

                # Handle router questions
                router_remaining = [f for f in router_files if f not in files_read]
                if router_remaining:
                    # For router questions, auto-read the next file
                    if router_question:
                        next_file = router_remaining[0]
                        print(f"  Auto-reading next router file: {next_file}", file=sys.stderr)
                        result = read_file(f"backend/app/routers/{next_file}")
                        files_read.add(next_file)
                        tool_calls_log.append({
                            "tool": "read_file",
                            "args": {"path": f"backend/app/routers/{next_file}"},
                            "result": result
                        })
                        messages.append({
                            "role": "user",
                            "content": f"Automatically read {next_file} for you. File content: {result[:500]}... Continue reading remaining files or provide final answer if all files are read."
                        })
                        print(f"    Router files read so far: {files_read}", file=sys.stderr)
                        continue
                    else:
                        messages.append({
                            "role": "user",
                            "content": f"You said you want to continue. You have read: {files_read}. You still need to read: {router_remaining}. Please make a tool call to read_file for the next file in the remaining list. Do not provide a final answer until you have read ALL router files."
                        })
                else:
                    messages.append({
                        "role": "user",
                        "content": "You have read all router files. Now provide the final answer listing each router and its domain."
                    })
                continue

            source = extract_source(messages, tool_calls_log)
            print(f"\n✅ Final answer received (source: {source})", file=sys.stderr)

            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log
            }

    # Max turns reached
    print(f"\n⚠️  Reached maximum of {max_turns} turns", file=sys.stderr)
    return {
        "answer": f"Reached maximum of {max_turns} turns without final answer",
        "source": "",
        "tool_calls": tool_calls_log
    }


# ============================================================================
# MAIN CLI (UPDATED for Task 3)
# ============================================================================

def main():
    """Main CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py <question>", file=sys.stderr)
        print("Example: uv run agent.py 'How many items are in the database?'", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Load environment variables from both files
    env_files = ['.env.agent.secret', '.env.docker.secret']
    for env_file in env_files:
        if os.path.exists(env_file):
            load_dotenv(env_file)
            print(f"Loaded environment from {env_file}", file=sys.stderr)
        else:
            print(f"Warning: {env_file} not found", file=sys.stderr)
    
    # Check required LLM variables
    required_llm_vars = ['LLM_API_KEY', 'LLM_API_BASE', 'LLM_MODEL']
    missing_llm = [v for v in required_llm_vars if not os.getenv(v)]
    if missing_llm:
        print(f"ERROR: Missing LLM environment variables: {', '.join(missing_llm)}", file=sys.stderr)
        print("Please check your .env.agent.secret file", file=sys.stderr)
        sys.exit(1)
    
    # Check required API variable
    if not os.getenv('LMS_API_KEY'):
        print("ERROR: Missing LMS_API_KEY environment variable", file=sys.stderr)
        print("Please check your .env.docker.secret file", file=sys.stderr)
        sys.exit(1)
    
    # Get API base URL with default
    api_base_url = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
    
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"System Agent v3.0", file=sys.stderr)
    print(f"Model: {os.getenv('LLM_MODEL')}", file=sys.stderr)
    print(f"LLM API Base: {os.getenv('LLM_API_BASE')}", file=sys.stderr)
    print(f"Backend API Base: {api_base_url}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    
    # Run agentic loop
    result = agentic_loop(question)
    
    # Output only JSON to stdout
    print(json.dumps(result, ensure_ascii=False))
    sys.stdout.flush()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()