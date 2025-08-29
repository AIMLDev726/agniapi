# API Reference

Complete reference for Agni API framework components.

## Core Classes

### AgniAPI

The main application class that combines Flask and FastAPI patterns.

```python
class AgniAPI:
    def __init__(
        self,
        title: str = "Agni API",
        description: str = "",
        version: str = "1.0.0",
        debug: bool = False,
        mcp_enabled: bool = False,
        mcp_server_name: str = "agni-api-server",
        **kwargs
    )
```

**Parameters:**
- `title`: Application title for OpenAPI documentation
- `description`: Application description
- `version`: Application version
- `debug`: Enable debug mode
- `mcp_enabled`: Enable MCP server capabilities
- `mcp_server_name`: Name for the MCP server

**Methods:**

#### Route Decorators

```python
@app.get(path, **kwargs)
@app.post(path, **kwargs)
@app.put(path, **kwargs)
@app.delete(path, **kwargs)
@app.patch(path, **kwargs)
@app.options(path, **kwargs)
@app.head(path, **kwargs)
```

#### Flask-style Route Registration

```python
app.route(rule, methods=None, **kwargs)
app.add_url_rule(rule, endpoint=None, view_func=None, **kwargs)
```

#### Blueprint Registration

```python
app.register_blueprint(blueprint, **options)
```

#### Middleware

```python
app.add_middleware(middleware_class, **kwargs)
```

#### Error Handlers

```python
app.exception_handler(exc_class_or_status_code)
```

#### WebSocket

```python
app.websocket(path, **kwargs)
```

#### Server

```python
app.run(host="127.0.0.1", port=8000, debug=None, **kwargs)
```

### Blueprint

Flask-style blueprint for organizing routes.

```python
class Blueprint:
    def __init__(
        self,
        name: str,
        import_name: str,
        url_prefix: str = None,
        subdomain: str = None,
        url_defaults: Dict[str, Any] = None,
        static_folder: str = None,
        static_url_path: str = None,
        template_folder: str = None,
        root_path: str = None,
        tags: List[str] = None,
        dependencies: List[Dependency] = None,
        responses: Dict[Union[int, str], Dict[str, Any]] = None,
    )
```

**Methods:**
- Same route decorators as `AgniAPI`
- `register(app, options=None)`: Register with application

## Request and Response

### Request

```python
class Request:
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    path_params: Dict[str, Any]
    cookies: Dict[str, str]
    
    async def body() -> bytes
    async def text() -> str
    async def json() -> Any
    async def form() -> Dict[str, Any]
    async def files() -> Dict[str, UploadFile]
```

### Response Classes

```python
class JSONResponse:
    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Dict[str, str] = None,
        media_type: str = "application/json"
    )

class HTMLResponse:
    def __init__(
        self,
        content: str,
        status_code: int = 200,
        headers: Dict[str, str] = None,
        media_type: str = "text/html"
    )

class PlainTextResponse:
    def __init__(
        self,
        content: str,
        status_code: int = 200,
        headers: Dict[str, str] = None,
        media_type: str = "text/plain"
    )

class RedirectResponse:
    def __init__(
        self,
        url: str,
        status_code: int = 307,
        headers: Dict[str, str] = None
    )

class FileResponse:
    def __init__(
        self,
        path: str,
        status_code: int = 200,
        headers: Dict[str, str] = None,
        media_type: str = None,
        filename: str = None
    )
```

## Dependency Injection

### Depends

```python
def Depends(
    dependency: Callable,
    use_cache: bool = True,
    scope: str = "request"
) -> Any
```

### Common Dependencies

```python
async def get_current_user(request: Request) -> Optional[Dict[str, Any]]
async def get_database() -> Dict[str, Any]
def require_auth(request: Request, user = Depends(get_current_user)) -> Dict[str, Any]
def require_admin(user = Depends(require_auth)) -> Dict[str, Any]
```

## Security

### Authentication Schemes

```python
class HTTPBasic:
    def __init__(self, realm: str = "Secure Area", auto_error: bool = True)

class HTTPBearer:
    def __init__(self, scheme_name: str = "Bearer", auto_error: bool = True)

class OAuth2PasswordBearer:
    def __init__(
        self,
        token_url: str,
        scheme_name: str = "OAuth2PasswordBearer",
        scopes: Dict[str, str] = None,
        auto_error: bool = True
    )

class APIKeyHeader:
    def __init__(self, name: str = "X-API-Key", auto_error: bool = True)

class APIKeyQuery:
    def __init__(self, name: str = "api_key", auto_error: bool = True)

class APIKeyCookie:
    def __init__(self, name: str = "api_key", auto_error: bool = True)
```

### JWT Manager

```python
class JWTManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256")
    
    def create_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str
    
    def verify_token(self, token: str) -> Dict[str, Any]
```

### Password Hashing

```python
class PasswordHasher:
    @staticmethod
    def hash_password(password: str, salt: str = None) -> str
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool
    
    @staticmethod
    def generate_salt() -> str
```

## WebSockets

### WebSocket

```python
class WebSocket:
    @property
    def client() -> Optional[str]
    @property
    def url() -> str
    @property
    def headers() -> Dict[str, str]
    @property
    def query_params() -> Dict[str, str]
    @property
    def cookies() -> Dict[str, str]
    
    async def accept(subprotocol: str = None, headers: Dict[str, str] = None)
    async def close(code: int = 1000, reason: str = "")
    async def send_text(data: str)
    async def send_bytes(data: bytes)
    async def send_json(data: Any, mode: str = "text")
    async def receive_text() -> str
    async def receive_bytes() -> bytes
    async def receive_json(mode: str = "text") -> Any
```

## MCP Integration

### Decorators

```python
@mcp_tool(name: str = None, description: str = "", input_schema: Dict = None)
@mcp_resource(uri: str = None, name: str = "", description: str = "", mime_type: str = "text/plain")
@mcp_prompt(name: str = None, description: str = "", arguments: List[Dict] = None)
```

### MCP Server

```python
class MCPServer:
    def __init__(
        self,
        name: str = "agni-api-server",
        version: str = "1.0.0",
        description: str = "Agni API MCP Server"
    )
    
    def register_tool(self, name: str, handler: Callable, description: str = "", input_schema: Dict = None)
    def register_resource(self, uri: str, handler: Callable, name: str = "", description: str = "", mime_type: str = "text/plain")
    def register_prompt(self, name: str, handler: Callable, description: str = "", arguments: List[Dict] = None)
    
    async def run_stdio()
    async def run_sse(host: str = "localhost", port: int = 8080)
    async def run_websocket(host: str = "localhost", port: int = 8080)
```

### MCP Client

```python
class MCPClient:
    async def connect_stdio(self, name: str, command: str, args: List[str] = None, env: Dict[str, str] = None)
    async def connect_sse(self, name: str, url: str, headers: Dict[str, str] = None)
    async def connect_websocket(self, name: str, url: str, headers: Dict[str, str] = None)
    
    async def list_tools(self, client_name: str) -> List[Tool]
    async def call_tool(self, client_name: str, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult
    async def list_resources(self, client_name: str) -> List[Resource]
    async def read_resource(self, client_name: str, uri: str) -> str
```

## Middleware

### Built-in Middleware

```python
class CORSMiddleware:
    def __init__(
        self,
        app,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        expose_headers: List[str] = None,
        max_age: int = 600
    )

class TrustedHostMiddleware:
    def __init__(
        self,
        app,
        allowed_hosts: List[str] = None,
        www_redirect: bool = True
    )

class GZipMiddleware:
    def __init__(
        self,
        app,
        minimum_size: int = 500,
        compresslevel: int = 9
    )

class HTTPSRedirectMiddleware:
    def __init__(self, app)

class RequestLoggingMiddleware:
    def __init__(self, app, logger=None)
```

## Testing

### TestClient

```python
class TestClient:
    def __init__(
        self,
        app: AgniAPI,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        root_path: str = ""
    )
    
    # Synchronous methods
    def get(self, url: str, **kwargs) -> httpx.Response
    def post(self, url: str, **kwargs) -> httpx.Response
    def put(self, url: str, **kwargs) -> httpx.Response
    def delete(self, url: str, **kwargs) -> httpx.Response
    def patch(self, url: str, **kwargs) -> httpx.Response
    def options(self, url: str, **kwargs) -> httpx.Response
    def head(self, url: str, **kwargs) -> httpx.Response
    
    # Asynchronous methods
    async def aget(self, url: str, **kwargs) -> httpx.Response
    async def apost(self, url: str, **kwargs) -> httpx.Response
    async def aput(self, url: str, **kwargs) -> httpx.Response
    async def adelete(self, url: str, **kwargs) -> httpx.Response
    async def apatch(self, url: str, **kwargs) -> httpx.Response
    
    # WebSocket testing
    def websocket_connect(self, url: str, **kwargs)
```

## Exceptions

### HTTP Exceptions

```python
class HTTPException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Dict[str, str] = None
    )

# Specific HTTP exceptions
class BadRequest(HTTPException)          # 400
class Unauthorized(HTTPException)        # 401
class Forbidden(HTTPException)           # 403
class NotFound(HTTPException)            # 404
class MethodNotAllowed(HTTPException)    # 405
class UnprocessableEntity(HTTPException) # 422
class InternalServerError(HTTPException) # 500
```

### Other Exceptions

```python
class ValidationError(Exception)
class WebSocketException(Exception)
class DependencyException(Exception)
class SecurityException(Exception)
class MCPException(Exception)
```

## CLI Commands

```bash
# Project management
agniapi new <name>                    # Create new project
agniapi run [options]                 # Run development server
agniapi test [options]                # Run tests

# Documentation
agniapi openapi [options]             # Generate OpenAPI spec
agniapi routes                        # List all routes

# MCP
agniapi mcp [options]                 # Run MCP server
```

## Configuration

### Environment Variables

- `AGNI_DEBUG`: Enable debug mode
- `AGNI_SECRET_KEY`: Secret key for JWT and sessions
- `AGNI_MCP_ENABLED`: Enable MCP server
- `AGNI_LOG_LEVEL`: Logging level

### Application Settings

```python
app.debug = True
app.secret_key = "your-secret-key"
app.mcp_enabled = True
```
