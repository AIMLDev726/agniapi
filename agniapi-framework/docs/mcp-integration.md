# MCP Integration Guide

Agni API provides built-in support for the Model Context Protocol (MCP), enabling seamless AI integration.

## What is MCP?

The Model Context Protocol (MCP) is a standardized way for AI models to interact with external tools, resources, and data sources. Agni API includes:

- **MCP Server**: Expose your API as tools and resources for AI models
- **MCP Client**: Connect to other MCP servers
- **Automatic Registration**: Use decorators to register tools and resources

## Enabling MCP

Enable MCP when creating your application:

```python
from agniapi import AgniAPI

app = AgniAPI(
    mcp_enabled=True,
    mcp_server_name="my-api-server"
)
```

## MCP Tools

Tools are functions that AI models can call to perform actions.

### Basic Tool

```python
from agniapi import mcp_tool

@mcp_tool("get_weather", "Get weather information for a city")
async def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    # Your weather API logic here
    return {
        "city": city,
        "temperature": "22°C",
        "condition": "sunny",
        "humidity": "65%"
    }
```

### Tool with Complex Parameters

```python
from typing import List, Optional

@mcp_tool("search_users", "Search for users in the database")
async def search_users(
    query: str,
    limit: int = 10,
    active_only: bool = True,
    roles: Optional[List[str]] = None
) -> List[dict]:
    """Search for users with various filters."""
    # Your search logic here
    return [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"}
    ]
```

### Tool with Custom Schema

```python
@mcp_tool(
    name="calculate_metrics",
    description="Calculate business metrics",
    input_schema={
        "type": "object",
        "properties": {
            "metric_type": {
                "type": "string",
                "enum": ["revenue", "users", "engagement"]
            },
            "date_range": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "format": "date"},
                    "end": {"type": "string", "format": "date"}
                }
            }
        },
        "required": ["metric_type"]
    }
)
async def calculate_metrics(metric_type: str, date_range: dict = None) -> dict:
    """Calculate various business metrics."""
    # Your metrics calculation logic
    return {"metric": metric_type, "value": 12345}
```

## MCP Resources

Resources provide access to data that AI models can read.

### Basic Resource

```python
from agniapi import mcp_resource
import json

@mcp_resource(
    uri="database://users",
    name="User Database",
    description="Complete user database with profiles",
    mime_type="application/json"
)
async def users_database() -> str:
    """Provide access to user database."""
    users = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"}
    ]
    return json.dumps(users, indent=2)
```

### File Resource

```python
@mcp_resource(
    uri="file://logs/application.log",
    name="Application Logs",
    description="Recent application log entries",
    mime_type="text/plain"
)
async def application_logs() -> str:
    """Provide access to application logs."""
    # Read from actual log file or database
    logs = [
        "2024-01-01 10:00:00 INFO: Application started",
        "2024-01-01 10:01:00 INFO: User logged in",
        "2024-01-01 10:02:00 WARN: High memory usage"
    ]
    return "\n".join(logs)
```

### Dynamic Resource

```python
@mcp_resource(
    uri="api://stats/realtime",
    name="Real-time Statistics",
    description="Live application statistics"
)
async def realtime_stats() -> str:
    """Provide real-time statistics."""
    from datetime import datetime
    
    stats = {
        "timestamp": datetime.now().isoformat(),
        "active_users": 42,
        "requests_per_minute": 150,
        "error_rate": 0.02
    }
    return json.dumps(stats, indent=2)
```

## MCP Prompts

Prompts are templates that help AI models generate better responses.

### Basic Prompt

```python
from agniapi import mcp_prompt

@mcp_prompt("code_review", "Generate a code review prompt")
async def code_review_prompt(
    code: str,
    language: str = "python",
    focus: str = "general"
) -> dict:
    """Generate a prompt for code review."""
    return {
        "messages": [
            {
                "role": "system",
                "content": f"You are an expert {language} developer performing code reviews."
            },
            {
                "role": "user",
                "content": f"Please review this {language} code with focus on {focus}:\n\n{code}"
            }
        ]
    }
```

### Complex Prompt with Context

```python
@mcp_prompt("api_documentation", "Generate API documentation")
async def api_docs_prompt(
    endpoint: str,
    method: str = "GET",
    include_examples: bool = True
) -> dict:
    """Generate documentation for an API endpoint."""
    
    # Get endpoint information from your API
    endpoint_info = get_endpoint_info(endpoint, method)
    
    context = f"Endpoint: {method} {endpoint}\n"
    context += f"Parameters: {endpoint_info.get('parameters', 'None')}\n"
    context += f"Response: {endpoint_info.get('response_schema', 'Unknown')}"
    
    messages = [
        {
            "role": "system",
            "content": "You are a technical writer creating API documentation."
        },
        {
            "role": "user",
            "content": f"Create comprehensive documentation for this API endpoint:\n\n{context}"
        }
    ]
    
    if include_examples:
        messages.append({
            "role": "user",
            "content": "Include practical examples and common use cases."
        })
    
    return {"messages": messages}
```

## Running MCP Server

### Stdio Transport (Most Common)

```python
# In your main application file
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        # Run as MCP server
        import asyncio
        asyncio.run(app.mcp_server.run_stdio())
    else:
        # Run as regular API
        app.run(debug=True)
```

Run as MCP server:
```bash
python main.py mcp
```

### Using CLI

```bash
# Run MCP server with stdio
agniapi mcp --transport stdio

# Run MCP server with SSE
agniapi mcp --transport sse --host localhost --port 8080

# Run MCP server with WebSocket
agniapi mcp --transport websocket --host localhost --port 8080
```

### SSE Transport

```python
# For web-based AI clients
async def run_mcp_sse():
    await app.mcp_server.run_sse(host="localhost", port=8080)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_mcp_sse())
```

### WebSocket Transport

```python
# For real-time applications
async def run_mcp_websocket():
    await app.mcp_server.run_websocket(host="localhost", port=8080)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_mcp_websocket())
```

## MCP Client Usage

Connect to other MCP servers from your application:

```python
from agniapi.mcp import MCPClient

# Create client
mcp_client = MCPClient()

# Connect to external MCP server
await mcp_client.connect_stdio(
    "external_server",
    "python",
    ["external_mcp_server.py"]
)

# List available tools
tools = await mcp_client.list_tools("external_server")
print(f"Available tools: {[tool.name for tool in tools]}")

# Call a tool
result = await mcp_client.call_tool(
    "external_server",
    "get_data",
    {"query": "users"}
)
print(f"Tool result: {result}")

# Read a resource
content = await mcp_client.read_resource(
    "external_server",
    "database://config"
)
print(f"Resource content: {content}")
```

## Integration with Regular API

Combine MCP tools with regular API endpoints:

```python
@mcp_tool("get_user_analytics", "Get user analytics data")
async def get_user_analytics(user_id: int) -> dict:
    """Get analytics for a specific user."""
    # Your analytics logic
    return {
        "user_id": user_id,
        "page_views": 150,
        "session_duration": "5m 30s",
        "last_active": "2024-01-01T10:00:00Z"
    }

# Also expose as regular API endpoint
@app.get("/analytics/users/{user_id}")
async def user_analytics_api(user_id: int):
    """Regular API endpoint using the same logic."""
    return await get_user_analytics(user_id)
```

## Best Practices

### 1. Tool Design

- **Single Purpose**: Each tool should do one thing well
- **Clear Names**: Use descriptive names like `get_weather` not `tool1`
- **Good Descriptions**: Help AI models understand when to use the tool
- **Type Hints**: Always use type hints for parameters and return values

### 2. Resource Organization

- **Logical URIs**: Use meaningful URIs like `database://users` or `file://logs/app.log`
- **Appropriate MIME Types**: Use correct MIME types for content
- **Fresh Data**: Ensure resources return current data
- **Access Control**: Consider security for sensitive resources

### 3. Error Handling

```python
@mcp_tool("safe_operation", "Perform operation with error handling")
async def safe_operation(param: str) -> dict:
    """Tool with proper error handling."""
    try:
        # Your operation logic
        result = perform_operation(param)
        return {"success": True, "result": result}
    except ValueError as e:
        return {"success": False, "error": f"Invalid parameter: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Operation failed: {e}"}
```

### 4. Performance

- **Async Operations**: Use async/await for I/O operations
- **Caching**: Cache expensive operations when appropriate
- **Timeouts**: Set reasonable timeouts for external calls
- **Resource Limits**: Limit resource size and tool execution time

## Security Considerations

### 1. Authentication

```python
from agniapi import Depends
from agniapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    # Validate token and return user
    return {"user_id": 1, "permissions": ["read", "write"]}

@mcp_tool("secure_operation", "Secure operation requiring auth")
async def secure_operation(
    data: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Tool that requires authentication."""
    if "write" not in current_user["permissions"]:
        return {"error": "Insufficient permissions"}
    
    # Perform operation
    return {"success": True, "user": current_user["user_id"]}
```

### 2. Input Validation

```python
@mcp_tool("validated_tool", "Tool with input validation")
async def validated_tool(email: str, age: int) -> dict:
    """Tool with proper input validation."""
    import re
    
    # Validate email
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return {"error": "Invalid email format"}
    
    # Validate age
    if age < 0 or age > 150:
        return {"error": "Invalid age range"}
    
    return {"email": email, "age": age, "valid": True}
```

### 3. Rate Limiting

```python
from collections import defaultdict
from datetime import datetime, timedelta

# Simple rate limiting
call_counts = defaultdict(list)

@mcp_tool("rate_limited_tool", "Tool with rate limiting")
async def rate_limited_tool(user_id: str, data: str) -> dict:
    """Tool with rate limiting."""
    now = datetime.now()
    
    # Clean old calls
    call_counts[user_id] = [
        call_time for call_time in call_counts[user_id]
        if now - call_time < timedelta(minutes=1)
    ]
    
    # Check rate limit (10 calls per minute)
    if len(call_counts[user_id]) >= 10:
        return {"error": "Rate limit exceeded"}
    
    # Record this call
    call_counts[user_id].append(now)
    
    # Perform operation
    return {"data": data, "timestamp": now.isoformat()}
```

## Debugging MCP

### 1. Logging

```python
import logging

# Enable MCP logging
logging.basicConfig(level=logging.DEBUG)
mcp_logger = logging.getLogger("agniapi.mcp")

@mcp_tool("debug_tool", "Tool with debugging")
async def debug_tool(param: str) -> dict:
    """Tool with debug logging."""
    mcp_logger.info(f"Tool called with param: {param}")
    
    try:
        result = process_param(param)
        mcp_logger.info(f"Tool result: {result}")
        return result
    except Exception as e:
        mcp_logger.error(f"Tool error: {e}")
        raise
```

### 2. Testing MCP Tools

```python
import pytest
from agniapi.testing import TestClient

@pytest.mark.asyncio
async def test_mcp_tool():
    """Test MCP tool functionality."""
    # Test the tool directly
    result = await get_weather("London")
    assert result["city"] == "London"
    assert "temperature" in result
    
    # Test via API if exposed
    client = TestClient(app)
    response = client.get("/weather/London")
    assert response.status_code == 200
```

## Examples

Check the `examples/mcp_server_example.py` file for a complete working example that demonstrates:

- Multiple MCP tools with different parameter types
- Resources with various data sources
- Prompts for different use cases
- Integration with regular API endpoints
- Error handling and validation

This comprehensive MCP integration makes Agni API uniquely suited for AI-powered applications!
