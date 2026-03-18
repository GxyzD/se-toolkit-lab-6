# Implementation Plan for Task 2: The Documentation Agent

## 1. What I'm building
I will upgrade the agent from Task 1 to use tools and an agentic loop.
The agent will be able to read files from the wiki/ directory to answer questions.

## 2. Tools to implement

### 2.1 read_file(path)
- Read a file from the project
- Parameters: path (string) - relative path from project root
- Returns: file contents or error message
- Security: must not read files outside project (block ..)

### 2.2 list_files(path)
- List contents of a directory
- Parameters: path (string) - relative directory path
- Returns: newline-separated listing
- Security: must not list directories outside project

## 3. Agentic Loop design
- Maximum 10 iterations
- Send question + tool definitions to LLM
- If LLM wants to call tools → execute them, add results to conversation
- If LLM gives text answer → that's final, extract source
- Log all tool calls

## 4. LLM Provider
I will use the same Qwen API on VM:
- API Base: http://10.93.26.116:42005/v1
- Model: qwen3-coder-plus
- Key in .env.agent.secret

## 5. Security
- Use Path.resolve() to check paths
- Block any path with '..'
- Check that resolved path starts with project root

## 6. Testing
Two new tests:
1. Question about merge conflicts → should call read_file
2. Question about wiki contents → should call list_files

## 7. Documentation
Update AGENT.md to describe:
- New tools
- Agentic loop
- Source field