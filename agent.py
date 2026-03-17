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

def read_file(path: str) -> str:
    """Read file safely (no directory traversal)"""
    # Нормализуем путь и проверяем, что он внутри проекта
    project_root = Path.cwd()
    full_path = (project_root / path).resolve()
    
    # Проверка безопасности
    if not str(full_path).startswith(str(project_root)):
        return "Error: Access denied - path outside project directory"
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

def list_files(path: str) -> str:
    """List files safely"""
    project_root = Path.cwd()
    full_path = (project_root / path).resolve()
    
    if not str(full_path).startswith(str(project_root)):
        return "Error: Access denied - path outside project directory"
    
    if not full_path.exists():
        return f"Error: Path not found: {path}"
    
    if not full_path.is_dir():
        return f"Error: Not a directory: {path}"
    
    try:
        entries = list(full_path.iterdir())
        # Сортируем: сначала папки, потом файлы
        dirs = [e.name + "/" for e in entries if e.is_dir()]
        files = [e.name for e in entries if e.is_file()]
        return "\n".join(sorted(dirs) + sorted(files))
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def agentic_loop(messages, max_turns=10):
    """Main agent loop"""
    tool_calls_log = []
    
    for turn in range(max_turns):
        # Вызов LLM с текущими сообщениями и определениями инструментов
        response = call_llm_with_tools(messages, TOOLS)
        
        # Проверяем, есть ли вызовы инструментов
        if 'tool_calls' in response and response['tool_calls']:
            # Выполняем каждый вызов
            for tool_call in response['tool_calls']:
                tool_name = tool_call['function']['name']
                tool_args = json.loads(tool_call['function']['arguments'])
                
                # Выполняем инструмент
                if tool_name == 'read_file':
                    result = read_file(tool_args['path'])
                elif tool_name == 'list_files':
                    result = list_files(tool_args['path'])
                else:
                    result = f"Error: Unknown tool {tool_name}"
                
                # Логируем вызов
                tool_calls_log.append({
                    'tool': tool_name,
                    'args': tool_args,
                    'result': result
                })
                
                # Добавляем результат в сообщения
                messages.append({
                    'role': 'tool',
                    'tool_call_id': tool_call['id'],
                    'content': result
                })
        else:
            # Нет вызовов инструментов — это финальный ответ
            answer = response['choices'][0]['message']['content']
            source = extract_source_from_conversation(messages, tool_calls_log)
            
            return {
                'answer': answer,
                'source': source,
                'tool_calls': tool_calls_log
            }
    
    # Если превысили лимит вызовов
    return {
        'answer': 'Reached maximum tool calls without final answer',
        'source': '',
        'tool_calls': tool_calls_log
    }