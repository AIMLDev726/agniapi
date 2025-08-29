# Migration Guide

This guide helps you migrate from Flask or FastAPI to Agni API.

## From Flask to Agni API

Agni API maintains Flask's familiar patterns while adding modern features.

### Basic Application

**Flask:**
```python
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({"message": "Hello World"})

@app.route('/users/<int:user_id>')
def get_user(user_id):
    return jsonify({"user_id": user_id})

if __name__ == '__main__':
    app.run(debug=True)
```

**Agni API:**
```python
from agniapi import AgniAPI

app = AgniAPI()

@app.get('/')
async def hello():
    return {"message": "Hello World"}

@app.get('/users/{user_id}')
async def get_user(user_id: int):
    return {"user_id": user_id}

if __name__ == '__main__':
    app.run(debug=True)
```

### Request Handling

**Flask:**
```python
from flask import request, jsonify

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    
    # Manual validation
    if not name or not email:
        return jsonify({"error": "Missing fields"}), 400
    
    return jsonify({"name": name, "email": email})
```

**Agni API:**
```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str

@app.post('/users')
async def create_user(user: User):
    # Automatic validation
    return {"name": user.name, "email": user.email}
```

### Blueprints

**Flask:**
```python
from flask import Blueprint

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
def list_users():
    return jsonify({"users": []})

app.register_blueprint(users_bp)
```

**Agni API:**
```python
from agniapi import Blueprint

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.get('/')
async def list_users():
    return {"users": []}

app.register_blueprint(users_bp)
```

### Error Handling

**Flask:**
```python
from flask import abort

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.route('/items/<int:item_id>')
def get_item(item_id):
    if item_id == 0:
        abort(404)
    return jsonify({"item_id": item_id})
```

**Agni API:**
```python
from agniapi import HTTPException

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Not found"}

@app.get('/items/{item_id}')
async def get_item(item_id: int):
    if item_id == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item_id": item_id}
```

### Authentication

**Flask:**
```python
from flask import request, jsonify
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token required"}), 401
        # Validate token...
        return f(*args, **kwargs)
    return decorated

@app.route('/protected')
@require_auth
def protected():
    return jsonify({"message": "Protected"})
```

**Agni API:**
```python
from agniapi import Depends
from agniapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    # Validate token...
    return {"user": "authenticated"}

@app.get('/protected')
async def protected(user = Depends(get_current_user)):
    return {"message": "Protected", "user": user}
```

## From FastAPI to Agni API

Agni API is largely compatible with FastAPI syntax.

### Basic Application

**FastAPI:**
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

**Agni API:**
```python
from agniapi import AgniAPI

app = AgniAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

### Pydantic Models

**FastAPI:**
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = False

@app.post("/items/")
async def create_item(item: Item):
    return item
```

**Agni API:**
```python
from agniapi import AgniAPI
from pydantic import BaseModel

app = AgniAPI()

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = False

@app.post("/items/")
async def create_item(item: Item):
    return item
```

### Dependencies

**FastAPI:**
```python
from fastapi import Depends

async def common_parameters(q: str = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
async def read_items(commons: dict = Depends(common_parameters)):
    return commons
```

**Agni API:**
```python
from agniapi import Depends

async def common_parameters(q: str = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
async def read_items(commons: dict = Depends(common_parameters)):
    return commons
```

### Security

**FastAPI:**
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    # Validate token
    return {"user": "current"}

@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
```

**Agni API:**
```python
from agniapi import Depends, HTTPException
from agniapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    # Validate token
    return {"user": "current"}

@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
```

## Key Differences and Additions

### 1. Blueprint Support (vs FastAPI)

Agni API adds Flask-style blueprints that FastAPI doesn't have:

```python
from agniapi import Blueprint

# This is unique to Agni API
users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.get('/')
async def list_users():
    return {"users": []}

app.register_blueprint(users_bp)
```

### 2. MCP Integration (New Feature)

Both Flask and FastAPI lack built-in MCP support:

```python
from agniapi import mcp_tool, mcp_resource

# Enable MCP server
app = AgniAPI(mcp_enabled=True)

@mcp_tool("get_weather", "Get weather information")
async def get_weather(city: str) -> dict:
    return {"city": city, "temperature": "22°C"}

@mcp_resource("data://users", "User Database")
async def users_resource() -> str:
    return json.dumps(users_data)
```

### 3. Unified WSGI/ASGI Support

Unlike FastAPI (ASGI only) or Flask (WSGI only), Agni API supports both:

```python
# Works with both WSGI and ASGI servers
app = AgniAPI()

# ASGI (recommended)
# uvicorn main:app

# WSGI (for legacy compatibility)
# gunicorn main:app
```

## Migration Checklist

### From Flask

- [ ] Replace `Flask` with `AgniAPI`
- [ ] Add type hints to route functions
- [ ] Convert `@app.route()` to specific HTTP method decorators
- [ ] Replace `jsonify()` with direct dictionary returns
- [ ] Update error handling to use `HTTPException`
- [ ] Convert request parsing to Pydantic models
- [ ] Update authentication to use dependency injection
- [ ] Add `async`/`await` for better performance

### From FastAPI

- [ ] Replace `FastAPI` with `AgniAPI`
- [ ] Consider using blueprints for better organization
- [ ] Enable MCP if you need AI integration
- [ ] Update imports from `fastapi` to `agniapi`
- [ ] Test WebSocket functionality (may have slight differences)

## Common Pitfalls

### 1. Async/Await

**Wrong:**
```python
@app.get('/')
def sync_handler():  # Sync function
    return {"message": "Hello"}
```

**Right:**
```python
@app.get('/')
async def async_handler():  # Async function
    return {"message": "Hello"}
```

### 2. Import Paths

**Wrong:**
```python
from fastapi import HTTPException  # Old import
```

**Right:**
```python
from agniapi import HTTPException  # New import
```

### 3. Response Types

**Wrong:**
```python
from flask import jsonify

@app.get('/')
async def handler():
    return jsonify({"message": "Hello"})  # Unnecessary
```

**Right:**
```python
@app.get('/')
async def handler():
    return {"message": "Hello"}  # Direct return
```

## Testing Migration

Update your tests to use Agni API's test client:

**Before:**
```python
# Flask
from flask import Flask
app = Flask(__name__)
client = app.test_client()

# FastAPI
from fastapi.testclient import TestClient
client = TestClient(app)
```

**After:**
```python
from agniapi.testing import TestClient
client = TestClient(app)
```

## Performance Considerations

1. **Use async/await**: Better performance than sync functions
2. **Enable MCP selectively**: Only if you need AI integration
3. **Use appropriate middleware**: Only add what you need
4. **Consider caching**: Use dependency caching for expensive operations

## Getting Help

If you encounter issues during migration:

1. Check the [API Reference](api-reference.md)
2. Look at [Examples](../examples/) for patterns
3. Open an issue on GitHub
4. Join our community discussions

The migration should be straightforward, and you'll gain access to powerful new features like MCP integration and unified WSGI/ASGI support!
