"""
Middleware system for Agni API framework.
ASGI-compatible middleware with Flask-style patterns.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Union
from abc import ABC, abstractmethod

from .request import Request
from .response import Response
from .types import MiddlewareType, is_async_callable
from .exceptions import HTTPException


class BaseMiddleware(ABC):
    """Base class for middleware."""
    
    def __init__(self, app):
        self.app = app
    
    @abstractmethod
    async def __call__(self, scope, receive, send):
        """ASGI interface."""
        pass


class MiddlewareStack:
    """
    Manages the middleware stack for the application.
    Handles both ASGI and WSGI-style middleware.
    """
    
    def __init__(self):
        self._middleware: List[MiddlewareType] = []
        self._middleware_instances: List[Any] = []
    
    def add(self, middleware_class: type, **kwargs):
        """Add middleware to the stack."""
        self._middleware.append((middleware_class, kwargs))
    
    def build_stack(self, app):
        """Build the middleware stack around the app."""
        # Start with the original app
        current_app = app
        
        # Wrap each middleware around the app (in reverse order)
        for middleware_class, kwargs in reversed(self._middleware):
            current_app = middleware_class(current_app, **kwargs)
            self._middleware_instances.append(current_app)
        
        return current_app
    
    def clear(self):
        """Clear all middleware."""
        self._middleware.clear()
        self._middleware_instances.clear()


class CORSMiddleware(BaseMiddleware):
    """
    CORS (Cross-Origin Resource Sharing) middleware.
    """
    
    def __init__(
        self,
        app,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        expose_headers: List[str] = None,
        max_age: int = 600,
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.expose_headers = expose_headers or []
        self.max_age = max_age
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive, send)
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            await self._handle_preflight(scope, receive, send)
            return
        
        # Add CORS headers to response
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                
                # Add CORS headers
                origin = request.headers.get("origin")
                if origin and (origin in self.allow_origins or "*" in self.allow_origins):
                    headers[b"access-control-allow-origin"] = origin.encode()
                
                if self.allow_credentials:
                    headers[b"access-control-allow-credentials"] = b"true"
                
                if self.expose_headers:
                    headers[b"access-control-expose-headers"] = ", ".join(self.expose_headers).encode()
                
                message["headers"] = list(headers.items())
            
            await send(message)
        
        await self.app(scope, receive, send_with_cors)
    
    async def _handle_preflight(self, scope, receive, send):
        """Handle CORS preflight requests."""
        request = Request(scope, receive, send)
        
        headers = []
        
        # Check origin
        origin = request.headers.get("origin")
        if origin and (origin in self.allow_origins or "*" in self.allow_origins):
            headers.append((b"access-control-allow-origin", origin.encode()))
        
        # Allow methods
        headers.append((b"access-control-allow-methods", ", ".join(self.allow_methods).encode()))
        
        # Allow headers
        requested_headers = request.headers.get("access-control-request-headers")
        if requested_headers and "*" in self.allow_headers:
            headers.append((b"access-control-allow-headers", requested_headers.encode()))
        elif self.allow_headers:
            headers.append((b"access-control-allow-headers", ", ".join(self.allow_headers).encode()))
        
        # Credentials
        if self.allow_credentials:
            headers.append((b"access-control-allow-credentials", b"true"))
        
        # Max age
        headers.append((b"access-control-max-age", str(self.max_age).encode()))
        
        # Send response
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": headers,
        })
        await send({
            "type": "http.response.body",
            "body": b"",
        })


class TrustedHostMiddleware(BaseMiddleware):
    """
    Middleware to validate trusted hosts.
    """
    
    def __init__(
        self,
        app,
        allowed_hosts: List[str] = None,
        www_redirect: bool = True,
    ):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or ["*"]
        self.www_redirect = www_redirect
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Check if host is allowed
        headers = dict(scope.get("headers", []))
        host = headers.get(b"host", b"").decode()
        
        if not self._is_host_allowed(host):
            # Return 400 Bad Request
            await send({
                "type": "http.response.start",
                "status": 400,
                "headers": [(b"content-type", b"text/plain")],
            })
            await send({
                "type": "http.response.body",
                "body": b"Invalid host header",
            })
            return
        
        await self.app(scope, receive, send)
    
    def _is_host_allowed(self, host: str) -> bool:
        """Check if host is in allowed hosts."""
        if "*" in self.allowed_hosts:
            return True
        
        return host in self.allowed_hosts


class GZipMiddleware(BaseMiddleware):
    """
    GZip compression middleware.
    """
    
    def __init__(
        self,
        app,
        minimum_size: int = 500,
        compresslevel: int = 9,
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive, send)
        
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            await self.app(scope, receive, send)
            return
        
        # Collect response
        response_started = False
        response_complete = False
        status_code = 200
        response_headers = []
        body_parts = []
        
        async def send_wrapper(message):
            nonlocal response_started, response_complete, status_code, response_headers
            
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                response_headers = list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))
                if not message.get("more_body", False):
                    response_complete = True
                    await self._send_compressed_response(send, status_code, response_headers, body_parts)
        
        await self.app(scope, receive, send_wrapper)
    
    async def _send_compressed_response(self, send, status_code, headers, body_parts):
        """Send compressed response."""
        import gzip
        
        # Combine body parts
        body = b"".join(body_parts)
        
        # Check if compression is worthwhile
        if len(body) < self.minimum_size:
            # Send uncompressed
            await send({
                "type": "http.response.start",
                "status": status_code,
                "headers": headers,
            })
            await send({
                "type": "http.response.body",
                "body": body,
            })
            return
        
        # Compress body
        compressed_body = gzip.compress(body, compresslevel=self.compresslevel)
        
        # Update headers
        headers_dict = dict(headers)
        headers_dict[b"content-encoding"] = b"gzip"
        headers_dict[b"content-length"] = str(len(compressed_body)).encode()
        
        # Send compressed response
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": list(headers_dict.items()),
        })
        await send({
            "type": "http.response.body",
            "body": compressed_body,
        })


class HTTPSRedirectMiddleware(BaseMiddleware):
    """
    Middleware to redirect HTTP requests to HTTPS.
    """
    
    def __init__(self, app):
        super().__init__(app)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Check if request is already HTTPS
        if scope.get("scheme") == "https":
            await self.app(scope, receive, send)
            return
        
        # Redirect to HTTPS
        host = None
        for name, value in scope.get("headers", []):
            if name == b"host":
                host = value.decode()
                break
        
        if not host:
            host = "localhost"
        
        path = scope.get("path", "/")
        query_string = scope.get("query_string", b"").decode()
        
        redirect_url = f"https://{host}{path}"
        if query_string:
            redirect_url += f"?{query_string}"
        
        await send({
            "type": "http.response.start",
            "status": 301,
            "headers": [
                (b"location", redirect_url.encode()),
                (b"content-type", b"text/plain"),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": b"Redirecting to HTTPS",
        })


class RequestLoggingMiddleware(BaseMiddleware):
    """
    Middleware for logging requests.
    """
    
    def __init__(self, app, logger=None):
        super().__init__(app)
        self.logger = logger or self._get_default_logger()
    
    def _get_default_logger(self):
        import logging
        logger = logging.getLogger("agniapi.requests")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive, send)
        start_time = time.time()
        
        # Log request
        self.logger.info(f"Request: {request.method} {request.path}")
        
        # Track response
        status_code = 200
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            status_code = 500
            self.logger.error(f"Request failed: {e}")
            raise
        finally:
            # Log response
            duration = time.time() - start_time
            self.logger.info(
                f"Response: {status_code} - {duration:.3f}s - {request.method} {request.path}"
            )


# Middleware decorator for Flask-style usage
def middleware(middleware_class: type):
    """
    Decorator to register middleware.
    """
    def decorator(app):
        app.add_middleware(middleware_class)
        return app
    return decorator


# Alias for backward compatibility
Middleware = BaseMiddleware
