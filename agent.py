import os
import json
from pathlib import Path


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