# Getting Started with Agni API

Welcome to Agni API! This guide will help you get up and running with the framework quickly.

## What is Agni API?

Agni API is a unified REST API framework that combines the best features of Flask and FastAPI with built-in Model Context Protocol (MCP) support. It provides:

- **Flask-style** blueprints and routing patterns
- **FastAPI-style** async support and automatic type validation
- **Built-in MCP server** capabilities for AI integration
- **Seamless WSGI/ASGI** compatibility
- **Comprehensive security** features

## Installation

### Basic Installation

```bash
pip install agniapi
```

### With Optional Dependencies

```bash
# For MCP support
pip install agniapi[mcp]

# For JWT authentication
pip install agniapi[jwt]

# For development tools
pip install agniapi[dev]

# For production server
pip install agniapi[server]

# Install everything
pip install agniapi[all]
```

## Your First Application

Create a file called `main.py`:

```python
from agniapi import AgniAPI

app = AgniAPI(title="My First API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Hello, Agni API!"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}

if __name__ == "__main__":
    app.run(debug=True)
```

Run your application:

```bash
python main.py
```

Your API will be available at `http://127.0.0.1:8000`.

## Interactive Documentation

Agni API automatically generates interactive API documentation:

- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`
- **OpenAPI JSON**: `http://127.0.0.1:8000/openapi.json`

## Using the CLI

Agni API includes a powerful CLI tool for development:

### Create a New Project

```bash
agniapi new my-project
cd my-project
pip install -r requirements.txt
```

### Run Development Server

```bash
agniapi run --reload --debug
```

### Generate OpenAPI Specification

```bash
agniapi openapi --output api-spec.json
```

### List Routes

```bash
agniapi routes
```

## Key Concepts

### 1. Type Validation with Pydantic

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    age: int

@app.post("/users")
async def create_user(user: User):
    return {"message": f"Created user {user.name}"}
```

### 2. Dependency Injection

```python
from agniapi import Depends

async def get_database():
    return {"db": "connected"}

@app.get("/items")
async def read_items(db = Depends(get_database)):
    return {"items": [], "db": db}
```

### 3. Flask-style Blueprints

```python
from agniapi import Blueprint

users_bp = Blueprint("users", __name__, url_prefix="/users")

@users_bp.get("/")
async def list_users():
    return {"users": []}

app.register_blueprint(users_bp)
```

### 4. WebSocket Support

```python
from agniapi.websockets import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
```

### 5. MCP Integration

```python
from agniapi import mcp_tool

@mcp_tool("get_weather", "Get weather information")
async def get_weather(city: str) -> dict:
    return {"city": city, "temperature": "22°C"}

# Enable MCP server
app = AgniAPI(mcp_enabled=True)
```

## Authentication

### JWT Authentication

```python
from agniapi.security import HTTPBearer, JWTManager

security = HTTPBearer()
jwt_manager = JWTManager("your-secret-key")

async def get_current_user(token: str = Depends(security)):
    payload = jwt_manager.verify_token(token)
    return payload

@app.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"user": user}
```

### API Key Authentication

```python
from agniapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

@app.get("/protected")
async def protected_route(api_key: str = Depends(api_key_header)):
    # Validate API key
    return {"message": "Access granted"}
```

## Middleware

```python
from agniapi.middleware import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Error Handling

```python
from agniapi import HTTPException

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    if item_id == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item_id": item_id}

# Custom error handler
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Resource not found", "path": request.path}
```

## Testing

```python
from agniapi.testing import TestClient

def test_read_main():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Agni API!"}

# Async testing
async def test_async():
    async with TestClient(app) as client:
        response = await client.aget("/")
        assert response.status_code == 200
```

## Next Steps

- Read the [API Reference](api-reference.md) for detailed documentation
- Check out [Examples](../examples/) for more complex applications
- Learn about [MCP Integration](mcp-integration.md) for AI capabilities
- Explore [Migration Guides](migration.md) if coming from Flask or FastAPI

## Getting Help

- **Documentation**: [docs.agniapi.dev](https://docs.agniapi.dev)
- **GitHub Issues**: [github.com/agniapi/agniapi/issues](https://github.com/agniapi/agniapi/issues)
- **Discussions**: [github.com/agniapi/agniapi/discussions](https://github.com/agniapi/agniapi/discussions)

## What's Next?

Now that you have a basic understanding of Agni API, you can:

1. **Explore Examples**: Check out the `examples/` directory for comprehensive applications
2. **Add Authentication**: Implement JWT or API key authentication
3. **Use Blueprints**: Organize your application with modular blueprints
4. **Enable MCP**: Add AI capabilities with built-in MCP support
5. **Deploy**: Use the production server options for deployment

Happy coding with Agni API! 🔥
