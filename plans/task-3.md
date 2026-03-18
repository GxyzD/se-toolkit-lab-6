# Implementation Plan for Task 3: The System Agent

## 1. Overview
In Task 2, I built an agent that can read documentation from the `wiki/` directory. For Task 3, I will extend it with a new tool — `query_api` — so it can interact with the deployed backend service. This will allow the agent to answer questions about live data (item counts, scores) and diagnose system issues by combining API responses with source code reading.

## 2. New Tool: query_api

### 2.1 Tool Definition
I will add a new function-calling schema to the existing `TOOLS` list in `agent.py`:

```python
{
    "type": "function",
    "function": {
        "name": "query_api",
        "description": "Send HTTP request to the deployed backend API",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                    "description": "HTTP method"
                },
                "path": {
                    "type": "string",
                    "description": "API endpoint path (e.g., /items/, /analytics/completion-rate?lab=lab-01)"
                },
                "body": {
                    "type": "string",
                    "description": "Optional JSON request body for POST/PUT requests"
                }
            },
            "required": ["method", "path"]
        }
    }
}