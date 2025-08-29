"""
Request handling for Agni API framework.
Combines Flask and FastAPI request patterns.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import parse_qs

from werkzeug.wrappers import Request as WerkzeugRequest
from starlette.requests import Request as StarletteRequest
from starlette.datastructures import Headers, QueryParams, FormData
from pydantic import BaseModel, ValidationError

from .forms import FormParser, UploadFile


class Request:
    """
    Unified request object that works with both WSGI and ASGI.
    Provides Flask and FastAPI-style interfaces.
    """
    
    def __init__(self, scope: Dict[str, Any], receive=None, send=None):
        self.scope = scope
        self.receive = receive
        self.send = send
        
        # Create underlying request objects for compatibility
        if scope.get("type") == "http":
            self._starlette_request = StarletteRequest(scope, receive)
        else:
            self._starlette_request = None
        
        self._werkzeug_request = None
        self._body = None
        self._json = None
        self._form = None
        self._form_parser = FormParser()
    
    @classmethod
    def from_werkzeug(cls, werkzeug_request: WerkzeugRequest) -> 'Request':
        """Create Request from Werkzeug request (WSGI compatibility)."""
        # Convert Werkzeug request to ASGI scope
        scope = {
            "type": "http",
            "method": werkzeug_request.method,
            "path": werkzeug_request.path,
            "query_string": werkzeug_request.query_string,
            "headers": [(k.lower().encode(), v.encode()) 
                       for k, v in werkzeug_request.headers.items()],
        }
        
        request = cls(scope)
        request._werkzeug_request = werkzeug_request
        return request
    
    # URL and path properties
    @property
    def method(self) -> str:
        """HTTP method (GET, POST, etc.)."""
        return self.scope.get("method", "GET")
    
    @property
    def url(self) -> str:
        """Full URL of the request."""
        if self._starlette_request:
            return str(self._starlette_request.url)
        elif self._werkzeug_request:
            return self._werkzeug_request.url
        return ""
    
    @property
    def path(self) -> str:
        """Path portion of the URL."""
        return self.scope.get("path", "/")
    
    @property
    def query_string(self) -> bytes:
        """Raw query string as bytes."""
        return self.scope.get("query_string", b"")
    
    @property
    def headers(self) -> Headers:
        """Request headers."""
        if self._starlette_request:
            return self._starlette_request.headers
        elif self._werkzeug_request:
            return Headers(self._werkzeug_request.headers.items())
        return Headers(self.scope.get("headers", []))
    
    # Query parameters
    @property
    def query_params(self) -> QueryParams:
        """Query parameters as a multi-dict."""
        if self._starlette_request:
            return self._starlette_request.query_params
        elif self._werkzeug_request:
            return QueryParams(self._werkzeug_request.args.items(multi=True))
        
        # Parse from query string
        qs = self.query_string.decode()
        parsed = parse_qs(qs, keep_blank_values=True)
        items = []
        for key, values in parsed.items():
            for value in values:
                items.append((key, value))
        return QueryParams(items)
    
    @property
    def args(self) -> QueryParams:
        """Flask-style alias for query_params."""
        return self.query_params
    
    # Request body handling
    async def body(self) -> bytes:
        """Get raw request body."""
        if self._body is None:
            if self._starlette_request:
                self._body = await self._starlette_request.body()
            elif self._werkzeug_request:
                self._body = self._werkzeug_request.get_data()
            else:
                self._body = b""
        return self._body
    
    async def json(self) -> Any:
        """Parse request body as JSON."""
        if self._json is None:
            try:
                body = await self.body()
                if body:
                    self._json = json.loads(body.decode())
                else:
                    self._json = None
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise ValueError("Invalid JSON in request body")
        return self._json
    
    async def form(self) -> FormData:
        """Parse request body as form data."""
        if self._form is None:
            if self._starlette_request:
                self._form = await self._starlette_request.form()
            elif self._werkzeug_request:
                # Convert Werkzeug form to Starlette FormData format
                form_dict = {}
                for key, value in self._werkzeug_request.form.items():
                    form_dict[key] = value
                self._form = FormData(form_dict)
            else:
                self._form = FormData({})
        return self._form

    async def form_data(self) -> Dict[str, Any]:
        """
        Parse form data with enhanced file upload support.
        Returns dictionary with form fields and UploadFile objects.
        """
        if self._starlette_request:
            return await self._form_parser.parse_form(self._starlette_request)
        else:
            # Fallback to basic form parsing
            form = await self.form()
            return dict(form)
    
    async def text(self) -> str:
        """Get request body as text."""
        body = await self.body()
        return body.decode()
    
    # Pydantic model parsing
    async def parse_model(self, model_class: type[BaseModel]) -> BaseModel:
        """
        Parse request body into a Pydantic model.
        Supports both JSON and form data.
        """
        content_type = self.headers.get("content-type", "")

        try:
            if "application/json" in content_type:
                data = await self.json()
                if data is None:
                    data = {}
            elif "application/x-www-form-urlencoded" in content_type:
                form_data = await self.form()
                data = dict(form_data)
            elif "multipart/form-data" in content_type:
                form_data = await self.form()
                data = dict(form_data)
            else:
                # Try JSON first, then form data
                try:
                    data = await self.json()
                    if data is None:
                        data = {}
                except (ValueError, json.JSONDecodeError):
                    try:
                        form_data = await self.form()
                        data = dict(form_data)
                    except Exception:
                        data = {}

            # Handle Pydantic v2 and v1
            if hasattr(model_class, 'model_validate'):
                # Pydantic v2
                return model_class.model_validate(data)
            else:
                # Pydantic v1 or regular constructor
                return model_class(**data)

        except ValidationError as e:
            raise ValueError(f"Validation error: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse request body: {e}")
    
    # Cookies
    @property
    def cookies(self) -> Dict[str, str]:
        """Request cookies."""
        if self._starlette_request:
            return dict(self._starlette_request.cookies)
        elif self._werkzeug_request:
            return dict(self._werkzeug_request.cookies)
        
        # Parse from headers
        cookie_header = self.headers.get("cookie", "")
        cookies = {}
        for item in cookie_header.split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                cookies[key] = value
        return cookies
    
    # Client information
    @property
    def client(self) -> Optional[str]:
        """Client IP address."""
        if self._starlette_request:
            return self._starlette_request.client.host if self._starlette_request.client else None
        elif self._werkzeug_request:
            return self._werkzeug_request.remote_addr
        
        # Get from scope
        client = self.scope.get("client")
        return client[0] if client else None
    
    @property
    def user_agent(self) -> str:
        """User agent string."""
        return self.headers.get("user-agent", "")
    
    # Authentication
    @property
    def auth(self) -> Optional[str]:
        """Authorization header."""
        return self.headers.get("authorization")
    
    # State management (for middleware)
    @property
    def state(self) -> Dict[str, Any]:
        """Request state for storing data between middleware."""
        if not hasattr(self, "_state"):
            self._state = {}
        return self._state
    
    # Flask-style properties
    @property
    def endpoint(self) -> Optional[str]:
        """Flask-style endpoint name."""
        return self.state.get("endpoint")
    
    @property
    def view_args(self) -> Dict[str, Any]:
        """Flask-style view arguments (path parameters)."""
        return self.state.get("view_args", {})
    
    # Utility methods
    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a header value with optional default."""
        return self.headers.get(name.lower(), default)
    
    def has_header(self, name: str) -> bool:
        """Check if a header exists."""
        return name.lower() in self.headers
    
    def is_json(self) -> bool:
        """Check if request content type is JSON."""
        content_type = self.headers.get("content-type", "")
        return "application/json" in content_type
    
    def is_form(self) -> bool:
        """Check if request content type is form data."""
        content_type = self.headers.get("content-type", "")
        return ("application/x-www-form-urlencoded" in content_type or 
                "multipart/form-data" in content_type)
    
    def is_secure(self) -> bool:
        """Check if request is over HTTPS."""
        return self.scope.get("scheme") == "https"

    async def files(self) -> Dict[str, Union[UploadFile, List[UploadFile]]]:
        """
        Get uploaded files from the request.
        Returns dictionary with field names as keys and UploadFile objects as values.
        """
        form_data = await self.form_data()
        files = {}

        for key, value in form_data.items():
            if isinstance(value, UploadFile):
                files[key] = value
            elif isinstance(value, list) and all(isinstance(item, UploadFile) for item in value):
                files[key] = value

        return files

    async def get_file(self, field_name: str) -> Optional[UploadFile]:
        """Get a single uploaded file by field name."""
        files = await self.files()
        file_data = files.get(field_name)

        if isinstance(file_data, UploadFile):
            return file_data
        elif isinstance(file_data, list) and file_data:
            return file_data[0]  # Return first file if multiple

        return None

    def __repr__(self) -> str:
        return f"<Request {self.method} {self.path}>"
