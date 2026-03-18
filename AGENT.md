# Agent Documentation for Task 2

## Overview
This agent answers questions by reading documentation from the `wiki/` folder.
It uses tools and an agentic loop to find information.

## Version
- Version 2.0 (Task 2) - Added tools and agentic loop
- Version 1.0 (Task 1) - Basic LLM calls

## Tools

### read_file(path)
Reads a file from the project.
- **path**: relative path from project root
- **Returns**: file contents or error message

### list_files(path)
Lists files in a directory.
- **path**: relative directory path
- **Returns**: newline-separated list (directories end with /)

## Agentic Loop
1. Send question + tool definitions to LLM
2. If LLM calls tools → execute them, add results, repeat
3. If LLM gives text answer → that's final
4. Maximum 10 iterations

## Output Format
```json
{
  "answer": "The answer text",
  "source": "wiki/filename.md#section",
  "tool_calls": [
    {
      "tool": "read_file",
      "args": {"path": "wiki/file.md"},
      "result": "file contents..."
    }
  ]
}
