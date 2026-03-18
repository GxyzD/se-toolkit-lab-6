## Task 3: System Agent Features

### New Tool: query_api
The agent can now query the live backend API to get real data and diagnose issues.

**Parameters:**
- `method`: HTTP method (GET, POST, etc.)
- `path`: API endpoint path
- `body`: Optional JSON body for POST/PUT
- `auth`: Whether to include authentication header (default: true)

**Authentication:**
- Uses `LMS_API_KEY` from `.env.docker.secret`
- Base URL from `AGENT_API_BASE_URL` (default: http://localhost:42002)

### Decision Making
The system prompt has been enhanced to help the LLM choose the right tool:
- Wiki questions → `list_files` + `read_file` on `wiki/`
- Code questions → `read_file` on `.py` files
- Data/API questions → `query_api`
- Bug diagnosis → `query_api` first, then `read_file`

### Bug Detection Checklist
When asked about bugs or risky code, the agent is instructed to actively look for:
1. **Division operations** (`a / b`) - check if divisor could be zero (ZeroDivisionError risk)
2. **None-unsafe operations** - sorting, comparisons, or arithmetic on values that could be None
3. **Missing error handling** - operations that could fail without try/except
4. **SQL queries without NULL checks** - look for `.score`, `.avg()`, etc. without `.is_not(None)`
5. **Sorting with None values** - `sorted(rows, key=lambda r: r.field)` fails if field is None

For example, in `analytics.py`, the completion-rate endpoint has a division by zero risk:
```python
rate = (passed_learners / total_learners) * 100  # Fails if total_learners is 0
```

And the top-learners endpoint has a None-unsafe sort:
```python
ranked = sorted(rows, key=lambda r: r.avg_score, reverse=True)  # Fails if avg_score is None
```

### Error Handling Comparison
When asked to compare error handling between modules (e.g., ETL vs API routers), the agent:
1. Reads both files completely before answering
2. Looks for: try/except blocks, HTTPException usage, raise_for_status(), error return values
3. Compares patterns: ETL uses exceptions that propagate; API routers use HTTPException with status codes

**ETL Pipeline (`etl.py`):**
- Uses `raise_for_status()` to propagate HTTP errors
- Relies on exception propagation for error handling
- Returns structured data on success

**API Routers (`items.py`, etc.):**
- Uses `HTTPException` with proper HTTP status codes (404, 422, etc.)
- Catches `IntegrityError` and converts to HTTP 422
- Returns structured error responses with status codes

### Benchmark Results
After implementing `query_api` and iterating through the local benchmark:
