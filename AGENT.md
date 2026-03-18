## Task 3: System Agent Features

### New Tool: query_api
The agent can now query the live backend API to get real data and diagnose issues.

**Parameters:**
- `method`: HTTP method (GET, POST, etc.)
- `path`: API endpoint path
- `body`: Optional JSON body for POST/PUT

**Authentication:**
- Uses `LMS_API_KEY` from `.env.docker.secret`
- Base URL from `AGENT_API_BASE_URL` (default: http://localhost:42002)

### Decision Making
The system prompt has been enhanced to help the LLM choose the right tool:
- Wiki questions → `list_files` + `read_file` on `wiki/`
- Code questions → `read_file` on `.py` files
- Data/API questions → `query_api`
- Bug diagnosis → `query_api` first, then `read_file`

### Benchmark Results
After implementing `query_api` and iterating through the local benchmark:
