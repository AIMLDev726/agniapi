"""
Type definitions for Agni API framework.
"""

from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol, Union

from .request import Request
from .response import Response, ResponseType

# Type variables (removed unused P and T)

# Basic type aliases
ASGIApp = Callable[[Dict[str, Any], Callable, Callable], Awaitable[None]]
WSGIApp = Callable[[Dict[str, Any], Callable], Any]

# ASGI types
Scope = Dict[str, Any]
Receive = Callable[[], Awaitable[Dict[str, Any]]]
Send = Callable[[Dict[str, Any]], Awaitable[None]]

# Route handler types
SyncRouteHandler = Callable[..., ResponseType]
AsyncRouteHandler = Callable[..., Awaitable[ResponseType]]
RouteHandler = Union[SyncRouteHandler, AsyncRouteHandler]

# Middleware types
MiddlewareType = Union[
    Callable[[Request, Callable], ResponseType],
    Callable[[Request, Callable], Awaitable[ResponseType]],
]

# Dependency types
DependencyCallable = Union[
    Callable[..., Any],
    Callable[..., Awaitable[Any]],
]

# WebSocket handler types
WebSocketHandler = Callable[..., Awaitable[None]]

# Error handler types
ErrorHandler = Union[
    Callable[[Request, Exception], ResponseType],
    Callable[[Request, Exception], Awaitable[ResponseType]],
]

# Lifespan handler types
LifespanHandler = Callable[[], None]
AsyncLifespanHandler = Callable[[], Awaitable[None]]

# Security scheme types
SecurityScheme = Dict[str, Any]

# OpenAPI types
OpenAPISchema = Dict[str, Any]
OpenAPIOperation = Dict[str, Any]
OpenAPIParameter = Dict[str, Any]
OpenAPIResponse = Dict[str, Any]

# MCP types
MCPTool = Callable[..., Any]
MCPResource = Callable[..., Any]
MCPPrompt = Dict[str, Any]


class Dependency:
    """
    Represents a dependency that can be injected into route handlers.
    Similar to FastAPI's Depends.
    """
    
    def __init__(
        self,
        dependency: DependencyCallable,
        *,
        use_cache: bool = True,
        scope: str = "request",
    ):
        self.dependency = dependency
        self.use_cache = use_cache
        self.scope = scope
        
        # Get signature for type analysis
        self.signature = inspect.signature(dependency)
        self.is_async = inspect.iscoroutinefunction(dependency)
    
    def __call__(self, *args, **kwargs):
        """Make the dependency callable."""
        return self.dependency(*args, **kwargs)
    
    def __repr__(self):
        return f"Dependency({self.dependency.__name__})"


class SecurityDependency(Dependency):
    """
    Special dependency for security schemes.
    """
    
    def __init__(
        self,
        dependency: DependencyCallable,
        *,
        scheme_name: Optional[str] = None,
        auto_error: bool = True,
    ):
        super().__init__(dependency)
        self.scheme_name = scheme_name
        self.auto_error = auto_error


class BackgroundTask:
    """
    Represents a background task to be executed after the response is sent.
    Similar to FastAPI's BackgroundTasks.
    """
    
    def __init__(self, func: Callable, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.is_async = inspect.iscoroutinefunction(func)
    
    async def __call__(self):
        """Execute the background task."""
        if self.is_async:
            await self.func(*self.args, **self.kwargs)
        else:
            self.func(*self.args, **self.kwargs)


class BackgroundTasks:
    """
    Collection of background tasks.
    """
    
    def __init__(self):
        self.tasks: List[BackgroundTask] = []
    
    def add_task(self, func: Callable, *args, **kwargs):
        """Add a background task."""
        task = BackgroundTask(func, *args, **kwargs)
        self.tasks.append(task)
    
    async def execute_all(self):
        """Execute all background tasks."""
        for task in self.tasks:
            await task()


class UploadFile:
    """
    Represents an uploaded file.
    Compatible with both Flask and FastAPI patterns.
    """
    
    def __init__(
        self,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        file=None,
    ):
        self.filename = filename
        self.content_type = content_type
        self.file = file
        self._size: Optional[int] = None
    
    @property
    def size(self) -> int:
        """Get file size."""
        if self._size is None:
            if hasattr(self.file, 'seek') and hasattr(self.file, 'tell'):
                current_pos = self.file.tell()
                self.file.seek(0, 2)  # Seek to end
                self._size = self.file.tell()
                self.file.seek(current_pos)  # Restore position
            else:
                self._size = 0
        return self._size
    
    async def read(self, size: int = -1) -> bytes:
        """Read file content."""
        if hasattr(self.file, 'read'):
            if inspect.iscoroutinefunction(self.file.read):
                return await self.file.read(size)
            else:
                return self.file.read(size)
        return b""
    
    async def write(self, data: bytes):
        """Write data to file."""
        if hasattr(self.file, 'write'):
            if inspect.iscoroutinefunction(self.file.write):
                await self.file.write(data)
            else:
                self.file.write(data)
    
    async def seek(self, offset: int):
        """Seek to position in file."""
        if hasattr(self.file, 'seek'):
            if inspect.iscoroutinefunction(self.file.seek):
                await self.file.seek(offset)
            else:
                self.file.seek(offset)
    
    async def close(self):
        """Close the file."""
        if hasattr(self.file, 'close'):
            if inspect.iscoroutinefunction(self.file.close):
                await self.file.close()
            else:
                self.file.close()


class WebSocketConnectionState:
    """
    Represents the state of a WebSocket connection.
    """

    def __init__(self):
        self.connected = False
        self.client_state = "CONNECTING"
        self.application_state = "CONNECTING"


class HTTPConnection:
    """
    Base class for HTTP connections.
    """
    
    def __init__(self, scope: Dict[str, Any]):
        self.scope = scope
    
    @property
    def client(self) -> Optional[str]:
        """Client address."""
        client = self.scope.get("client")
        return client[0] if client else None
    
    @property
    def url(self) -> str:
        """Connection URL."""
        scheme = self.scope.get("scheme", "http")
        server = self.scope.get("server", ("localhost", 80))
        path = self.scope.get("path", "/")
        query_string = self.scope.get("query_string", b"")
        
        url = f"{scheme}://{server[0]}:{server[1]}{path}"
        if query_string:
            url += f"?{query_string.decode()}"
        
        return url


# Protocol definitions for type checking
class RequestProtocol(Protocol):
    """Protocol for request objects."""
    
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    
    async def body(self) -> bytes: ...
    async def json(self) -> Any: ...


class ResponseProtocol(Protocol):
    """Protocol for response objects."""
    
    status_code: int
    headers: Dict[str, str]
    content: Any


class MiddlewareProtocol(Protocol):
    """Protocol for middleware."""
    
    async def __call__(
        self,
        request: RequestProtocol,
        call_next: Callable[[RequestProtocol], Awaitable[ResponseProtocol]]
    ) -> ResponseProtocol: ...


class SecuritySchemeProtocol(Protocol):
    """Protocol for security schemes."""
    
    async def __call__(self, request: RequestProtocol) -> Any: ...


# Utility type functions
def is_async_callable(obj: Any) -> bool:
    """Check if an object is an async callable."""
    return inspect.iscoroutinefunction(obj) or (
        hasattr(obj, "__call__") and inspect.iscoroutinefunction(obj.__call__)
    )


def get_type_hints_with_defaults(func: Callable) -> Dict[str, Any]:
    """Get type hints with default values for a function."""
    sig = inspect.signature(func)
    hints = {}
    
    for name, param in sig.parameters.items():
        hints[name] = {
            "annotation": param.annotation,
            "default": param.default,
            "kind": param.kind,
        }
    
    return hints
