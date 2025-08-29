# Agni API

A unified REST API framework that combines the best features of Flask and FastAPI with built-in Model Context Protocol (MCP) support.

## Features

### 🔥 **Unified Framework**
- **Flask-style** blueprints and routing
- **FastAPI-style** async support and type hints
- **Seamless integration** between sync and async code
- **Automatic API documentation** with OpenAPI/Swagger

### ⚡ **High Performance**
- Full async/await support
- ASGI and WSGI compatibility
- Optimized request handling
- Built-in middleware system

### 🤖 **Built-in MCP Support**
- **MCP Server** capabilities out of the box
- **MCP Client** for connecting to other servers
- **Easy tool registration** with decorators
- **Resource and prompt management**

### 🛡️ **Security First**
- OAuth2, JWT, and API key authentication
- Built-in security schemes
- CORS, HTTPS redirect, and trusted host middleware
- Password hashing utilities

### 🧪 **Developer Experience**
- **Type hints** throughout
- **Dependency injection** system
- **WebSocket** support
- **Testing utilities** for both sync and async
- **CLI tools** for development

## Quick Start

### Installation

```bash
pip install agniapi
```

For MCP support:
```bash
pip install agniapi[mcp]
```

For development:
```bash
pip install agniapi[dev]
```

### Basic Application

```python
from agniapi import AgniAPI, JSONResponse

app = AgniAPI(title="My API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Hello, World!"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": f"User {user_id}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

**Access your API:**
- **API**: http://localhost:8000
- **OpenAPI Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Run the Example

```bash
# Try the complete example
python examples/simple_api.py
```

### With Type Validation

```python
from agniapi import AgniAPI
from pydantic import BaseModel

app = AgniAPI()

class User(BaseModel):
    name: str
    email: str
    age: int

@app.post("/users")
async def create_user(user: User):
    return {"message": f"Created user {user.name}"}
```

### Flask-style Blueprints

```python
from agniapi import AgniAPI, Blueprint

app = AgniAPI()
users_bp = Blueprint("users", __name__, url_prefix="/users")

@users_bp.get("/")
async def list_users():
    return {"users": []}

@users_bp.post("/")
async def create_user():
    return {"message": "User created"}

app.register_blueprint(users_bp)
```

### MCP Integration

```python
from agniapi import AgniAPI, mcp_tool, mcp_resource

app = AgniAPI(mcp_enabled=True)

@mcp_tool("get_weather", "Get weather information")
async def get_weather(location: str) -> dict:
    return {"location": location, "temperature": "22°C", "condition": "sunny"}

@mcp_resource("database://users", "User Database")
async def get_users_resource() -> list:
    return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

@app.get("/")
async def root():
    return {"message": "API with MCP support"}
```

### Dependency Injection

```python
from agniapi import AgniAPI, Depends

app = AgniAPI()

async def get_database():
    # Database connection logic
    return {"db": "connected"}

async def get_current_user(db = Depends(get_database)):
    # User authentication logic
    return {"user": "authenticated"}

@app.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"message": f"Hello {user['user']}"}
```

### WebSocket Support

```python
from agniapi import AgniAPI
from agniapi.websockets import WebSocket

app = AgniAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except:
        pass
```

## CLI Usage

### Create a new project

```bash
agniapi new my-project
cd my-project
pip install -r requirements.txt
```

### Run development server

```bash
agniapi run --reload --debug
```

### Generate OpenAPI documentation

```bash
agniapi openapi --output api-spec.json
```

### List all routes

```bash
agniapi routes
```

### Run MCP server

```bash
agniapi mcp --transport stdio
agniapi mcp --transport sse --host localhost --port 8080
agniapi mcp --transport websocket --host localhost --port 8080
```

### Run tests

```bash
agniapi test --coverage
```

## Advanced Features

### Middleware

```python
from agniapi import AgniAPI
from agniapi.middleware import CORSMiddleware

app = AgniAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Security

```python
from agniapi import AgniAPI, Depends
from agniapi.security import HTTPBearer, JWTManager

app = AgniAPI()
security = HTTPBearer()
jwt_manager = JWTManager("your-secret-key")

async def get_current_user(token: str = Depends(security)):
    payload = jwt_manager.verify_token(token)
    return payload

@app.get("/protected")
async def protected(user = Depends(get_current_user)):
    return {"user": user}
```

### Testing

```python
from agniapi.testing import TestClient
from main import app

def test_api():
    client = TestClient(app)
    
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}
    
    # Async testing
    async def test_async():
        response = await client.aget("/users/1")
        assert response.status_code == 200
```

## Comparison with Flask and FastAPI

| Feature | Flask | FastAPI | Agni API |
|---------|-------|---------|----------|
| Async Support | ❌ | ✅ | ✅ |
| Type Hints | ❌ | ✅ | ✅ |
| Auto Documentation | ❌ | ✅ | ✅ |
| Blueprints | ✅ | ❌ | ✅ |
| Dependency Injection | ❌ | ✅ | ✅ |
| WebSocket Support | ❌ | ✅ | ✅ |
| MCP Support | ❌ | ❌ | ✅ |
| WSGI Compatible | ✅ | ❌ | ✅ |
| ASGI Compatible | ❌ | ✅ | ✅ |

## Migration Guides

### From Flask

```python
# Flask
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/users/<int:user_id>')
def get_user(user_id):
    return jsonify({"user_id": user_id})

# Agni API
from agniapi import AgniAPI

app = AgniAPI()

@app.get('/users/{user_id}')
async def get_user(user_id: int):
    return {"user_id": user_id}
```

### From FastAPI

```python
# FastAPI
from fastapi import FastAPI

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}

# Agni API (same syntax!)
from agniapi import AgniAPI

app = AgniAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
```

## Documentation

- **API Reference**: [docs.agniapi.dev](https://docs.agniapi.dev)
- **User Guide**: [docs.agniapi.dev/guide](https://docs.agniapi.dev/guide)
- **MCP Integration**: [docs.agniapi.dev/mcp](https://docs.agniapi.dev/mcp)
- **Examples**: [github.com/agniapi/examples](https://github.com/agniapi/examples)

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Flask** - For the blueprint system and WSGI patterns
- **FastAPI** - For async support and type validation patterns  
- **Starlette** - For ASGI implementation
- **Pydantic** - For data validation
- **MCP** - For the Model Context Protocol specification
